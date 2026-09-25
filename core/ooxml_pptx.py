"""
Pure-Python OpenXML PPTX Builder and Reader
Generates valid Microsoft PowerPoint (.pptx) presentations strictly adhering to ECMA-376 standards.
Widescreen 16:9 layout (12192000 x 6858000 EMU).
"""
import io
from collections import Counter
import re
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from typing import List, Dict, Any, Optional, Tuple

from core.ooxml_package import image_info
from core.ooxml_parts import (IMAGE_DEFAULTS, LAYOUT_CT, MASTER_CT, THEME_CT, pptx_picture_xml, rels_xml,
                              slide_layout_xml, slide_master_xml, theme_xml)

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

SLIDE_WIDTH = 12192000   # 16:9 EMU
SLIDE_HEIGHT = 6858000  # 16:9 EMU
EMU_PER_INCH = 914400
TITLE_LOGO_WIDTH = int(1.8 * EMU_PER_INCH)
SLIDE_LOGO_WIDTH = int(0.9 * EMU_PER_INCH)

def make_shape_xml(sp_id: int, name: str, x: int, y: int, cx: int, cy: int, text_runs: List[Dict[str, Any]],
                   fill_color: Optional[str] = None, border_color: Optional[str] = None, border_width: int = 12700,
                   radius: Optional[int] = None) -> str:
    """Creates a DrawingML shape XML snippet."""
    fill_xml = f'<a:solidFill><a:srgbClr val="{fill_color}"/></a:solidFill>' if fill_color else '<a:noFill/>'
    ln_xml = f'<a:ln w="{border_width}"><a:solidFill><a:srgbClr val="{border_color}"/></a:solidFill></a:ln>' if border_color else '<a:ln><a:noFill/></a:ln>'
    
    geom = "roundRect" if radius else "rect"
    geom_xml = f'<a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>'

    paras_xml = []
    for p in text_runs:
        align = p.get("align", "l")
        a_map = {"left": "l", "center": "ctr", "right": "r", "l": "l", "ctr": "ctr", "r": "r"}
        al_val = a_map.get(align, "l")
        
        runs = p.get("runs", [])
        if not runs and "text" in p:
            runs = [{"text": p["text"], "bold": p.get("bold", False), "size": p.get("size", 14), "color": p.get("color", "333333")}]

        # A leading "\n" in the layouts below means "gap before this paragraph". A raw newline
        # inside <a:t> is not a line break in PowerPoint, so it becomes paragraph spacing instead.
        spacing = '<a:spcBef><a:spcPts val="600"/></a:spcBef>' if runs and str(runs[0].get("text", "")).startswith("\n") else ""
        bullet = '<a:buFont typeface="Arial"/><a:buChar char="&#8226;"/>' if p.get("bullet") else ""
        indent = ' marL="285750" indent="-285750"' if p.get("bullet") else ""

        r_xmls = []
        for r in runs:
            t_esc = escape(r.get("text", "").lstrip("\n"))
            sz = int(r.get("size", 14) * 100)
            b_attr = ' b="1"' if r.get("bold", False) else ' b="0"'
            i_attr = ' i="1"' if r.get("italic", False) else ''
            clr = r.get("color", "333333")
            r_xmls.append(f'<a:r><a:rPr lang="en-US" sz="{sz}"{b_attr}{i_attr} dirty="0"><a:solidFill><a:srgbClr val="{clr}"/></a:solidFill></a:rPr><a:t>{t_esc}</a:t></a:r>')
            
        paras_xml.append(f'<a:p><a:pPr algn="{al_val}"{indent}>{spacing}{bullet}</a:pPr>{"".join(r_xmls)}</a:p>')

    tx_body = "".join(paras_xml) if paras_xml else '<a:p><a:endParaRPr/></a:p>'

    return f"""<p:sp>
  <p:nvSpPr>
    <p:cNvPr id="{sp_id}" name="{escape(name)}"/>
    <p:cNvSpPr/>
    <p:nvPr/>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm>
      <a:off x="{x}" y="{y}"/>
      <a:ext cx="{cx}" cy="{cy}"/>
    </a:xfrm>
    {geom_xml}
    {fill_xml}
    {ln_xml}
  </p:spPr>
  <p:txBody>
    <a:bodyPr vert="horz" lIns="91440" tIns="91440" rIns="91440" bIns="91440" rtlCol="0" anchor="ctr"/>
    <a:lstStyle/>
    {tx_body}
  </p:txBody>
</p:sp>"""


