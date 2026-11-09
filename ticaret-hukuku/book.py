# -*- coding: utf-8 -*-
"""Tasarım belirteçleri, font kaydı, stiller ve satır içi işaretleme."""
import os
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

# renkler
NAVY   = HexColor("#12233B")
NAVY2  = HexColor("#1B3252")
INK    = HexColor("#1B2430")
GREY   = HexColor("#6B7280")
MUTED  = HexColor("#9AA0A6")
RULE   = HexColor("#E3DED3")
RULE2  = HexColor("#EFEAE0")
GOLD   = HexColor("#B08432")
GOLD_L = HexColor("#F3E7CE")
TEAL   = HexColor("#2C6B63")
TEAL_L = HexColor("#EAF2F0")
RED    = HexColor("#8C3B32")
RED_L  = HexColor("#F8EEEC")
PURP   = HexColor("#4B4470")
PURP_L = HexColor("#EFEDF7")
TINT   = HexColor("#F8F6F0")
PAPER  = colors.white

# sayfa ölçüsü
PAGE_W, PAGE_H = 595.2756, 841.8898
M_TOP  = 46.0
M_BOT  = 42.0
M_OUT  = 38.0
M_IN   = 52.0
GUTTER = 21.0
COL_W  = (PAGE_W - M_OUT - M_IN - GUTTER) / 2.0

TR_UP = {"i": "İ", "ı": "I", "ğ": "Ğ", "ü": "Ü", "ş": "Ş", "ö": "Ö", "ç": "Ç", "â": "Â"}
TR_LOW = {"İ": "i", "I": "ı", "Ğ": "ğ", "Ü": "ü", "Ş": "ş", "Ö": "ö", "Ç": "ç", "Â": "â"}


def tr_upper(t):
    return "".join(TR_UP.get(c, c.upper()) for c in t)


def tr_lower(t):
    return "".join(TR_LOW.get(c, c.lower()) for c in t)


TR_ORDER = "aâbcçdefgğhıiîjklmnoöprsştuüûvyz"
_TR_RANK = {c: i for i, c in enumerate(TR_ORDER)}


def tr_key(t):
    t = tr_lower(t)
    out = []
    for c in t:
        out.append((_TR_RANK.get(c, 140), c))
    return out


def register():
    for name, f in [
        ("Body", "SSerif-Regular.ttf"), ("Body-It", "SSerif-Italic.ttf"),
        ("Body-SB", "SSerif-Semibold.ttf"), ("Body-B", "SSerif-Bold.ttf"),
        ("Body-SBI", "SSerif-SemiboldItalic.ttf"),
        ("Sans", "Inter-Regular.ttf"), ("Sans-M", "Inter-Medium.ttf"),
        ("Sans-SB", "Inter-SemiBold.ttf"), ("Sans-B", "Inter-Bold.ttf"),
        ("Sans-EB", "Inter-ExtraBold.ttf"),
    ]:
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, f)))
    for fam, faces in [
        ("Body", ("Body", "Body-B", "Body-It", "Body-BI")),
        ("Sans", ("Sans", "Sans-B", "Sans", "Sans-B")),
    ]:
        try:
            pdfmetrics.registerFontFamily(fam, normal=faces[0], bold=faces[1],
                                          italic=faces[2], boldItalic=faces[3])
        except Exception:
            pass


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(t):
    """**kalın**, _italik_, `kod` ve 12.345 gibi sayıları biçimler."""
    import re
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r'<font name="Body-SB">\1</font>', t)
    t = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r'<font name="Body-It">\1</font>', t)
    t = re.sub(r"`(.+?)`", r'<font name="Sans-M" size="7.6" color="#12233B">\1</font>', t)
    return t


