"""
OOXML package access for in-place editing of existing .docx / .pptx files.

Why not rebuild the file: an edit must only touch the XML parts it changes. Every other
part (fonts, themes, settings, media, custom XML) is copied back byte-for-byte.

Why the namespace juggling: ElementTree forgets which namespace prefixes a part declared and
only re-declares the ones still in use. Word/PowerPoint list extra prefixes in `mc:Ignorable`,
so a dropped declaration makes Office report the file as corrupt. We therefore re-register the
part's prefixes before serialising and restore the original root start tag.
"""
import io
import posixpath
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
from typing import Dict, List, Optional, Tuple

PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
IMAGE_REL_TYPE = DOC_REL_NS + "/image"
OFFICE_DOC_REL_TYPE = DOC_REL_NS + "/officeDocument"
XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'

# Prefixes we may introduce ourselves (e.g. when adding a picture), so ET never invents "ns0"
KNOWN_PREFIXES = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": DOC_REL_NS,
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

IMAGE_TYPES = {"png": "image/png", "jpeg": "image/jpeg", "gif": "image/gif"}
MAX_ENTRIES = 5000
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
_ROOT_TAG = re.compile(rb"<(?![?!])[^>]*>")
_XMLNS_ATTR = re.compile(r'\sxmlns(?::[\w.-]+)?="[^"]*"')


class PackageError(Exception):
    """The file is not a readable Office package."""


def _register(ns_map: Dict[str, str]) -> None:
    for prefix, uri in ns_map.items():
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            pass  # reserved prefix such as "xml"; ET handles those itself


def _relative(target_part: str, source_part: str) -> str:
    # Leading "/" keeps posixpath away from the (Windows) working directory
    return posixpath.relpath("/" + target_part, "/" + posixpath.dirname(source_part))


