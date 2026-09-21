"""
Pure-Python OpenXML DOCX Builder and Reader
Generates valid Microsoft Word (.docx) files adhering strictly to the ECMA-376 OpenXML standard.
"""
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from typing import List, Dict, Any, Optional

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

DOC_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

def get_styles_xml(primary_font="Georgia", heading_font="Arial", primary_color="1B365D", secondary_color="00A3E0"):
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="{primary_font}" w:hAnsi="{primary_font}" w:cs="{primary_font}"/>
        <w:sz w:val="22"/>
        <w:color w:val="222222"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:styleId="Normal" w:default="1">
    <w:name w:val="Normal"/>
    <w:pPr>
      <w:spacing w:line="276" w:lineRule="auto" w:after="160"/>
    </w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:pPr>
      <w:spacing w:before="360" w:after="160"/>
      <w:outlineLvl w:val="0"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{heading_font}" w:hAnsi="{heading_font}"/>
      <w:b/>
      <w:color w:val="{primary_color}"/>
      <w:sz w:val="44"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:pPr>
      <w:spacing w:before="240" w:after="120"/>
      <w:outlineLvl w:val="1"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{heading_font}" w:hAnsi="{heading_font}"/>
      <w:b/>
      <w:color w:val="{secondary_color}"/>
      <w:sz w:val="32"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:pPr>
      <w:spacing w:before="180" w:after="80"/>
      <w:outlineLvl w:val="2"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{heading_font}" w:hAnsi="{heading_font}"/>
      <w:b/>
      <w:color w:val="333333"/>
      <w:sz w:val="26"/>
    </w:rPr>
  </w:style>
</w:styles>"""

class DocxBuilder:
    def __init__(self, title: str = "Enterprise Proposal", primary_font: str = "Georgia", heading_font: str = "Arial",
                 primary_color: str = "1B365D", secondary_color: str = "00A3E0"):
        self.title = title
        self.primary_font = primary_font
        self.heading_font = heading_font
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.paragraphs_xml: List[str] = []

    def add_title_block(self, title: str, subtitle: Optional[str] = None, metadata: Optional[Dict[str, str]] = None):
        t_esc = escape(title)
        xml = f"""<w:p>
  <w:pPr>
    <w:spacing w:before="480" w:after="120"/>
    <w:jc w:val="center"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="{self.heading_font}" w:hAnsi="{self.heading_font}"/>
      <w:b/>
      <w:sz w:val="56"/>
      <w:color w:val="{self.primary_color}"/>
    </w:rPr>
    <w:t>{t_esc}</w:t>
  </w:r>
</w:p>"""
        self.paragraphs_xml.append(xml)

        if subtitle:
            sub_esc = escape(subtitle)
            sub_xml = f"""<w:p>
  <w:pPr>
    <w:spacing w:before="60" w:after="240"/>
    <w:jc w:val="center"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="{self.primary_font}" w:hAnsi="{self.primary_font}"/>
      <w:i/>
      <w:sz w:val="28"/>
      <w:color w:val="555555"/>
    </w:rPr>
    <w:t>{sub_esc}</w:t>
  </w:r>
</w:p>"""
            self.paragraphs_xml.append(sub_xml)

        if metadata:
            meta_items = " | ".join(f"{k}: {v}" for k, v in metadata.items())
            meta_esc = escape(meta_items)
            meta_xml = f"""<w:p>
  <w:pPr>
    <w:spacing w:before="120" w:after="360"/>
    <w:jc w:val="center"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:sz w:val="18"/>
      <w:color w:val="777777"/>
    </w:rPr>
    <w:t>{meta_esc}</w:t>
  </w:r>
</w:p>"""
            self.paragraphs_xml.append(meta_xml)

    def add_heading_1(self, text: str):
        t_esc = escape(text)
        xml = f"""<w:p>
  <w:pPr>
    <w:pStyle w:val="Heading1"/>
  </w:pPr>
  <w:r>
    <w:t>{t_esc}</w:t>
  </w:r>
