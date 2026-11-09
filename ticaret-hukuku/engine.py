# -*- coding: utf-8 -*-
"""Akış öğeleri (kutu, künye, kapaq), ayrıştırıcı ve belge şablonu."""
import os, re
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Paragraph, Spacer, Table, TableStyle, Flowable,
                                PageBreak, NextPageTemplate, FrameBreak, CondPageBreak,
                                KeepTogether, BaseDocTemplate, PageTemplate, Frame)
from reportlab.pdfbase import pdfmetrics
from book import *  # noqa

CONTENT = os.path.join(HERE, "content")

WEEK_ITEMS = [
    ("D1", "22 EYLÜL", "Kapsam · yöntem"),
    ("D2", "29 EYLÜL", "Sistemler"),
    ("D3", "29 EYLÜL", "Ticari iş"),
    ("D4", "6 EKİM", "Faiz"),
    ("D5", "13 EKİM", "Dava · işletme"),
    ("D6", "20 EKİM", "Şube · devir"),
    ("D7", "27 EKİM", "Birleşme"),
    ("D8", "SON DERS", "Tacir · şirket"),
]

QA_N = [0]
DEFERRED_TOC = []
TOC_SEQ = [0]
PAGES_LABEL = ["SAYFA"]

BOX_STYLE = {
    "kural":      (NAVY, HexColor("#F2F4F8"), "KURAL"),
    "tanim":      (NAVY, HexColor("#F2F4F8"), "TANIM"),
    "ornek":      (TEAL, TEAL_L, "ÖRNEK OLAY"),
    "tuzak":      (RED, RED_L, "SINAV TUZAĞI"),
    "karsilastir": (PURP, PURP_L, "KARŞILAŞTIR"),
    "belirsiz":   (GREY, HexColor("#F4F3F0"), "KAYITTA NET DEĞİL"),
    "ozet":       (GOLD, HexColor("#FBF5E8"), "ÜÇ CÜMLEDE"),
}


# ------------------------------------------------------------------ flowables
class Rule(Flowable):
    def __init__(self, width, color=RULE, t=0.5, pad=3.0):
        Flowable.__init__(self)
        self.width, self.color, self.t, self.pad = width, color, t, pad
        self.height = t + pad * 2

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setStrokeColor(self.color)
        c.setLineWidth(self.t)
        c.line(0, self.pad, self.width, self.pad)


class KeepGroup(Flowable):
    """Öğeleri bölmeden taşır: sığmıyorsa sütunu atlar (CondPageBreak'in aksine
    kırılma, başlık ile tablo arasına girmez)."""
    def __init__(self, items, max_total=726):
        Flowable.__init__(self)
        self.items = [f for f in items if f is not None]
        self.max_total = max_total
        self.width = 0
        self.height = 0
        self._hs = []

    def wrap(self, aw, ah):
        self.width = aw
        hs = []
        for f in self.items:
            try:
                hs.append(f.wrap(aw, ah)[1])
            except Exception:
                hs.append(0)
        self._hs = hs
        h = sum(hs)
        self.height = h
        if h > ah and h <= self.max_total and ah > 150:
            return aw, ah + 1          # sığmıyor: bir sonraki sütuna
        return aw, h

    def split(self, aw, ah):
        return []                       # bölünmez

    def draw(self):
        c = self.canv
        y = self.height
        for f, h in zip(self.items, self._hs):
            y -= h
            if isinstance(f, Heading):
                TOC_SEQ[0] += 1
                lvl, txt = f._toc
                DEFERRED_TOC.append((TOC_SEQ[0], lvl, txt, c.getPageNumber()))
                try:
                    key = "k%d" % TOC_SEQ[0]
                    c.bookmarkPage(key)
                    c.addOutlineEntry(txt, key, level=min(lvl, 2), closed=True)
                except Exception:
                    pass
            f.drawOn(c, 0, y)


class Heading(Paragraph):
    def __init__(self, text, style, level, plain):
        Paragraph.__init__(self, text, style)
        self._toc = (level, plain)


