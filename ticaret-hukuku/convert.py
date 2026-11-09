# -*- coding: utf-8 -*-
"""Orijinal 36 sayfalık notu yapılandırılmış markdown'a çevirir."""
import pymupdf, re, os

SRC = "ticaret_hukuku_vize_kitapcigi_compact.pdf"
OUT = "content"

CH = {
    "D1": ("1. HAFTA · 22 EYLÜL", "Dersin Çerçevesi: Kapsam, Kaynak, Yöntem",
           "Ticaret hukukunun sınırı, altı kitap, dört sistem ve sınavın ne istediği."),
    "D2": ("2. HAFTA · 29 EYLÜL (I)", "Temeller: Sistemler, Kaynaklar, Senetler",
           "Modern sisteme geçiş, kanunlar arası ilişki, kıymetli evrak ve tüketici senetleri."),
    "D3": ("2. HAFTA · 29 EYLÜL (II)", "Ticari İşin Belirlenmesi ve Sonuçları",
           "İki ölçüt, işletme bağlantısı, haksız fiil, karine ve teselsül."),
    "D4": ("3. HAFTA · 6 EKİM", "Faiz: Türler, Oranlar, Tavanlar",
           "Adi–ticari faiz ayrımı, anapara faizi, temerrüt, bileşik faiz istisnaları."),
    "D5": ("4. HAFTA · 13 EKİM", "Kurallar, Davalar, Mahkemeler, İşletme",
           "Uygulama sırası, mutlak–nispi ayrımı, arabuluculuk ve işletmenin unsurları."),
    "D6": ("5. HAFTA · 20 EKİM", "Şube, Unvan ve İşletmenin Devri",
           "Merkez–şube ayrımı, ticari temsilci, unvan–işletme adı–marka, devirde sorumluluk."),
    "D7": ("6. HAFTA · 27 EKİM", "Birleşme, Rehin ve Tacirliğin Kazanılması",
           "Tasfiye, teslimsiz taşınır rehni, görünüşe güven ve fiilen tacir olma."),
    "D8": ("VİZE ÖNCESİ SON DERS", "Tacir Statüsü, Şirketler, Ticari Hükümler",
           "Tacir kime denir, ortak hangi borçtan sorumludur, hükümler nereden doğar."),
}
ORDER = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"]


def rows_of(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            sp = [s for s in l["spans"] if s["text"].strip()]
            if not sp:
                continue
            y = l["bbox"][1]
            if y < 34 or y > 792:
                continue
            out.append({"x": round(l["bbox"][0], 1), "y": y,
                        "size": round(sp[0]["size"], 1),
                        "bold": "Bold" in sp[0]["font"],
                        "text": "".join(s["text"] for s in sp).strip()})
    out.sort(key=lambda r: (round(r["y"], 1), r["x"]))
    grouped = []
    for r in out:
        if grouped and abs(grouped[-1]["y"] - r["y"]) < 4:
            grouped[-1]["cells"].append(r)
        else:
            grouped.append({"y": r["y"], "cells": [r]})
    return grouped


def is_bullet(row):
    c = row["cells"]
    return len(c) == 1 and c[0]["text"].startswith("•")


def build():
    doc = pymupdf.open(SRC)
    chapters = {}
    cur = None
    state = None          # ("p", [..]) | ("b", [..]) | ("t", [rows]) | ("h3", ..)
    prev_y = None

    def flush():
        nonlocal state
        if not state:
            return
        kind, val = state
        ch = chapters[cur]
        if kind == "p":
            ch["blocks"].append(("p", " ".join(val)))
        elif kind == "b":
            ch["blocks"].append(("b", " ".join(val)))
        elif kind == "t":
            ch["blocks"].append(("t", val))
        state = None

    for pno, page in enumerate(doc):
        if pno < 2:
            continue
        prev_y = None
        for row in rows_of(page):
            cells = row["cells"]
            size = cells[0]["size"]
            text = " ".join(c["text"] for c in cells)
            if size == 9.5:
                m = re.search(r"Kaynak:\s*(D\d)", text)
                if m:
                    flush()
                    cur = m.group(1)
                    chapters.setdefault(cur, {"blocks": [], "src": text.split(" / ")[0]})
                continue
            if size >= 17:
                continue
            if size == 14.0:
                flush()
                chapters[cur]["blocks"].append(("h2", text))
                prev_y = row["y"]
                continue
            istable = size == 10.5
            if istable:
                if state and state[0] != "t":
                    flush()
                if not state:
                    state = ("t", {"cols": [c["x"] for c in cells] if len(cells) > 1 else None,
                                   "rows": []})
                t = state[1]
                if t["cols"] is None and len(cells) > 1:
                    t["cols"] = [c["x"] for c in cells]
                if t["cols"] and len(cells) > 1:
                    t["rows"].append([c["text"] for c in cells])
                else:
                    x = cells[0]["x"]
                    idx = min(range(len(t["cols"] or [x])),
                              key=lambda i: abs((t["cols"] or [x])[i] - x))
                    if not t["rows"] or idx == 0:
                        t["rows"].append([""] * len(t["cols"] or [x]))
                    r = t["rows"][-1]
                    while len(r) <= idx:
                        r.append("")
                    r[idx] = (r[idx] + " " + cells[0]["text"]).strip()
                prev_y = row["y"]
                continue
            # gövde
            gap = 99 if prev_y is None else row["y"] - prev_y
            prev_y = row["y"]
            c = cells[0]
            if is_bullet(row):
                flush()
                state = ("b", [c["text"][1:].strip()])
                continue
            if state and state[0] == "b" and c["x"] > 52 and gap < 20:
                state[1].append(c["text"])
                continue
            if c["bold"] and gap > 12 and len(c["text"]) < 95 and not c["text"].endswith("."):
                flush()
                chapters[cur]["blocks"].append(("h3", c["text"]))
                continue
            cont = state and state[0] == "p" and (
                gap < 17 or (gap > 40 and c["text"][:1].islower()))
            if cont:
                state[1].append(c["text"])
            else:
                flush()
                state = ("p", [c["text"]])
    flush()
    return chapters


def render():
    chapters = build()
    os.makedirs(OUT, exist_ok=True)
    for idx, code in enumerate(ORDER, 1):
        ch = chapters.get(code)
        kicker, title, lede = CH[code]
        out = [f"# {code} | {kicker} | {title} | {lede}", ""]
        n = 0
        for kind, val in ch["blocks"]:
            if kind == "h2":
                n += 1
                out += [f"## {code[1]}.{n} {val}", ""]
            elif kind == "h3":
                out += [f"### {val}", ""]
            elif kind == "p":
                out += [val, ""]
            elif kind == "b":
                out += ["- " + val, ""]
            elif kind == "t":
                rows = val["rows"]
                if len(rows) < 2:
                    continue
                ncol = max(len(r) for r in rows)
                out += ["|=Karşılaştırma", ""]
                for r in rows:
                    r = [x.replace("|", "/").strip() for x in (r + [""] * (ncol - len(r)))]
                    out.append("| " + " | ".join(r) + " |")
                out.append("")
        out += ["!notes", ""]
        path = os.path.join(OUT, f"{idx:02d}_{code.lower()}.md")
        open(path, "w").write("\n".join(out))
        print(path, len(out), "lines", n, "sections",
              sum(1 for k, _ in ch["blocks"] if k == "t"), "tables")


if __name__ == "__main__":
    render()