</w:p>"""
        self.paragraphs_xml.append(xml)

    def add_heading_2(self, text: str):
        t_esc = escape(text)
        xml = f"""<w:p>
  <w:pPr>
    <w:pStyle w:val="Heading2"/>
  </w:pPr>
  <w:r>
    <w:t>{t_esc}</w:t>
  </w:r>
</w:p>"""
        self.paragraphs_xml.append(xml)

    def add_heading_3(self, text: str):
        t_esc = escape(text)
        xml = f"""<w:p>
  <w:pPr>
    <w:pStyle w:val="Heading3"/>
  </w:pPr>
  <w:r>
    <w:t>{t_esc}</w:t>
  </w:r>
</w:p>"""
        self.paragraphs_xml.append(xml)

    def add_paragraph(self, text: str, bold: bool = False, italic: bool = False, color: Optional[str] = None):
        t_esc = escape(text)
        rpr_parts = []
        if bold:
            rpr_parts.append("<w:b/>")
        if italic:
            rpr_parts.append("<w:i/>")
        if color:
            rpr_parts.append(f'<w:color w:val="{color}"/>')
        rpr_str = f"<w:rPr>{''.join(rpr_parts)}</w:rPr>" if rpr_parts else ""

        xml = f"""<w:p>
  <w:pPr>
    <w:spacing w:line="276" w:lineRule="auto" w:after="160"/>
  </w:pPr>
  <w:r>
    {rpr_str}
    <w:t>{t_esc}</w:t>
  </w:r>
</w:p>"""
        self.paragraphs_xml.append(xml)

    def add_callout(self, title: str, body: str, bg_color: str = "F1F5F9", border_color: str = "1B365D"):
        t_esc = escape(title)
        b_esc = escape(body)
        xml = f"""<w:tbl>
  <w:tblPr>
    <w:tblW w:w="9200" w:type="dxa"/>
    <w:tblBorders>
      <w:left w:val="single" w:sz="36" w:space="0" w:color="{border_color}"/>
      <w:top w:val="none"/>
      <w:right w:val="none"/>
      <w:bottom w:val="none"/>
    </w:tblBorders>
    <w:tblCellMar>
      <w:top w:w="180" w:type="dxa"/>
      <w:bottom w:w="180" w:type="dxa"/>
      <w:left w:w="240" w:type="dxa"/>
      <w:right w:w="240" w:type="dxa"/>
    </w:tblCellMar>
  </w:tblPr>
  <w:tr>
    <w:tc>
      <w:tcPr>
        <w:tcW w:w="9200" w:type="dxa"/>
        <w:shd w:val="clear" w:color="auto" w:fill="{bg_color}"/>
      </w:tcPr>
      <w:p>
        <w:pPr><w:spacing w:after="80"/></w:pPr>
        <w:r>
          <w:rPr><w:b/><w:color w:val="{border_color}"/><w:sz w:val="24"/></w:rPr>
          <w:t>{t_esc}</w:t>
        </w:r>
      </w:p>
      <w:p>
        <w:r>
          <w:rPr><w:sz w:val="20"/><w:color w:val="334155"/></w:rPr>
          <w:t>{b_esc}</w:t>
        </w:r>
      </w:p>
    </w:tc>
  </w:tr>
</w:tbl>"""
        self.paragraphs_xml.append(xml)

    def add_bullet(self, text: str, prefix: str = "• "):
        t_esc = escape(text)
        xml = f"""<w:p>
  <w:pPr>
    <w:ind w:left="480" w:hanging="240"/>
    <w:spacing w:after="100"/>
  </w:pPr>
  <w:r>
    <w:rPr><w:b/><w:color w:val="{self.primary_color}"/></w:rPr>
    <w:t>{prefix}</w:t>
  </w:r>
  <w:r>
    <w:t>{t_esc}</w:t>
  </w:r>
