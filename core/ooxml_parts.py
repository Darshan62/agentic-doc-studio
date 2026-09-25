"""
Static OOXML parts shared by the DOCX/PPTX builders.

PowerPoint refuses a deck without a slide master, a slide layout and a theme ("the file is
corrupted"), so every generated .pptx gets this minimal blank master/layout/theme set.
"""
from xml.sax.saxutils import escape

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
EMPTY_TREE = ('<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
              '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
              '<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>')

MASTER_CT = "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"
LAYOUT_CT = "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"
THEME_CT = "application/vnd.openxmlformats-officedocument.theme+xml"
IMAGE_DEFAULTS = ('<Default Extension="png" ContentType="image/png"/>'
                  '<Default Extension="jpeg" ContentType="image/jpeg"/>'
                  '<Default Extension="jpg" ContentType="image/jpeg"/>')


def rels_xml(rels: list) -> str:
    """rels: [(rel_id, type_suffix, target)]"""
    items = "".join(f'<Relationship Id="{rid}" Type="{REL_TYPE}/{kind}" Target="{target}"/>'
                    for rid, kind, target in rels)
    return f'{HEADER}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{items}</Relationships>'


def theme_xml(font: str = "Arial", dark: str = "0F2D59", accent: str = "2563EB") -> str:
    fill = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    line = f'<a:ln w="9525">{fill}</a:ln>'
    effect = "<a:effectStyle><a:effectLst/></a:effectStyle>"
    font = escape(font, {'"': "&quot;"})
    return (f'{HEADER}<a:theme xmlns:a="{A_NS}" name="DocuSynth"><a:themeElements>'
            '<a:clrScheme name="DocuSynth">'
            '<a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
            f'<a:dk2><a:srgbClr val="{dark}"/></a:dk2><a:lt2><a:srgbClr val="E7E6E6"/></a:lt2>'
            f'<a:accent1><a:srgbClr val="{accent}"/></a:accent1><a:accent2><a:srgbClr val="ED7D31"/></a:accent2>'
            '<a:accent3><a:srgbClr val="A5A5A5"/></a:accent3><a:accent4><a:srgbClr val="FFC000"/></a:accent4>'
            '<a:accent5><a:srgbClr val="5B9BD5"/></a:accent5><a:accent6><a:srgbClr val="70AD47"/></a:accent6>'
            '<a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink>'
            '</a:clrScheme>'
            f'<a:fontScheme name="DocuSynth"><a:majorFont><a:latin typeface="{font}"/><a:ea typeface=""/>'
            f'<a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="{font}"/><a:ea typeface=""/>'
            '<a:cs typeface=""/></a:minorFont></a:fontScheme>'
            f'<a:fmtScheme name="DocuSynth"><a:fillStyleLst>{fill * 3}</a:fillStyleLst>'
            f'<a:lnStyleLst>{line * 3}</a:lnStyleLst><a:effectStyleLst>{effect * 3}</a:effectStyleLst>'
            f'<a:bgFillStyleLst>{fill * 3}</a:bgFillStyleLst></a:fmtScheme>'
            '</a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>')


def slide_master_xml() -> str:
    return (f'{HEADER}<p:sldMaster xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:p="{P_NS}">'
            '<p:cSld><p:bg><p:bgPr><a:solidFill><a:schemeClr val="bg1"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
            f'<p:spTree>{EMPTY_TREE}</p:spTree></p:cSld>'
            '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
            'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
            '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
            '<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="3200"/></a:lvl1pPr></p:titleStyle>'
            '<p:bodyStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:bodyStyle>'
            '<p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:otherStyle></p:txStyles>'
            '</p:sldMaster>')


def slide_layout_xml() -> str:
    return (f'{HEADER}<p:sldLayout xmlns:a="{A_NS}" xmlns:r="{R_NS}" xmlns:p="{P_NS}" type="blank" preserve="1">'
            f'<p:cSld name="Blank"><p:spTree>{EMPTY_TREE}</p:spTree></p:cSld>'
            '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')


def pptx_picture_xml(shape_id: int, name: str, rel_id: str, x: int, y: int, cx: int, cy: int) -> str:
    name = escape(name, {'"': "&quot;"})
    return (f'<p:pic><p:nvPicPr><p:cNvPr id="{shape_id}" name="{name}" descr="{name}"/>'
            '<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')


def docx_picture_xml(pic_id: int, name: str, rel_id: str, cx: int, cy: int) -> str:
    name = escape(name, {'"': "&quot;"})
    return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{pic_id}" name="{name}" descr="{name}"/>'
            f'<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="{A_NS}" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            f'<a:graphic xmlns:a="{A_NS}"><a:graphicData uri="{PIC_NS}"><pic:pic xmlns:pic="{PIC_NS}">'
            f'<pic:nvPicPr><pic:cNvPr id="{pic_id}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
            '</wp:inline></w:drawing></w:r>')
