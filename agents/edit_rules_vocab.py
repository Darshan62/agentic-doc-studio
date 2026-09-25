"""
Vocabulary and small extractors used by the rule-based edit parser: ordinals, fonts, colours,
sizes, resize amounts and move directions.
"""
import re
from typing import Any, Dict, Optional

from core.edit_schema import NAMED_COLORS

ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
            "eighth": 8, "ninth": 9, "tenth": 10, "last": -1, "final": -1, "1st": 1, "2nd": 2, "3rd": 3,
            "4th": 4, "5th": 5, "6th": 6, "7th": 7, "8th": 8, "9th": 9, "10th": 10}
ORDINAL_WORDS = "|".join(sorted(ORDINALS, key=len, reverse=True))

KNOWN_FONTS = ["Arial", "Arial Black", "Arial Narrow", "Calibri", "Calibri Light", "Cambria", "Candara", "Consolas",
               "Constantia", "Corbel", "Courier New", "Georgia", "Garamond", "Helvetica", "Impact", "Lato",
               "Montserrat", "Open Sans", "Roboto", "Segoe UI", "Tahoma", "Times New Roman", "Trebuchet MS",
               "Verdana", "Aptos", "Aptos Display", "Century Gothic", "Gill Sans", "Palatino", "Book Antiqua",
               "Franklin Gothic", "Inter", "Poppins", "Source Sans Pro", "Comic Sans MS", "Lucida Sans", "Futura",
               "Baskerville", "Rockwell", "Didot", "Nunito", "Raleway", "Merriweather", "Playfair Display"]
_FONT_PATTERN = re.compile(r"\b(" + "|".join(re.escape(f) for f in sorted(KNOWN_FONTS, key=len, reverse=True))
                           + r")\b", re.IGNORECASE)
_GENERIC_FONT = re.compile(r"\bfont\b(?!\s+(?:size|colou?r|style|weight))(?:\s+(?:family|face))?\s+(?:to|as|into|=)\s+"
                           r"([A-Za-z][\w\- ]{0,40}?)(?=\s*(?:,|;|\.|\band\b|\bwith\b|\bat\b|\d|$))", re.IGNORECASE)
_COLOR_PATTERN = re.compile(r"(#[0-9a-f]{6}\b|\b(?:" + "|".join(re.escape(c) for c in sorted(NAMED_COLORS, key=len, reverse=True))
                            + r")\b)", re.IGNORECASE)