class ChapterHead(Flowable):
    """Tam genişlikte lacivert bölüm kapağı."""
    def __init__(self, code, kicker, title, lede, width, height=104):
        Flowable.__init__(self)
        self.code, self.kicker, self.title, self.lede = code, kicker, title, lede
        self.width, self.height = width, height

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.setFillColor(NAVY)
        c.rect(0, 0, w, h, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(0, h - 3.2, w, 3.2, stroke=0, fill=1)
        c.saveState()
        pth = c.beginPath()
        pth.rect(0, 0, w, h)
        c.clipPath(pth, stroke=0, fill=0)
        c.setFillColor(HexColor("#1B3252"))
        c.circle(w - 34, -6, 66, stroke=0, fill=1)
        c.setFillColor(HexColor("#22374F"))
        c.circle(w - 34, -6, 46, stroke=0, fill=1)
        c.restoreState()
        x = 16
        c.setFillColor(GOLD)
        c.setFont("Sans-B", 7.6)
        c.drawString(x, h - 26, self.code)
        c.setFillColor(HexColor("#8FA3BC"))
        c.setFont("Sans-M", 7.0)
        kw = pdfmetrics.stringWidth(self.code, "Sans-B", 7.6)
        c.drawString(x + kw + 7, h - 26, self.kicker)
        c.setFillColor(colors.white)
        title = self.title
        size = 21.5
        avail = w - 62
        while size > 13.5 and pdfmetrics.stringWidth(title, "Sans-SB", size) > avail:
            size -= 0.5
        c.setFont("Sans-SB", size)
        c.drawString(x, h - 54, title)
        c.setFillColor(HexColor("#AFC0D4"))
        c.setFont("Body", 8.6)
        lede = self.lede or ""
        maxw = w - 40
        words, line, lines = lede.split(), "", []
        for wd in words:
            t = (line + " " + wd).strip()
            if pdfmetrics.stringWidth(t, "Body", 8.6) > maxw:
                lines.append(line); line = wd
            else:
                line = t
        if line:
            lines.append(line)
        yy = h - 71
        for ln in lines[:2]:
            c.drawString(x, yy, ln)
            yy -= 11.6


class Box(Flowable):
    """Sol renkli şeritli, hafif zeminli bilgi kutusu."""
    def __init__(self, kind, title, body, width):
        Flowable.__init__(self)
        self.kind, self.title, self.body, self.width = kind, title, body, width
        self.bar, self.bg, self.label = BOX_STYLE.get(kind, BOX_STYLE["kural"])
        self.pad_l, self.pad_t, self.pad_b = 9.0, 6.4, 6.0

    def wrap(self, aw, ah):
        inner = self.width - self.pad_l - 7
        self._items = []
        y = 0
        lbl = Paragraph('<font name="Sans-B" size="6.3" color="%s">%s</font>'
                        % (self.bar.hexval().replace("0x", "#")[:7],
                           tr_upper(self.title or self.label)), S0)
        self._lbl = lbl
        lh = lbl.wrap(inner, ah)[1]
        y += lh + 3.4
        for p in self.body:
            w, h = p.wrap(inner, ah)
            self._items.append((p, h))
            y += h
        self.height = y + self.pad_t + self.pad_b
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.rect(0, 0, self.width, self.height, stroke=0, fill=1)
        c.setFillColor(self.bar)
        c.rect(0, 0, 2.6, self.height, stroke=0, fill=1)
        y = self.height - self.pad_t
        self._lbl.drawOn(c, self.pad_l, y - self._lbl.height)
        y -= self._lbl.height + 3.4
        for p, h in self._items:
            p.drawOn(c, self.pad_l, y - h)
            y -= h


class QA(Flowable):
    """Numaralı soru–cevap bloğu."""
    def __init__(self, n, q, a, width):
        Flowable.__init__(self)
        self.n, self.q, self.a, self.width = n, q, a, width
        self.qp = Paragraph(inline(q), QS)
        self.ap = Paragraph(inline(a), AS) if a else None

    def wrap(self, aw, ah):
        w = self.width
        self.qh = self.qp.wrap(w - 17, ah)[1]
        self.ah_ = self.ap.wrap(w - 17, ah)[1] if self.ap else 0
        self.height = self.qh + self.ah_ + 7
        return self.width, self.height

    def draw(self):
        c = self.canv
        y = self.height
        c.setStrokeColor(HexColor("#E7E1D4"))
        c.setLineWidth(0.4)
        c.line(0, self.height - 0.4, self.width, self.height - 0.4)
        c.setFillColor(GOLD)
        c.setFont("Sans-B", 7.2)
        c.drawRightString(10.5, self.height - 8.0, "%d" % self.n)
        self.qp.drawOn(c, 17, y - self.qh)
        if self.ap:
            c.setFillColor(RULE)
            c.rect(14, y - self.qh - 3.2, self.width - 20, 0.4, stroke=0, fill=1)
            self.ap.drawOn(c, 14, 0)
        c.setFillColor(RULE2)
        c.rect(14, -0.2, self.width - 14, 0.3, stroke=0, fill=1)


class NotesBlock(Flowable):
    """Bölüm sonu çizgili not alanı: kalan sütun yüksekliğini doldurur."""
    def __init__(self, label, width, min_h=70):
        Flowable.__init__(self)
        self.label, self.width, self.min_h = label, width, min_h

    def wrap(self, aw, ah):
        self.height = max(0, ah - 6)
        if self.height < 64:            # az yer kaldıysa boş sayfa açmayalım
            self.height = 0
        self.height = max(self.height, 0)
        return self.width, self.height

    def draw(self):
        if self.height < 64:
            return
        c = self.canv
        c.setFillColor(GOLD)
        c.setFont("Sans-B", 6.3)
        c.drawString(0, self.height - 8, tr_upper(self.label))
        y = self.height - 20
        c.setStrokeColor(HexColor("#D9D3C6"))
        c.setDash(1, 2.2)
        c.setLineWidth(0.4)
        while y > 2:
            c.line(0, y, self.width, y)
            y -= 13.4
        c.setDash()


class WeekStrip(Flowable):
    def __init__(self, items, width, height=30):
        Flowable.__init__(self)
        self.items, self.width, self.height = items, width, height

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        n = len(self.items)
        gap = 3.0
        w = (self.width - gap * (n - 1)) / n
        for i, (code, date, sub) in enumerate(self.items):
            x = i * (w + gap)
            c.setFillColor(NAVY if i % 2 == 0 else HexColor("#1A2E48"))
            c.rect(x, 0, w, self.height, stroke=0, fill=1)
            c.setFillColor(GOLD)
            c.setFont("Sans-B", 6.2)
            c.drawString(x + 4.5, self.height - 11, code)
            c.setFillColor(colors.white)
            c.setFont("Sans-M", 5.8)
            c.drawString(x + 15, self.height - 11, date)
            c.setFillColor(HexColor("#93A7BF"))
            c.setFont("Sans", 5.4)
            c.drawString(x + 4.5, 5.2, sub)


# ------------------------------------------------------------------ stiller
S0 = ParagraphStyle("lbl", fontName="Sans-B", fontSize=6.3, leading=7.6)
QS = ParagraphStyle("qs", fontName="Body-B", fontSize=8.8, leading=11.4, textColor=NAVY,
                    spaceAfter=1.6)
AS = ParagraphStyle("as", fontName="Body", fontSize=8.5, leading=11.2, textColor=INK,
                    alignment=TA_JUSTIFY)


# ------------------------------------------------------------------ ayrıştırıcı
def auto_widths(rows, width, ncol):
    """Sütun genişliklerini hücre metinlerinin uzunluğuna göre dağıtır."""
    if ncol == 1:
        return [width]
    lens = []
    for j in range(ncol):
        body = [len(str(r[j])) for r in rows[1:]]
        head = len(str(rows[0][j])) * 0.75
        vals = body + [head]
        m = sum(vals) / max(len(vals), 1)
        # en uzun hücre de pay alsın, ama baskın olmasın
        lens.append(0.72 * m + 0.28 * max(vals))
    if ncol == 2:
        lo, hi = 0.18, 0.62
    else:
        lo, hi = 0.09, 0.46
    raw = [max(l, 1.0) ** 0.62 for l in lens]
    tot = sum(raw)
    fr = [r / tot for r in raw]
    # yumuşat: uçlarını sınırla, kalanı oransal dağıt
    for _ in range(6):
        over = [i for i, f in enumerate(fr) if f > hi]
        under = [i for i, f in enumerate(fr) if f < lo]
        if not over and not under:
            break
        fixed = {}
        for i in over:
            fixed[i] = hi
        for i in under:
            fixed[i] = lo
        rest = [i for i in range(ncol) if i not in fixed]
        budget = 1.0 - sum(fixed.values())
        rtot = sum(raw[i] for i in rest) or 1.0
        for i in fixed:
            fr[i] = fixed[i]
        for i in rest:
            fr[i] = budget * raw[i] / rtot
    return [width * f for f in fr]


def make_table(caption, rows, width, S):
    if not rows:
        return []
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    widths = auto_widths(rows, width, ncol)
    head = [Paragraph(inline(c), S["table_h"]) for c in rows[0]]
    body = [[Paragraph(inline(c), S["table"]) for c in r] for r in rows[1:]]
    t = Table([head] + body, colWidths=widths, hAlign="LEFT", repeatRows=1,
              splitByRow=(len(rows) > 9))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.8),
        ("LINEBELOW", (0, 1), (-1, -1), 0.35, RULE),
        ("BOX", (0, 0), (-1, -1), 0.4, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TINT]),
    ]))
    out = []
    if caption:
        out += [Paragraph(inline(caption), S["caption"]), Spacer(1, 2.0)]
    out += [t]
    return out