class PptxBuilder:
    def __init__(self, title: str = "Enterprise AI Presentation",
                 primary_color: str = "0F2D59", secondary_color: str = "2563EB",
                 accent_color: str = "10B981", bg_color: str = "F8FAFC",
                 primary_font: str = "Arial"):
        self.title = title
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.accent_color = accent_color
        self.bg_color = bg_color
        self.primary_font = primary_font
        self.slides: List[Dict[str, Any]] = []
        self.images: List[bytes] = []
        self.logo: Optional[Tuple[int, float]] = None  # (image index, height / width)

    def set_logo(self, data: bytes) -> None:
        """Shows the picture large on the title slide and small in the corner of every other slide."""
        _, width, height = image_info(data)
        self.images.append(data)
        self.logo = (len(self.images) - 1, height / width)

    def media_name(self, index: int) -> str:
        return f"image{index + 1}.{image_info(self.images[index])[0]}"

    def logo_shape(self, slide_type: str) -> Optional[Dict[str, Any]]:
        if self.logo is None:
            return None
        index, ratio = self.logo
        if slide_type == "title":
            cx = TITLE_LOGO_WIDTH
            return {"type": "picture", "image": index, "name": "Company Logo",
                    "x": 1000000, "y": 500000, "cx": cx, "cy": int(cx * ratio)}
        cx = SLIDE_LOGO_WIDTH
        return {"type": "picture", "image": index, "name": "Company Logo",
                "x": SLIDE_WIDTH - 600000 - cx, "y": 250000, "cx": cx, "cy": int(cx * ratio)}

    def add_bullet_slide(self, title: str, category: str, bullets: List[str]):
        shapes = self.add_header_elements(title, category)
        paras = [{"bullet": True, "runs": [{"text": b, "size": 18, "color": "1E293B"}]} for b in bullets]
        shapes.append({"type": "text", "name": "Content Placeholder", "x": 800000, "y": 1800000,
                       "cx": 10592000, "cy": 4400000, "paras": paras})
        self.slides.append({"type": "bullets", "title": title, "shapes": shapes})

    def add_title_slide(self, title: str, subtitle: str, metadata: str = "Confidential | Enterprise Strategy 2025"):
        slide = {
            "type": "title",
            "title": title,
            "subtitle": subtitle,
            "metadata": metadata,
            "shapes": [
                # Top accent banner
                {"type": "rect", "x": 0, "y": 0, "cx": SLIDE_WIDTH, "cy": 180000, "fill": self.secondary_color},
                # Main Title Card
                {"type": "text", "name": "Title", "x": 1000000, "y": 1800000, "cx": 10192000, "cy": 1800000,
                 "paras": [
                     {"align": "center", "runs": [{"text": title, "bold": True, "size": 36, "color": self.primary_color}]}
                 ]},
                # Subtitle
                {"type": "text", "name": "Subtitle", "x": 1200000, "y": 3600000, "cx": 9792000, "cy": 1200000,
                 "paras": [
                     {"align": "center", "runs": [{"text": subtitle, "bold": False, "size": 20, "color": "475569"}]}
                 ]},
                # Bottom metadata bar
                {"type": "text", "name": "Footer", "x": 1000000, "y": 5800000, "cx": 10192000, "cy": 500000,
                 "paras": [
                     {"align": "center", "runs": [{"text": metadata, "bold": False, "size": 12, "color": "94A3B8"}]}
                 ]}
            ]
        }
        self.slides.append(slide)

    def add_header_elements(self, title: str, category: str = "EXECUTIVE BRIEFING") -> List[Dict[str, Any]]:
        return [
            # Header accent line
            {"type": "rect", "x": 800000, "y": 450000, "cx": 400000, "cy": 40000, "fill": self.accent_color},
            # Category eyebrow
            {"type": "text", "name": "Category", "x": 800000, "y": 550000, "cx": 10500000, "cy": 300000,
             "paras": [{"runs": [{"text": category.upper(), "bold": True, "size": 11, "color": self.secondary_color}]}]},
            # Slide Title
            {"type": "text", "name": "Title", "x": 800000, "y": 850000, "cx": 10500000, "cy": 700000,
             "paras": [{"runs": [{"text": title, "bold": True, "size": 26, "color": self.primary_color}]}]},
            # Subtle header divider
            {"type": "rect", "x": 800000, "y": 1550000, "cx": 10592000, "cy": 20000, "fill": "E2E8F0"}
        ]

    def add_executive_summary_slide(self, title: str, summary_text: str, highlights: List[str]):
        shapes = self.add_header_elements(title, "STRATEGIC OVERVIEW")
        # Callout card
        shapes.append({
            "type": "card", "x": 800000, "y": 1800000, "cx": 10592000, "cy": 1400000,
            "fill": "F1F5F9", "border": self.primary_color, "border_w": 25400,
            "paras": [
                {"runs": [{"text": "EXECUTIVE CALLOUT: ", "bold": True, "size": 14, "color": self.primary_color},
                          {"text": summary_text, "bold": False, "size": 14, "color": "1E293B"}]}
            ]
        })
        # 3 highlight cards below
        card_w = 3300000
        gap = 346000
        start_x = 800000
        for i, h in enumerate(highlights[:3]):
            x = start_x + i * (card_w + gap)
            shapes.append({
                "type": "card", "x": x, "y": 3400000, "cx": card_w, "cy": 2800000,
                "fill": "FFFFFF", "border": "CBD5E1",
                "paras": [
                    {"runs": [{"text": f"Pillar 0{i+1}", "bold": True, "size": 14, "color": self.secondary_color}]},
                    {"runs": [{"text": h, "bold": False, "size": 13, "color": "334155"}]}
                ]
            })
        self.slides.append({"type": "executive_summary", "title": title, "shapes": shapes})

    def add_three_pillar_slide(self, title: str, subtitle: str, pillars: List[Dict[str, str]]):
        shapes = self.add_header_elements(title, "MARKET DYNAMICS")
        card_w = 3300000
        gap = 346000
        start_x = 800000
        for i, p in enumerate(pillars[:3]):
            x = start_x + i * (card_w + gap)
            p_title = p.get("title", f"Initiative {i+1}")
            p_desc = p.get("desc", "")
            p_metric = p.get("metric", "")
            
            paras = [
                {"runs": [{"text": p_title, "bold": True, "size": 16, "color": self.primary_color}]},
                {"runs": [{"text": "\n" + p_desc, "bold": False, "size": 13, "color": "475569"}]}
            ]
            if p_metric:
                paras.append({"runs": [{"text": f"\n\n{p_metric}", "bold": True, "size": 18, "color": self.accent_color}]})

            shapes.append({
                "type": "card", "x": x, "y": 1800000, "cx": card_w, "cy": 4400000,
                "fill": "FFFFFF", "border": "E2E8F0",
                "paras": paras
            })
        self.slides.append({"type": "three_pillars", "title": title, "shapes": shapes})

    def add_two_column_slide(self, title: str, category: str, col1_title: str, col1_points: List[str],
                             col2_title: str, col2_points: List[str]):
        shapes = self.add_header_elements(title, category)
        col_w = 5100000
        gap = 392000
        
        # Col 1
        c1_paras: List[Dict[str, Any]] = [{"runs": [{"text": col1_title, "bold": True, "size": 16, "color": self.primary_color}]}]
        for pt in col1_points:
            c1_paras.append({"bullet": True, "runs": [{"text": pt, "bold": False, "size": 13, "color": "334155"}]})
        shapes.append({
            "type": "card", "x": 800000, "y": 1800000, "cx": col_w, "cy": 4400000,
            "fill": "FFFFFF", "border": "E2E8F0", "paras": c1_paras
        })
        
        # Col 2
        c2_paras: List[Dict[str, Any]] = [{"runs": [{"text": col2_title, "bold": True, "size": 16, "color": self.secondary_color}]}]
        for pt in col2_points:
            c2_paras.append({"bullet": True, "runs": [{"text": pt, "bold": False, "size": 13, "color": "334155"}]})
        shapes.append({
            "type": "card", "x": 800000 + col_w + gap, "y": 1800000, "cx": col_w, "cy": 4400000,
            "fill": "FFFFFF", "border": "E2E8F0", "paras": c2_paras
        })
        self.slides.append({"type": "two_column", "title": title, "shapes": shapes})

    def add_metrics_slide(self, title: str, metrics: List[Dict[str, str]]):
        shapes = self.add_header_elements(title, "KEY BUSINESS IMPACT & METRICS")
        # 4 Metric Cards in 2x2 grid
        card_w = 5100000
        card_h = 2050000
        coords = [
            (800000, 1800000),
            (6292000, 1800000),
            (800000, 4150000),
            (6292000, 4150000)
        ]
        for i, m in enumerate(metrics[:4]):
            x, y = coords[i]
            val = m.get("value", "")
            lbl = m.get("label", "")
            desc = m.get("desc", "")
            shapes.append({
                "type": "card", "x": x, "y": y, "cx": card_w, "cy": card_h,
                "fill": "FFFFFF", "border": "E2E8F0",
                "paras": [
                    {"runs": [{"text": val, "bold": True, "size": 32, "color": self.accent_color}]},
                    {"runs": [{"text": f"\n{lbl}", "bold": True, "size": 15, "color": self.primary_color}]},
                    {"runs": [{"text": f"\n{desc}", "bold": False, "size": 12, "color": "64748B"}]}
                ]
            })
        self.slides.append({"type": "metrics", "title": title, "shapes": shapes})

    def add_table_slide(self, title: str, category: str, headers: List[str], rows: List[List[str]]):
        shapes = self.add_header_elements(title, category)
        # Summary description card with table data inside
        table_text_paras = [
            {"runs": [{"text": " | ".join(headers), "bold": True, "size": 13, "color": self.primary_color}]}
        ]
        for r in rows:
            table_text_paras.append({
                "runs": [{"text": "\n" + " | ".join(str(c) for c in r), "bold": False, "size": 12, "color": "334155"}]
            })
        shapes.append({
            "type": "card", "x": 800000, "y": 1800000, "cx": 10592000, "cy": 4400000,
            "fill": "FFFFFF", "border": "CBD5E1",
            "paras": table_text_paras
        })
        self.slides.append({"type": "table", "title": title, "shapes": shapes})

    def add_citations_slide(self, title: str, citations: List[Dict[str, str]]):
        shapes = self.add_header_elements(title, "PROVENANCE & CITATIONS")
        paras = [
            {"runs": [{"text": "Verified Reference Sources and Knowledge Traceability", "bold": True, "size": 14, "color": self.primary_color}]}
        ]
        for c in citations:
            cid = c.get("id", "")
            ctitle = c.get("title", "")
            curl = c.get("url", "")
            paras.append({
                "runs": [
                    {"text": f"\n{cid} ", "bold": True, "size": 12, "color": self.secondary_color},
                    {"text": f"{ctitle} — ", "bold": True, "size": 12, "color": "1E293B"},
                    {"text": f"{curl}", "bold": False, "size": 11, "color": "64748B"}
                ]
            })
        shapes.append({
            "type": "card", "x": 800000, "y": 1800000, "cx": 10592000, "cy": 4400000,
            "fill": "FFFFFF", "border": "E2E8F0", "paras": paras
        })
        self.slides.append({"type": "citations", "title": title, "shapes": shapes})

    def generate_slide_xml(self, slide_data: Dict[str, Any], slide_num: int) -> Tuple[List[Tuple[str, str, str]], str]:
        """Returns the slide relationships (layout first, then one per picture) and the slide XML."""
        rels: List[Tuple[str, str, str]] = [("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml")]
        image_rels: Dict[int, str] = {}
        shapes = list(slide_data.get("shapes", []))
        logo = self.logo_shape(slide_data.get("type", ""))
        if logo:
            shapes.append(logo)
        sp_elements = []
        # Background rect
        sp_elements.append(make_shape_xml(1, "Background", 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, [], fill_color=self.bg_color))
        
        sp_id = 2
        for shp in shapes:
            stype = shp.get("type", "rect")
            if stype == "picture":
                image = shp["image"]
                if image not in image_rels:
                    image_rels[image] = f"rId{len(rels) + 1}"
                    rels.append((image_rels[image], "image", f"../media/{self.media_name(image)}"))
                sp_elements.append(pptx_picture_xml(sp_id, shp.get("name", "Picture"), image_rels[image],
                                                    shp["x"], shp["y"], shp["cx"], shp["cy"]))
                sp_id += 1
                continue
            x = shp.get("x", 0)
            y = shp.get("y", 0)
            cx = shp.get("cx", 1000000)
            cy = shp.get("cy", 1000000)
            fill = shp.get("fill")
            border = shp.get("border")
            border_w = shp.get("border_w", 12700)
            paras = shp.get("paras", [])
            name = f"{shp['name']} {sp_id}" if shp.get("name") else f"Shape_{sp_id}"
            sp_elements.append(make_shape_xml(sp_id, name, x, y, cx, cy, paras, fill_color=fill, border_color=border, border_width=border_w, radius=10 if stype=="card" else None))
            sp_id += 1

        shapes_str = "\n".join(sp_elements)
        return rels, f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="{P_NS}" xmlns:a="{A_NS}" xmlns:r="{R_NS}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      {shapes_str}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>"""

    def build_bytes(self) -> bytes:
        slide_count = len(self.slides)
        buf = io.BytesIO()

        # [Content_Types].xml
        types_overrides = [
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            IMAGE_DEFAULTS,
            '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
            f'<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="{MASTER_CT}"/>',
            f'<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="{LAYOUT_CT}"/>',
            f'<Override PartName="/ppt/theme/theme1.xml" ContentType="{THEME_CT}"/>',
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        ]
        for i in range(1, slide_count + 1):
            types_overrides.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')

        content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  {"".join(types_overrides)}
