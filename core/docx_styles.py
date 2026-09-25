"""
Resolves the formatting Word would actually show for a paragraph or run:
document defaults -> paragraph style chain -> character style chain -> direct formatting.
Theme fonts ("+Headings"/"+Body") and theme colours are looked up in the document theme.
"""
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from core.ooxml_package import DOC_REL_NS, OoxmlPackage, PackageError

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
W = f"{{{W_NS}}}"
A = f"{{{A_NS}}}"
FALSE_VALUES = {"0", "false", "off", "none"}
THEME_COLOR_ALIASES = {"text1": "dk1", "background1": "lt1", "text2": "dk2", "background2": "lt2",
                       "dark1": "dk1", "light1": "lt1", "dark2": "dk2", "light2": "lt2",
                       "hyperlink": "hlink", "followedHyperlink": "folHlink"}


def wval(el: Optional[ET.Element], default: Optional[str] = None) -> Optional[str]:
    if el is None:
        return default
    return el.get(W + "val", default)


def on_off(el: Optional[ET.Element]) -> Optional[bool]:
    """Reads a Word toggle like <w:b/> or <w:b w:val="0"/>. None = not set here."""
    if el is None:
        return None
    return (el.get(W + "val") or "1").lower() not in FALSE_VALUES


def read_theme(pkg: OoxmlPackage, theme_part: Optional[str]) -> Dict[str, Any]:
    theme: Dict[str, Any] = {"major": None, "minor": None, "colors": {}}
    if not theme_part or not pkg.has(theme_part):
        return theme
    try:
        root = pkg.xml(theme_part)
    except PackageError:
        return theme
    scheme = root.find(f".//{A}clrScheme")
    for slot in list(scheme) if scheme is not None else []:
        color = slot.find(f"{A}srgbClr")
        system = slot.find(f"{A}sysClr")
        value = color.get("val") if color is not None else (system.get("lastClr") if system is not None else None)
        if value:
            theme["colors"][slot.tag.split("}")[-1]] = value.upper()
    for key, tag in (("major", "majorFont"), ("minor", "minorFont")):
        latin = root.find(f".//{A}{tag}/{A}latin")
        if latin is not None:
            theme[key] = latin.get("typeface")
    return theme