def keep_headings(items, width, max_h=380):
    """Sayfa altında yalnız kalan başlıkları engeller: başlık, ardından gelen
    metin ya da kutucukla aynı grupta taşınır."""
    res, i, n = [], 0, len(items)
    while i < n:
        f = items[i]
        if isinstance(f, Heading) and i + 1 < n:
            j, lead = i + 1, []
            while j < n and isinstance(items[j], Spacer) and len(lead) < 2:
                lead.append(items[j]); j += 1
            nxt = items[j] if j < n else None
            tail = None
            if isinstance(nxt, Paragraph) and not isinstance(nxt, Heading):
                tail = [nxt]
            elif (isinstance(nxt, KeepGroup) and len(nxt.items) == 1
                  and isinstance(nxt.items[0], Box)):
                tail = list(nxt.items)
            if tail:
                grp = [f] + lead + tail
                try:
                    h = sum(x.wrap(width, 10000)[1] for x in grp)
                except Exception:
                    h = 10 ** 6
                if 0 < h <= max_h:
                    pre = []
                    while res and isinstance(res[-1], Rule):
                        pre.insert(0, res.pop())
                    res.append(KeepGroup(pre + grp))
                    i = j + 1
                    continue
        res.append(f)
        i += 1
    return res


def parse(path, S, width, wide=False, full_width=None):
    BODY = S["front_body"] if wide else S["body"]
    BUL = S["bullet"]; NUM = S["num"]
    lines = open(path, encoding="utf-8").read().split("\n")
    out, buf, pending = [], [], []
    i = 0

    def flush_pending():
        while pending:
            out.append(pending.pop(0))

    def flush():
        nonlocal buf
        if buf:
            flush_pending()
            txt = " ".join(x.strip() for x in buf).strip()
            if txt:
                out.append(Paragraph(inline(txt), BODY))
            buf = []

    while i < len(lines):
        s = lines[i].rstrip()
        if s.startswith("# "):
            flush(); flush_pending()
            parts = [p.strip() for p in s[2:].split("|")] + [""] * 4
            ch = ChapterHead(parts[0], parts[1], parts[2], parts[3],
                             width=full_width or width)
            ch._toc = (0, "%s · %s" % (parts[0], parts[2]))
            out += [NextPageTemplate("chapter"), PageBreak(), ch, FrameBreak(),
                    NextPageTemplate("2col"), Spacer(1, 9)]
            flush_pending(); i += 1; continue

        if s.startswith("## "):
            flush(); flush_pending()
            txt = s[3:].strip()
            m = re.match(r"^(\d+\.\d+)\s+(.*)$", txt)
            if m:
                html = ('<font name="Sans-B" size="9.0" color="#B08432">%s</font>'
                        '<font name="Sans-SB" size="11.4" color="#12233B">&nbsp;&nbsp;%s</font>'
                        % (m.group(1), inline(m.group(2))))
                plain = txt
            else:
                html = '<font name="Sans-SB" size="11.6" color="#12233B">%s</font>' % inline(txt)
                plain = txt
            pending.append(CondPageBreak(88))
            pending.append(Rule(width, color=RULE, t=0.5, pad=4.0))
            pending.append(Heading(html, S["h2"], 1, plain))
            i += 1; continue

        if s.startswith("### "):
            flush(); flush_pending()
            txt = s[4:].strip()
            pending.append(CondPageBreak(34))
            pending.append(Heading('<font name="Sans-SB" size="9.2" color="#2C6B63">%s</font>'
                                   % inline(txt), S["h3"], 2, txt))
            i += 1; continue

        if s.startswith("? "):
            flush(); flush_pending()
            q = s[2:].strip()
            a = ""
            if i + 1 < len(lines) and lines[i + 1].startswith("  = "):
                a = lines[i + 1][4:].strip()
                i += 1
            QA_N[0] += 1
            out += [Spacer(1, 1.6), QA(QA_N[0], q, a, width=width), Spacer(1, 1.6)]
            i += 1; continue

        if s.startswith(":::"):
            flush(); flush_pending()
            head = s[4:].strip()
            kind, _, title = head.partition(" ")
            kind = kind.strip() or "kural"
            title = title.strip()
            body, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith(":::"):
                ln = lines[i].strip()
                if ln:
                    if ln.startswith("- "):
                        p = Paragraph(inline(ln[2:]), ParagraphStyle(
                            "bx", parent=S["box_body"], leftIndent=6.0, bulletIndent=0.2))
                        p.bulletText = "•"
                    else:
                        p = Paragraph(inline(ln), S["box_body"])
                    body.append(p)
                i += 1
            if body:
                body[-1] = Paragraph(body[-1].text, ParagraphStyle(
                    "bx2", parent=S["box_body"], spaceAfter=0))
            bx = Box(kind, title, body, width)
            out += [Spacer(1, 2.0), KeepGroup([bx]), Spacer(1, 5.0)]
            i += 1; continue

        if s.startswith("|"):
            flush()
            if s.startswith("|="):
                cap = s[2:].strip(); i += 1
            else:
                cap = ""
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            tbl = make_table(cap, rows, width, S)
            block = pending + tbl
            pending.clear()
            try:
                h = sum(f.wrap(width, 10000)[1] for f in block)
            except Exception:
                h = 10 ** 6
            if h <= 706:
                out.append(KeepGroup(block))
            else:
                out.extend(block)
            out.append(Spacer(1, 5.0))
            continue

        if s.startswith("!notes"):
            flush(); flush_pending()
            out += [Spacer(1, 4.0), NotesBlock("Notlar", width)]
            i += 1; continue

        if s.startswith("!weeks"):
            flush(); flush_pending()
            out += [Spacer(1, 5), WeekStrip(WEEK_ITEMS, width=width), Spacer(1, 3)]
            i += 1; continue

        if s.startswith("%% "):
            flush(); flush_pending()
            out.append(Paragraph(inline(s[3:].strip()), S["display"]))
            i += 1; continue

        if s.startswith("^^ "):
            flush(); flush_pending()
            out.append(Paragraph(tr_upper(inline(s[3:].strip())), S["kicker"]))
            i += 1; continue

        if s.startswith(">> "):
            flush(); flush_pending()
            out.append(Paragraph("— " + inline(s[3:].strip()),
                                 ParagraphStyle("sn", parent=S["small"], fontSize=7.4,
                                                leading=9.8, textColor=HexColor("#4B5563"))))
            i += 1; continue

        if s.strip() in ("---", "***"):
            flush(); flush_pending()
            out.append(Rule(width, color=RULE, t=0.6, pad=5.0))
            i += 1; continue

        if s.startswith("- "):
            flush(); flush_pending()
            p = Paragraph(inline(s[2:].strip()), BUL); p.bulletText = "—"
            out.append(p); i += 1; continue

        m = re.match(r"^(\d+)\.\s+(.*)$", s)
        if m:
            flush(); flush_pending()
            p = Paragraph(inline(m.group(2)), NUM); p.bulletText = m.group(1) + "."
            out.append(p); i += 1; continue

        if s.strip() == "":
            flush(); i += 1; continue

        buf.append(s); i += 1

    flush(); flush_pending()
    return keep_headings(out, width)