</w:p>"""
        self.paragraphs_xml.append(xml)

    def add_table(self, headers: List[str], rows: List[List[str]], col_widths: Optional[List[int]] = None):
        num_cols = len(headers)
        if not col_widths:
            w_per_col = int(9200 / num_cols)
            col_widths = [w_per_col] * num_cols

        # Header cells
        hdr_cells = []
        for i, h in enumerate(headers):
            h_esc = escape(h)
            hdr_cells.append(f"""<w:tc>
  <w:tcPr>
    <w:tcW w:w="{col_widths[i]}" w:type="dxa"/>
    <w:shd w:val="clear" w:color="auto" w:fill="{self.primary_color}"/>
  </w:tcPr>
  <w:p>
    <w:pPr><w:jc w:val="left"/><w:spacing w:after="60" w:before="60"/></w:pPr>
    <w:r>
      <w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="20"/></w:rPr>
      <w:t>{h_esc}</w:t>
    </w:r>
  </w:p>
</w:tc>""")

        hdr_row_xml = f"<w:tr><w:trPr><w:tblHeader/></w:trPr>{''.join(hdr_cells)}</w:tr>"

        body_rows = []
        for r_idx, row in enumerate(rows):
            fill_color = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
            r_cells = []
            for c_idx, cell in enumerate(row):
                c_esc = escape(str(cell))
                c_w = col_widths[c_idx] if c_idx < len(col_widths) else 2000
                r_cells.append(f"""<w:tc>
  <w:tcPr>
    <w:tcW w:w="{c_w}" w:type="dxa"/>
    <w:shd w:val="clear" w:color="auto" w:fill="{fill_color}"/>
  </w:tcPr>
  <w:p>
    <w:pPr><w:spacing w:after="60" w:before="60"/></w:pPr>
    <w:r>
      <w:rPr><w:sz w:val="19"/><w:color w:val="222222"/></w:rPr>
      <w:t>{c_esc}</w:t>
    </w:r>
  </w:p>
</w:tc>""")
            body_rows.append(f"<w:tr>{''.join(r_cells)}</w:tr>")

        tbl_xml = f"""<w:tbl>
  <w:tblPr>
    <w:tblW w:w="9200" w:type="dxa"/>
    <w:tblBorders>
      <w:top w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
      <w:left w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
      <w:bottom w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
      <w:right w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
      <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
      <w:insideV w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
    </w:tblBorders>
    <w:tblCellMar>
      <w:top w:w="120" w:type="dxa"/>
      <w:bottom w:w="120" w:type="dxa"/>
      <w:left w:w="160" w:type="dxa"/>
      <w:right w:w="160" w:type="dxa"/>
    </w:tblCellMar>
  </w:tblPr>
  {hdr_row_xml}
  {''.join(body_rows)}
</w:tbl>"""
        self.paragraphs_xml.append(tbl_xml)

    def prepend_executive_summary(self, summary_text: str):
        # Insert callout at index right after title block (index 2 or 3)
        t_esc = escape("Executive Summary (Updated)")
        b_esc = escape(summary_text)
        xml = f"""<w:tbl>
  <w:tblPr>
    <w:tblW w:w="9200" w:type="dxa"/>
    <w:tblBorders>
      <w:left w:val="single" w:sz="36" w:space="0" w:color="{self.primary_color}"/>
      <w:top w:val="none"/>
      <w:right w:val="none"/>
      <w:bottom w:val="none"/>
    </w:tblBorders>
    <w:tblCellMar>
      <w:top w:w="180" w:type="dxa"/>
      <w:bottom w:w="180" w:type="dxa"/>
      <w:left w:w="240" w:type="dxa"/>
      <w:right w:w="240" w:type="dxa"/>
    </w:tblCellMar>
  </w:tblPr>
  <w:tr>
    <w:tc>
      <w:tcPr>
        <w:tcW w:w="9200" w:type="dxa"/>
        <w:shd w:val="clear" w:color="auto" w:fill="F8FAFC"/>
      </w:tcPr>
      <w:p>
        <w:pPr><w:spacing w:after="80"/></w:pPr>
        <w:r>
          <w:rPr><w:b/><w:color w:val="{self.primary_color}"/><w:sz w:val="24"/></w:rPr>
          <w:t>{t_esc}</w:t>
        </w:r>
      </w:p>
      <w:p>
        <w:r>
          <w:rPr><w:sz w:val="20"/><w:color w:val="334155"/></w:rPr>
          <w:t>{b_esc}</w:t>
        </w:r>
      </w:p>
    </w:tc>
  </w:tr>