</Types>"""

        # _rels/.rels
        pkg_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

        # ppt/presentation.xml (slides are rId1..N, then the master and the theme)
        master_rid, theme_rid = f"rId{slide_count + 1}", f"rId{slide_count + 2}"
        sld_id_list = []
        for i in range(1, slide_count + 1):
            sld_id_list.append(f'<p:sldId id="{255 + i}" r:id="rId{i}"/>')

        pres_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="{P_NS}" xmlns:a="{A_NS}" xmlns:r="{R_NS}">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="{master_rid}"/></p:sldMasterIdLst>
  <p:sldIdLst>
    {"".join(sld_id_list)}
  </p:sldIdLst>
  <p:sldSz cx="{SLIDE_WIDTH}" cy="{SLIDE_HEIGHT}"/>
  <p:notesSz cx="{SLIDE_HEIGHT}" cy="{SLIDE_WIDTH}"/>
</p:presentation>"""

        pres_rels = rels_xml([(f"rId{i}", "slide", f"slides/slide{i}.xml") for i in range(1, slide_count + 1)]
                             + [(master_rid, "slideMaster", "slideMasters/slideMaster1.xml"),
                                (theme_rid, "theme", "theme/theme1.xml")])

        core_props = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{escape(self.title)}</dc:title>
  <dc:creator>Enterprise Multi-Agent AI System</dc:creator>
  <cp:lastModifiedBy>PPT Generation Agent</cp:lastModifiedBy>
  <cp:revision>1</cp:revision>