# ------------------------------------------------------------------ TOC / dizin
def structure_toc(entries):
    blocks = []
    for lvl, text, page in entries:
        if lvl == 0 and text:
            blocks.append({"title": text, "page": page, "items": []})
        elif lvl == 1 and blocks:
            blocks[-1]["items"].append((text, page))
    return [b for b in blocks if b["items"] or b["title"]]


def toc_flowables(blocks, S, width=COL_W, max_rows=None):
    def pack(bs):
        items = []
        for b in bs:
            items.append(("c", b["title"], b["page"]))
            for t, p in b["items"]:
                items.append(("i", t, p))
        return items

    items = pack(blocks)
    parts = [items]
    out = []
    for pi, part in enumerate(parts):
        data, styles = [], []
        for kind, txt, page in part:
            if kind == "c":
                data.append([Paragraph(inline(txt), S["toc_c"]),
                             Paragraph('<font name="Sans-SB" size="9.8" color="#B08432">%s</font>' % page,
                                       ParagraphStyle("p", alignment=TA_RIGHT))])
                styles.append(("TOPPADDING", (0, len(data) - 1), (-1, len(data) - 1), 6.5))
            else:
                data.append([Paragraph(inline(txt), S["toc_i"]),
                             Paragraph('<font name="Sans-M" size="8.2" color="#6B7280">%s</font>' % page,
                                       ParagraphStyle("p", alignment=TA_RIGHT))])
        t = Table(data, colWidths=[width - 34, 34], hAlign="LEFT")
        st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("LEFTPADDING", (0, 0), (-1, -1), 0),
              ("RIGHTPADDING", (0, 0), (-1, -1), 0),
              ("TOPPADDING", (0, 0), (-1, -1), 0.5),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6)]
        t.setStyle(TableStyle(st + styles))
        out.append(t)
    return out