</w:tbl>"""
        insert_idx = min(3, len(self.paragraphs_xml))
        self.paragraphs_xml.insert(insert_idx, xml)

    def build_bytes(self) -> bytes:
        body_content = "\n".join(self.paragraphs_xml)
        document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}">
  <w:body>
    {body_content}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""

        styles_xml = get_styles_xml(self.primary_font, self.heading_font, self.primary_color, self.secondary_color)
        core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{escape(self.title)}</dc:title>
  <dc:creator>Enterprise Multi-Agent AI System</dc:creator>
  <cp:lastModifiedBy>Supervisor Agent</cp:lastModifiedBy>
  <cp:revision>1</cp:revision>
</cp:coreProperties>"""

        app_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Template>Normal.dotm</Template>
  <Application>Enterprise Multi-Agent DocuSynth</Application>
</Properties>"""

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
            zf.writestr("_rels/.rels", RELS_XML)
            zf.writestr("word/_rels/document.xml.rels", DOC_RELS_XML)
            zf.writestr("word/styles.xml", styles_xml)
            zf.writestr("word/document.xml", document_xml)
            zf.writestr("docProps/core.xml", core_xml)
            zf.writestr("docProps/app.xml", app_xml)

        return buf.getvalue()

    def save(self, filepath: str):
        data = self.build_bytes()
        with open(filepath, "wb") as f:
            f.write(data)


class DocxReader:
    """Extracts text, hierarchy, headings, and font/palette styling from DOCX packages."""
    def __init__(self, file_source):
        if isinstance(file_source, str):
            with open(file_source, "rb") as f:
                self.bytes_data = f.read()
        else:
            self.bytes_data = file_source

    def extract_structure(self) -> Dict[str, Any]:
        result = {
            "title": "",
            "headings": [],
            "paragraphs": [],
            "tables": [],
            "detected_fonts": set(),
            "detected_colors": set(),
            "word_count": 0
        }
        try:
            with zipfile.ZipFile(io.BytesIO(self.bytes_data)) as zf:
                # Styles
                if "word/styles.xml" in zf.namelist():
                    styles_xml = zf.read("word/styles.xml").decode("utf-8", errors="ignore")
                    fonts = re.findall(r'w:ascii="([^"]+)"', styles_xml)
                    colors = re.findall(r'w:color w:val="([0-9A-Fa-f]{6})"', styles_xml)
                    result["detected_fonts"].update(fonts)
                    result["detected_colors"].update(colors)

                # Document content
                if "word/document.xml" in zf.namelist():
                    doc_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
                    # Text extraction
                    tree = ET.fromstring(doc_xml)
                    text_parts = []
                    for p in tree.iter(f"{{{W_NS}}}p"):
                        p_text = "".join(p.itertext()).strip()
                        if not p_text:
                            continue
                        text_parts.append(p_text)
                        # Check if heading
                        pstyle = p.find(f".//{{{W_NS}}}pStyle")
                        if pstyle is not None:
                            val = pstyle.attrib.get(f"{{{W_NS}}}val") or pstyle.attrib.get("w:val") or pstyle.attrib.get("val", "")
                            if "heading" in val.lower():
                                result["headings"].append((val, p_text))
                        elif not result["title"] and len(p_text) < 120:
                            result["title"] = p_text

                    # Color search in document.xml
                    doc_colors = re.findall(r'w:color w:val="([0-9A-Fa-f]{6})"', doc_xml)
                    result["detected_colors"].update(doc_colors)

                    result["paragraphs"] = text_parts
                    result["word_count"] = sum(len(p.split()) for p in text_parts)
                    result["headings_count"] = len(result["headings"])

                # Core properties
                if "docProps/core.xml" in zf.namelist():
                    core_xml = zf.read("docProps/core.xml").decode("utf-8", errors="ignore")
                    t_match = re.search(r'<dc:title>([^<]+)</dc:title>', core_xml)
                    if t_match and not result["title"]:
                        result["title"] = t_match.group(1)

        except Exception as e:
            result["error"] = str(e)

        result["detected_fonts"] = list(result["detected_fonts"])
        result["detected_colors"] = list(result["detected_colors"])
        return result