def styles():
    S = {}
    S["body"] = ParagraphStyle("body", fontName="Body", fontSize=9.0, leading=12.3,
                               textColor=INK, alignment=TA_JUSTIFY, spaceAfter=3.4,
                               hyphenationLang="", splitLongWords=1)
    S["front_body"] = ParagraphStyle("front_body", parent=S["body"], fontSize=9.15,
                                     leading=12.7, spaceAfter=3.6)
    S["lead"] = ParagraphStyle("lead", fontName="Body", fontSize=9.8, leading=13.6,
                               textColor=HexColor("#3B4657"), alignment=TA_JUSTIFY,
                               spaceAfter=4.0)
    S["h2"] = ParagraphStyle("h2", fontName="Sans-SB", fontSize=11.6, leading=13.8,
                             textColor=NAVY, spaceBefore=1.0, spaceAfter=3.2,
                             keepWithNext=1)
    S["h3"] = ParagraphStyle("h3", fontName="Sans-SB", fontSize=9.2, leading=11.6,
                             textColor=TEAL, spaceBefore=4.4, spaceAfter=2.0,
                             keepWithNext=1)
    S["front_h"] = ParagraphStyle("front_h", fontName="Sans-SB", fontSize=12.6,
                                  leading=15.0, textColor=NAVY, spaceBefore=2,
                                  spaceAfter=4.6)
    S["kicker"] = ParagraphStyle("kicker", fontName="Sans-B", fontSize=7.2, leading=9.0,
                                 textColor=GOLD, spaceAfter=2.6)
    S["display"] = ParagraphStyle("display", fontName="Sans-SB", fontSize=34, leading=36,
                                  textColor=NAVY, spaceAfter=6)
    S["caption"] = ParagraphStyle("caption", fontName="Sans-M", fontSize=6.9, leading=8.8,
                                  textColor=GREY, spaceBefore=1.2, spaceAfter=2.4)
    S["table"] = ParagraphStyle("table", fontName="Body", fontSize=7.65, leading=9.4,
                                textColor=INK, alignment=TA_LEFT)
    S["table_h"] = ParagraphStyle("table_h", fontName="Sans-SB", fontSize=6.9,
                                  leading=8.4, textColor=colors.white)
    S["bullet"] = ParagraphStyle("bullet", parent=S["body"], leftIndent=9.5,
                                 bulletIndent=0.8, spaceAfter=2.2)
    S["bullet2"] = ParagraphStyle("bullet2", parent=S["body"], leftIndent=18.0,
                                  bulletIndent=10.0, fontSize=8.7, spaceAfter=1.8)
    S["num"] = ParagraphStyle("num", parent=S["body"], leftIndent=13.0, bulletIndent=0.8,
                              spaceAfter=2.2)
    S["box_lbl"] = ParagraphStyle("box_lbl", fontName="Sans-B", fontSize=6.5,
                                  leading=8.0, textColor=GREY)
    S["box_body"] = ParagraphStyle("box_body", fontName="Body", fontSize=8.4,
                                   leading=11.3, textColor=INK, alignment=TA_JUSTIFY,
                                   spaceAfter=2.4)
    S["toc_c"] = ParagraphStyle("toc_c", fontName="Sans-SB", fontSize=8.6, leading=11.0,
                                textColor=NAVY, spaceBefore=5.5, spaceAfter=2.2)
    S["toc_i"] = ParagraphStyle("toc_i", fontName="Body", fontSize=7.4, leading=9.4,
                                textColor=INK, leftIndent=10, firstLineIndent=-10,
                                spaceAfter=0.6)
    S["note_lbl"] = ParagraphStyle("note_lbl", fontName="Sans-B", fontSize=6.4,
                                   leading=8, textColor=GOLD)
    S["small"] = ParagraphStyle("small", fontName="Sans", fontSize=6.9, leading=9.2,
                                textColor=GREY)
    S["quote"] = ParagraphStyle("quote", fontName="Body-It", fontSize=11.5, leading=15.5,
                                textColor=HexColor("#E8D9B8"))
    return S