def image_info(data: bytes) -> Tuple[str, int, int]:
    """Returns (extension, width_px, height_px) for PNG/JPEG/GIF bytes, or raises ValueError."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return "png", width, height
    if data[:6] in (b"GIF87a", b"GIF89a"):
        width, height = struct.unpack("<HH", data[6:10])
        return "gif", width, height
    if data[:2] == b"\xff\xd8":
        pos = 2
        while pos + 9 < len(data):
            if data[pos] != 0xFF:
                pos += 1
                continue
            marker = data[pos + 1]
            length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
            # SOF0..SOF15 carry the frame size (C4/C8/CC are not frames)
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
                return "jpeg", width, height
            pos += 2 + length
    raise ValueError("Unsupported image. Use a PNG, JPEG or GIF file.")


class XmlPart:
    """A parsed XML part that remembers its original root tag and namespace prefixes."""

    def __init__(self, data: bytes):
        self.ns_map: Dict[str, str] = {}
        for _, (prefix, uri) in ET.iterparse(io.BytesIO(data), events=("start-ns",)):
            self.ns_map.setdefault(prefix, uri)
        self.root = ET.fromstring(data)
        match = _ROOT_TAG.search(data)
        self.root_tag = match.group(0).decode("utf-8") if match else ""

    def to_bytes(self) -> bytes:
        _register(KNOWN_PREFIXES)
        _register(self.ns_map)
        text = ET.tostring(self.root, encoding="unicode")
        new_tag_match = re.match(r"<[^>]*>", text)
        if self.root_tag and new_tag_match and not self.root_tag.endswith("/>"):
            new_tag = new_tag_match.group(0)
            original = self.root_tag
            # Keep every original declaration, plus any namespace we introduced during the edit
            for decl in _XMLNS_ATTR.findall(new_tag):
                if decl.strip().split("=")[0] + "=" not in original:
                    original = original[:-1] + decl + ">"
            text = original + text[len(new_tag):]
        return (XML_DECLARATION + text).encode("utf-8")


class OoxmlPackage:
    def __init__(self, data: bytes):
        try:
            self._zip_names: List[str] = []
            self._files: Dict[str, bytes] = {}
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                entries = zf.infolist()
                # Declared sizes are checked before decompressing, so a zip bomb is rejected cheaply
                if len(entries) > MAX_ENTRIES or sum(i.file_size for i in entries) > MAX_UNCOMPRESSED_BYTES:
                    raise PackageError("The file is too large to edit safely (over 200 MB uncompressed).")
                for info in entries:
                    self._zip_names.append(info.filename)
                    self._files[info.filename] = zf.read(info.filename)
        except (zipfile.BadZipFile, OSError, ValueError) as e:
            raise PackageError("The file is not a valid Office document (it may be corrupted).") from e
        if "[Content_Types].xml" not in self._files:
            raise PackageError("The file is missing [Content_Types].xml, so it is not a valid Office document.")
        self._xml: Dict[str, XmlPart] = {}

    @classmethod
    def from_file(cls, path: str) -> "OoxmlPackage":
        with open(path, "rb") as f:
            return cls(f.read())

    # ---------- raw parts ----------
    def has(self, name: str) -> bool:
        return name in self._files

    def names(self) -> List[str]:
        return list(self._zip_names)

    def read(self, name: str) -> bytes:
        if name in self._xml:
            return self._xml[name].to_bytes()
        return self._files[name]

    def write(self, name: str, data: bytes) -> None:
        self._xml.pop(name, None)
        if name not in self._files:
            self._zip_names.append(name)
        self._files[name] = data

    def remove(self, name: str) -> None:
        self._xml.pop(name, None)
        self._files.pop(name, None)
        self._zip_names = [n for n in self._zip_names if n != name]

    # ---------- xml parts ----------
    def xml(self, name: str) -> ET.Element:
        """Parsed root of an XML part. Changes to it are written back by to_bytes()."""
        if name not in self._xml:
            if name not in self._files:
                raise PackageError(f"The document is missing the part {name}.")
            try:
                self._xml[name] = XmlPart(self._files[name])
            except ET.ParseError as e:
                raise PackageError(f"The part {name} is not valid XML (the file may be corrupted).") from e
        return self._xml[name].root

    # ---------- relationships ----------
    @staticmethod
    def rels_name(part: str) -> str:
        folder, base = posixpath.split(part)
        return posixpath.join(folder, "_rels", base + ".rels")

    def rels(self, part: str) -> Optional[ET.Element]:
        name = self.rels_name(part)
        return self.xml(name) if self.has(name) else None

    def resolve(self, part: str, target: str) -> str:
        if target.startswith("/"):
            return target.lstrip("/")
        return posixpath.normpath(posixpath.join(posixpath.dirname(part), target))

    def rel_target(self, part: str, rel_id: str) -> Optional[str]:
        rels = self.rels(part)
        if rels is None:
            return None
        for rel in rels:
            if rel.get("Id") == rel_id and rel.get("TargetMode") != "External":
                return self.resolve(part, rel.get("Target", ""))
        return None

    def rels_of_type(self, part: str, rel_type: str) -> List[Tuple[str, str]]:
        rels = self.rels(part)
        if rels is None:
            return []
        return [(r.get("Id", ""), self.resolve(part, r.get("Target", "")))
                for r in rels if r.get("Type") == rel_type and r.get("TargetMode") != "External"]

    def main_part(self) -> str:
        for _, target in self.rels_of_type("", OFFICE_DOC_REL_TYPE):
            return target
        raise PackageError("The document has no main part (the file may be corrupted).")

    def add_rel(self, part: str, rel_type: str, target_part: str) -> str:
        name = self.rels_name(part)
        if not self.has(name):
            self.write(name, f'{XML_DECLARATION}<Relationships xmlns="{PKG_REL_NS}"></Relationships>'.encode())
        rels = self.xml(name)
        used = {r.get("Id") for r in rels}
        number = 1
        while f"rId{number}" in used:
            number += 1
        rel_id = f"rId{number}"
        target = _relative(target_part, part)
        ET.SubElement(rels, f"{{{PKG_REL_NS}}}Relationship", {"Id": rel_id, "Type": rel_type, "Target": target})
        return rel_id

    def set_rel_target(self, part: str, rel_id: str, target_part: str) -> None:
        rels = self.rels(part)
        if rels is None:
            return
        for rel in rels:
            if rel.get("Id") == rel_id:
                rel.set("Target", _relative(target_part, part))

    def remove_rel(self, part: str, rel_id: str) -> None:
        rels = self.rels(part)
        if rels is None:
            return
        for rel in list(rels):
            if rel.get("Id") == rel_id:
                rels.remove(rel)

    # ---------- content types & media ----------
    def ensure_default_type(self, extension: str, content_type: str) -> None:
        types = self.xml("[Content_Types].xml")
        for item in types:
            if item.tag == f"{{{CT_NS}}}Default" and item.get("Extension", "").lower() == extension:
                return
        ET.SubElement(types, f"{{{CT_NS}}}Default", {"Extension": extension, "ContentType": content_type})

    def remove_override(self, part: str) -> None:
        types = self.xml("[Content_Types].xml")
        for item in list(types):
            if item.tag == f"{{{CT_NS}}}Override" and item.get("PartName") == "/" + part:
                types.remove(item)

    def add_media(self, folder: str, data: bytes) -> str:
        """Stores image bytes as a new part (e.g. word/media/image7.png) and returns its name."""
        extension, _, _ = image_info(data)
        self.ensure_default_type(extension, IMAGE_TYPES[extension])
        number = 1
        while self.has(f"{folder}/image{number}.{extension}"):
            number += 1
        name = f"{folder}/image{number}.{extension}"
        self.write(name, data)
        return name

    # ---------- save ----------
    def to_bytes(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # [Content_Types].xml must be the first entry for some Office versions
            ordered = ["[Content_Types].xml"] + [n for n in self._zip_names if n != "[Content_Types].xml"]
            for name in ordered:
                zf.writestr(name, self.read(name))
        return buf.getvalue()