def index_flowables(page_texts, S, start_page=4):
    from book import tr_key
    norm = [(i + 1, tr_lower(t)) for i, t in enumerate(page_texts)]
    rows = []
    for term in TERMS:
        key = tr_lower(term)
        pages = [p for p, t in norm if p >= start_page and key in t]
        if pages:
            lab = "·".join(str(p) for p in pages[:16]) + ("…" if len(pages) > 16 else "")
            rows.append((term, lab))
    rows.sort(key=lambda r: tr_key(r[0]))
    if not rows:
        return [], 0
    data = [[Paragraph(inline(t), ParagraphStyle("ix", fontName="Sans-M", fontSize=8.4,
                                                 leading=13.4, textColor=NAVY)),
             Paragraph('<font name="Sans-M" size="6.6" color="#8A8397">%s</font>' % lab,
                       ParagraphStyle("ixp", alignment=TA_RIGHT, leading=13.4))]
            for t, lab in rows]
    t = Table(data, colWidths=[COL_W - 252, 252], hAlign="LEFT", repeatRows=0,
              splitByRow=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, RULE),
    ]))
    return [t], len(rows)


TERMS = [
    "aciz belgesi", "acente", "adi iş", "ahiz", "anonim şirket", "arabuluculuk",
    "avans faizi", "aval", "basiretli iş insanı", "bileşik faiz", "birleşme", "bono",
    "cari hesap", "cezaî şart", "ciro", "çek", "çekişmesiz yargı", "defter", "dernek",
    "devir", "donatma iştiraki", "emre yazılı", "esnaf", "faiz", "fatura", "gabin",
    "hamil", "hapis hakkı", "hâkim teşebbüs", "holding", "iflas", "ihtar", "işletme adı",
    "işletme değeri", "işletmenin devri", "kambiyo senedi", "kamu tüzel kişisi",
    "kâr payı", "karine", "kefalet", "kira", "kiracılık hakkı", "kollektif şirket",
    "komandit şirket", "komanditer", "komisyon", "konkordato", "kooperatif",
    "kıymetli evrak", "limited şirket", "marka", "merkez", "müteselsil", "nama yazılı",
    "nispi ticari dava", "ortak", "örf ve âdet", "özel hukuk tüzel kişisi", "rehin",
    "rekabet etmeme", "senet", "sicil", "sigorta", "şirket sözleşmesi", "şube", "tacir",
    "tacir gibi sorumluluk", "tacir sayılan", "tahvil", "taşınır rehni", "teamül",
    "temerrüt faizi", "tescil", "teselsül", "teyit mektubu", "ticaret sicili",
    "ticaret unvanı", "ticari iş", "ticari işletme", "ticari temsilci", "trampa",
    "tüketici", "vakıf", "yabancı para", "yetki sözleşmesi", "zayi belgesi",
]