_SIZE_PATTERNS = [re.compile(r"(\d+(?:\.\d+)?)\s*(?:pt|pts|point|points)\b", re.IGNORECASE),
                  re.compile(r"\bsize\s*(?:to|of|=|:|at)?\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE)]
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent\b)", re.IGNORECASE)
_DISTANCE = re.compile(r"(\d+(?:\.\d+)?)\s*(in|inch|inches|cm|mm|pt|points|px|pixels)\b", re.IGNORECASE)
UNIT_INCHES = {"in": 1, "inch": 1, "inches": 1, "cm": 1 / 2.54, "mm": 1 / 25.4, "pt": 1 / 72, "points": 1 / 72,
               "px": 1 / 96, "pixels": 1 / 96}
SLIGHT_INCHES, DEFAULT_MOVE_INCHES, LARGE_MOVE_INCHES = 0.25, 0.5, 1.0


def ordinal_before(text: str, noun: str) -> Optional[int]:
    """'the third bullet' -> 3, 'bullet 4' -> 4, 'the last paragraph' -> -1."""
    match = re.search(rf"\b({ORDINAL_WORDS})\s+(?:\w+\s+)?{noun}", text)
    if match:
        return ORDINALS[match.group(1)]
    match = re.search(rf"\b{noun}\s*(?:number\s*|no\.?\s*|#\s*)?(\d+)\b", text)
    return int(match.group(1)) if match else None


def slide_number(text: str) -> Optional[int]:
    match = re.search(r"\bslide\s*(?:number\s*|no\.?\s*|#\s*)?(\d+)\b", text)
    if match:
        return int(match.group(1))
    match = re.search(rf"\b({ORDINAL_WORDS})\s+slide\b", text)
    return ORDINALS[match.group(1)] if match and ORDINALS[match.group(1)] > 0 else None


def find_font(raw: str) -> Optional[str]:
    match = _FONT_PATTERN.search(raw)
    if match:
        return next(f for f in KNOWN_FONTS if f.lower() == match.group(1).lower())
    match = _GENERIC_FONT.search(raw)
    if match and match.group(1).strip().lower() not in {"the", "a", "bold", "italic", "bigger", "smaller"}:
        return match.group(1).strip().title() if match.group(1).islower() else match.group(1).strip()
    return None


def find_color(raw: str) -> Optional[str]:
    match = _COLOR_PATTERN.search(raw)
    return match.group(1).lower() if match else None


def find_size(raw: str) -> Optional[float]:
    for pattern in _SIZE_PATTERNS:
        match = pattern.search(raw)
        if match:
            return float(match.group(1))
    return None


def find_toggle(low: str, word: str) -> Optional[bool]:
    stem = {"bold": r"bold", "italic": r"italic(?:s|ize|ized)?", "underline": r"underlin(?:e|ed)"}[word]
    if re.search(rf"\b(?:un-?{stem}|not\s+{stem}|no\s+{stem}|remove\s+(?:the\s+)?{stem}|without\s+{stem})\b", low):
        return False
    return True if re.search(rf"\b{stem}\b", low) else None


def find_align(low: str) -> Optional[str]:
    if re.search(r"\b(center|centre|centered|centred|middle)\b", low) and not re.search(r"\bmove\b", low):
        return "center"
    for side in ("left", "right"):
        if re.search(rf"\b(?:align(?:ed)?\s+(?:to\s+the\s+)?{side}|{side}[- ]align(?:ed)?)\b", low):
            return side
    return "justify" if re.search(r"\bjustif(?:y|ied)\b", low) else None


def find_scale(low: str) -> Optional[float]:
    percent = _PERCENT.search(low)
    if percent:
        value = float(percent.group(1)) / 100
        if re.search(r"\bby\s+\d", low):
            return 1 - value if re.search(r"smaller|reduce|shrink|decrease|down", low) else 1 + value
        return value
    if re.search(r"\bhalf\b", low):
        return 0.5
    if re.search(r"\b(double|twice)\b", low):
        return 2.0
    slight = re.search(r"\b(slightly|a bit|a little|a touch)\b", low)
    much = re.search(r"\b(much|a lot|way|significantly)\b", low)
    if re.search(r"\b(smaller|shrink|reduce|decrease)\b", low):
        return 0.9 if slight else (0.6 if much else 0.8)
    if re.search(r"\b(bigger|larger|enlarge|increase|grow)\b", low):
        return 1.1 if slight else (1.5 if much else 1.25)
    return None


def find_move(low: str) -> Optional[Dict[str, Any]]:
    corner = re.search(r"\bto\s+(?:the\s+)?(top|bottom)?[\s-]*(left|right)?\s*(corner|side|edge)?\b", low)
    # "to the right" alone is a direction; "to the top right (corner)" or "to the left edge" is a place
    is_place = corner is not None and bool(corner.group(1) or (corner.group(2) and corner.group(3)))
    if corner is not None and is_place and not re.search(r"\b(slightly|a bit|a little|by)\b", low):
        spot = "-".join(filter(None, [corner.group(1), corner.group(2)]))
        return {"to": spot}
    if re.search(r"\bto\s+the\s+(center|centre|middle)\b", low):
        return {"to": "center"}
    distance = _DISTANCE.search(low)
    amount = float(distance.group(1)) * UNIT_INCHES[distance.group(2).lower()] if distance else (
        SLIGHT_INCHES if re.search(r"\b(slightly|a bit|a little|a touch|nudge)\b", low)
        else LARGE_MOVE_INCHES if re.search(r"\b(a lot|far|much)\b", low) else DEFAULT_MOVE_INCHES)
    dx = amount if re.search(r"\bright\b", low) else (-amount if re.search(r"\bleft\b", low) else 0)
    dy = amount if re.search(r"\b(down|lower|downward)\b", low) else (-amount if re.search(r"\b(up|higher|upward)\b", low) else 0)
    if not dx and not dy:
        return None
    return {"dx_inches": round(dx, 3), "dy_inches": round(dy, 3)}