class StyleSheet:
    def __init__(self, pkg: OoxmlPackage, doc_part: str):
        self.styles: Dict[str, Dict[str, Any]] = {}
        self.default_paragraph_style: Optional[str] = None
        self.doc_rpr: Optional[ET.Element] = None
        styles_part = next((t for _, t in pkg.rels_of_type(doc_part, DOC_REL_NS + "/styles")), None)
        theme_part = next((t for _, t in pkg.rels_of_type(doc_part, DOC_REL_NS + "/theme")), None)
        self.theme = read_theme(pkg, theme_part)
        if styles_part and pkg.has(styles_part):
            self._load(pkg.xml(styles_part))

    def _load(self, root: ET.Element) -> None:
        self.doc_rpr = root.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")
        for style in root.findall(f"{W}style"):
            style_id = style.get(W + "styleId")
            if not style_id:
                continue
            self.styles[style_id] = {
                "type": style.get(W + "type"),
                "name": (wval(style.find(W + "name")) or style_id).lower(),
                "based_on": wval(style.find(W + "basedOn")),
                "rpr": style.find(W + "rPr"),
                "ppr": style.find(W + "pPr"),
            }
            if style.get(W + "type") == "paragraph" and on_off_attr(style.get(W + "default")):
                self.default_paragraph_style = style_id

    def chain(self, style_id: Optional[str]) -> List[Dict[str, Any]]:
        """Styles from the root ancestor down to `style_id` (cycle safe)."""
        result: List[Dict[str, Any]] = []
        seen = set()
        while style_id and style_id in self.styles and style_id not in seen:
            seen.add(style_id)
            result.insert(0, self.styles[style_id])
            style_id = self.styles[style_id]["based_on"]
        return result

    def paragraph_style_id(self, p: ET.Element) -> Optional[str]:
        return wval(p.find(f"{W}pPr/{W}pStyle")) or self.default_paragraph_style

    def style_names(self, p: ET.Element) -> List[str]:
        style_id = self.paragraph_style_id(p)
        return [s["name"] for s in self.chain(style_id)] + ([style_id.lower()] if style_id else [])

    def outline_level(self, p: ET.Element) -> Optional[int]:
        direct = wval(p.find(f"{W}pPr/{W}outlineLvl"))
        if direct is not None and direct.isdigit() and int(direct) < 9:
            return int(direct)
        for style in reversed(self.chain(self.paragraph_style_id(p))):
            level = wval(style["ppr"].find(W + "outlineLvl")) if style["ppr"] is not None else None
            if level is not None and level.isdigit() and int(level) < 9:
                return int(level)
            name = style["name"]
            if name.startswith("heading ") and name[8:].isdigit():
                return int(name[8:]) - 1
        return None

    def has_style_name(self, p: ET.Element, name: str) -> bool:
        return name in self.style_names(p)

    def alignment(self, p: ET.Element) -> Optional[str]:
        value = wval(p.find(f"{W}pPr/{W}jc"))
        if value is None:
            for style in self.chain(self.paragraph_style_id(p)):
                if style["ppr"] is not None and style["ppr"].find(W + "jc") is not None:
                    value = wval(style["ppr"].find(W + "jc"))
        return {"both": "justify", "distribute": "justify", "start": "left", "end": "right"}.get(value or "", value)

    def run_props(self, p: ET.Element, run: Optional[ET.Element]) -> Dict[str, Any]:
        """Effective font, size (pt), bold, italic, underline and colour (#RRGGBB) for a run."""
        props: Dict[str, Any] = {"font": None, "size": 11.0, "bold": False, "italic": False,
                                 "underline": False, "color": None}
        layers = [self.doc_rpr]
        layers += [s["rpr"] for s in self.chain(self.paragraph_style_id(p))]
        rpr = run.find(W + "rPr") if run is not None else None
        if rpr is not None:
            layers += [s["rpr"] for s in self.chain(wval(rpr.find(W + "rStyle")))]
        layers.append(rpr)
        for layer in layers:
            if layer is not None:
                self._apply_layer(props, layer)
        return props

    def _apply_layer(self, props: Dict[str, Any], rpr: ET.Element) -> None:
        fonts = rpr.find(W + "rFonts")
        if fonts is not None:
            theme_font = fonts.get(W + "asciiTheme") or fonts.get(W + "hAnsiTheme")
            if theme_font:
                props["font"] = self.theme["major" if theme_font.startswith("major") else "minor"] or props["font"]
            elif fonts.get(W + "ascii") or fonts.get(W + "hAnsi"):
                props["font"] = fonts.get(W + "ascii") or fonts.get(W + "hAnsi")
        size = wval(rpr.find(W + "sz"))
        if size and size.isdigit():
            props["size"] = int(size) / 2
        for key, tag in (("bold", "b"), ("italic", "i")):
            value = on_off(rpr.find(W + tag))
            if value is not None:
                props[key] = value
        underline = rpr.find(W + "u")
        if underline is not None:
            props["underline"] = (wval(underline) or "single") != "none"
        color = rpr.find(W + "color")
        if color is not None:
            theme_color = color.get(W + "themeColor")
            if theme_color:
                slot = THEME_COLOR_ALIASES.get(theme_color, theme_color)
                if slot in self.theme["colors"]:
                    props["color"] = self.theme["colors"][slot]
            elif (wval(color) or "auto").lower() != "auto":
                props["color"] = wval(color)


def on_off_attr(value: Optional[str]) -> bool:
    return value is not None and value.lower() not in FALSE_VALUES