# ------------------------------------------------------------------ belge
class Book(BaseDocTemplate):
    def __init__(self, filename, S, toc_data=None):
        BaseDocTemplate.__init__(self, filename, pagesize=(PAGE_W, PAGE_H),
                                 leftMargin=M_OUT, rightMargin=M_IN,
                                 topMargin=M_TOP, bottomMargin=M_BOT,
                                 title="Ticari İşletme Hukuku · Vize Çalışma Kitapçığı",
                                 author="D1–D8 transkriptlerinden düzenlenmiştir")
        self.S = S
        self.toc_entries = []
        self.toc_data = toc_data
        self.page_chapters = {}
        self._chap = ""
        w = PAGE_W - M_OUT - M_IN
        full = Frame(M_OUT, M_BOT, w, PAGE_H - M_TOP - M_BOT, id="full",
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        c1 = Frame(M_OUT, M_BOT, COL_W, PAGE_H - M_TOP - M_BOT, id="c1",
                   leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        head_h = 112.0
        top = Frame(M_OUT, PAGE_H - M_TOP - head_h, w, head_h, id="top",
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        ch_h = PAGE_H - M_TOP - head_h - 14 - M_BOT
        cc1 = Frame(M_OUT, M_BOT, COL_W, ch_h, id="cc1",
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate("cover", [full], onPage=self.draw_cover),
            PageTemplate("front", [full], onPage=self.draw_front),
            PageTemplate("chapter", [top, cc1], onPage=self.draw_chapter),
            PageTemplate("2col", [c1], onPage=self.draw_body),
            PageTemplate("toc2", [c1], onPage=self.draw_toc),
        ])

    # --- çizimler
    def _bar(self, c, left_txt, right_txt, sub=""):
        c.setFillColor(NAVY)
        c.rect(0, PAGE_H - 9.2 * mm, PAGE_W, 9.2 * mm, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(0, PAGE_H - 9.2 * mm, PAGE_W, 0.9, stroke=0, fill=1)
        c.setFillColor(HexColor("#93A7BF"))
        c.setFont("Sans-B", 6.4)
        c.drawString(48, PAGE_H - 6.2 * mm, tr_upper(left_txt))
        if right_txt:
            c.setFillColor(HexColor("#D8C08A"))
            c.drawRightString(PAGE_W - 48, PAGE_H - 6.2 * mm, tr_upper(right_txt))

    def _foot(self, c, n):
        c.setStrokeColor(RULE)
        c.setLineWidth(0.4)
        c.line(48, 26, PAGE_W - 48, 26)
        c.setFillColor(MUTED)
        c.setFont("Sans", 6.2)
        c.drawString(48, 17, "D1–D8 transkriptlerine dayalı genişletilmiş çalışma notu")
        c.setFillColor(NAVY)
        c.setFont("Sans-SB", 7.4)
        c.drawRightString(PAGE_W - 48, 17, str(n))

    def draw_cover(self, c, doc):
        c.setFillColor(NAVY)
        c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
        c.setFillColor(HexColor("#1A2E48"))
        c.rect(0, 0, PAGE_W, 210, stroke=0, fill=1)
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.8)
        c.rect(16, 16, PAGE_W - 32, PAGE_H - 32, stroke=1, fill=0)
        x = 46
        c.setFillColor(GOLD)
        c.setFont("Sans-B", 8.2)
        c.drawString(x, PAGE_H - 92, tr_upper("Ticaret Hukuku"))
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.4)
        c.line(x, PAGE_H - 100, x + 34, PAGE_H - 100)
        c.setFillColor(HexColor("#93A7BF"))
        c.setFont("Sans-M", 7.0)
        c.drawString(x, PAGE_H - 116, tr_upper("Ticari işletme hukuku · vize çalışma kitapçığı"))
        c.setFillColor(colors.white)
        c.setFont("Sans-SB", 42)
        c.drawString(x - 2, PAGE_H - 178, "Ticari İşletme")
        c.drawString(x - 2, PAGE_H - 226, "Hukuku")
        c.setFillColor(HexColor("#D8C08A"))
        c.setFont("Body", 15.5)
        c.drawString(x, PAGE_H - 262, "Sekiz dersin tamamı · genişletilmiş çalışma kitapçığı")

        # kutu
        c.setFillColor(HexColor("#1B3252"))
        c.rect(x, PAGE_H - 352, PAGE_W - 2 * x, 62, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(x, PAGE_H - 352, 2.4, 62, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Sans-M", 8.4)
        c.drawString(x + 14, PAGE_H - 312, "D1–D8 ders kayıtlarının tamamı, yeniden yazılıp düzenlenmiş hâli")
        c.setFillColor(HexColor("#93A7BF"))
        c.setFont("Sans", 8.0)
        c.drawString(x + 14, PAGE_H - 328, "Kurallar · istisnalar · örnek olaylar · 76 soru · karşılaştırma tabloları")

        # odak listesi
        c.setFillColor(colors.white)
        c.setFont("Sans-M", 9.0)
        focus = ["Şirket türleri ve ortakların sorumluluğu",
                 "Teslimsiz taşınır rehni · faiz · temerrüt",
                 "Ticari davalar ve zorunlu arabuluculuk",
                 "Unvan, işletme adı, marka ve devirde kaderi",
                 "Birleşme–devir farkı ve alacaklı koruması",
                 "Tacir olmanın sonuçları: iflas, basiret, teyit"]
        y = PAGE_H - 400
        for f in focus:
            c.setFillColor(GOLD)
            c.rect(x, y + 2.4, 3.0, 3.0, stroke=0, fill=1)
            c.setFillColor(HexColor("#D6DEE9"))
            c.setFont("Body", 9.6)
            c.drawString(x + 11, y, f)
            y -= 16.5

        # ders şeridi
        c.saveState()
        c.translate(x, 232)
        ws = WeekStrip(WEEK_ITEMS, width=PAGE_W - 2 * x, height=34)
        ws.canv = c
        ws.draw()
        c.restoreState()
        c.setFillColor(HexColor("#7E92AB"))
        c.setFont("Sans-M", 6.2)
        c.drawString(x, 224, tr_upper("Sekiz ders · 22 Eylül – vize öncesi son ders"))
        # alıntı
        c.setFillColor(GOLD)
        c.setFont("Body", 26)
        c.drawString(x - 1, 118, "“")
        c.setFillColor(HexColor("#E8D9B8"))
        c.setFont("Body-It", 12.2)
        c.drawString(x + 20, 116, "Sınavda istenen dört adım: nitelendirme, kural, istisna, sonuç.")

        # istatistik şeridi
        stats = [("8", "BÖLÜM"), ("4", "EK"), ("13", "TABLO"), ("76", "SORU")]
        sy = 62
        c.setStrokeColor(HexColor("#33506F"))
        c.setLineWidth(0.5)
        c.line(x, sy + 34, PAGE_W - x, sy + 34)
        for i, (num, lab) in enumerate(stats):
            sx = x + i * ((PAGE_W - 2 * x) / 4)
            c.setFillColor(GOLD)
            c.setFont("Sans-SB", 19)
            c.drawString(sx, sy + 12, num)
            c.setFillColor(HexColor("#8FA3BC"))
            c.setFont("Sans-M", 6.2)
            c.drawString(sx, sy + 3, lab)
        c.setFillColor(HexColor("#7E92AB"))
        c.setFont("Sans", 6.6)
        c.drawString(x, 32, "Genişletilmiş 2. baskı · Kasım 2026")
        c.drawRightString(PAGE_W - x, 32, PAGES_LABEL[0] + "  ·  D1–D8")

    def draw_front(self, c, doc):
        self._bar(c, "Ticaret Hukuku · ön söz", "Nasıl kullanılır")
        self._foot(c, doc.page)

    def draw_chapter(self, c, doc):
        self._bar(c, "Ticaret Hukuku · ticari işletme hukuku", "")
        self._foot(c, doc.page)

    def draw_body(self, c, doc):
        self._bar(c, "Ticaret Hukuku · ticari işletme hukuku · vize kitapçığı", doc._chap or "")
        self._foot(c, doc.page)

    def draw_toc(self, c, doc):
        self._bar(c, "Ticaret Hukuku", "İçindekiler")
        self._foot(c, doc.page)

    def build(self, flowables, **kw):
        DEFERRED_TOC.clear()
        TOC_SEQ[0] = 0
        BaseDocTemplate.build(self, flowables, **kw)
        seen = set()
        merged = []
        for seq, lvl, txt, pg in sorted(self.toc_entries + DEFERRED_TOC):
            key = (lvl, txt)
            if key in seen:
                continue
            seen.add(key)
            merged.append((lvl, txt, pg))
        self.toc_entries = merged

    def afterFlowable(self, flowable):
        if isinstance(flowable, ChapterHead):
            self._chap = flowable.title
            self._has_chapter = True
            TOC_SEQ[0] += 1
            self.toc_entries.append((TOC_SEQ[0], 0,
                                     "%s · %s" % (flowable.code, flowable.title), self.page))
            try:
                key = "ch%d" % self.page
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry("%s · %s" % (flowable.code, flowable.title),
                                          key, level=0, closed=False)
            except Exception:
                pass
        elif isinstance(flowable, Heading) and getattr(self, "_has_chapter", False):
            lvl, txt = flowable._toc
            TOC_SEQ[0] += 1
            self.toc_entries.append((TOC_SEQ[0], lvl, txt, self.page))
            try:
                key = "s%d" % TOC_SEQ[0]
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(txt, key, level=min(lvl, 2), closed=True)
            except Exception:
                pass