</cp:coreProperties>"""

        app_props = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>Enterprise Multi-Agent DocuSynth</Application>
  <Slides>{slide_count}</Slides>
</Properties>"""

        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", pkg_rels)
            zf.writestr("ppt/presentation.xml", pres_xml)
            zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
            zf.writestr("docProps/core.xml", core_props)
            zf.writestr("docProps/app.xml", app_props)
            zf.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml())
            zf.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", rels_xml([
                ("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"), ("rId2", "theme", "../theme/theme1.xml")]))
            zf.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml())
            zf.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", rels_xml([
                ("rId1", "slideMaster", "../slideMasters/slideMaster1.xml")]))
            zf.writestr("ppt/theme/theme1.xml", theme_xml(self.primary_font, self.primary_color, self.secondary_color))
            for index, data in enumerate(self.images):
                zf.writestr(f"ppt/media/{self.media_name(index)}", data)

            for i, s_data in enumerate(self.slides, start=1):
                s_rels, s_xml = self.generate_slide_xml(s_data, i)
                zf.writestr(f"ppt/slides/slide{i}.xml", s_xml)
                zf.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", rels_xml(s_rels))

        return buf.getvalue()

    def save(self, filepath: str):
        data = self.build_bytes()
        with open(filepath, "wb") as f:
            f.write(data)


class PptxReader:
    """Parses PPTX presentations to extract slide count, titles, layout structures, and styling."""
    def __init__(self, file_source):
        if isinstance(file_source, str):
            with open(file_source, "rb") as f:
                self.bytes_data = f.read()
        else:
            self.bytes_data = file_source

    def extract_structure(self) -> Dict[str, Any]:
        result = {
            "slide_count": 0,
            "titles": [],
            "detected_fonts": [],
            "detected_colors": [],
            "slides_content": []
        }
        try:
            with zipfile.ZipFile(io.BytesIO(self.bytes_data)) as zf:
                slide_files = [n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
                # Sort numerically so slide10 comes after slide9
                slide_files.sort(key=lambda name: int(re.sub(r"\D", "", name)))
                result["slide_count"] = len(slide_files)

                for sf in slide_files:
                    s_xml = zf.read(sf).decode("utf-8", errors="ignore")
                    colors = re.findall(r'val="([0-9A-Fa-f]{6})"', s_xml)
                    result["detected_colors"].extend(colors)

                    tree = ET.fromstring(s_xml)
                    texts = []
                    for t in tree.iter(f"{{{A_NS}}}t"):
                        if t.text:
                            texts.append(t.text.strip())

                    slide_title = texts[0] if texts else f"Slide {len(result['titles'])+1}"
                    result["titles"].append(slide_title)
                    result["slides_content"].append({"title": slide_title, "text_snippets": texts[:5]})

        except Exception as e:
            result["error"] = str(e)

        result["detected_colors"] = [v for v, _ in Counter(result["detected_colors"]).most_common()]
        # Most frequent first, so the "primary" colour/font is the dominant one
        result["detected_fonts"] = [v for v, _ in Counter(result["detected_fonts"]).most_common()]
        return result
