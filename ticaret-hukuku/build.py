# -*- coding: utf-8 -*-
"""Kitapçığı derler (içindekiler ve dizin sayfa numaraları iki geçişte)."""
import os, glob, sys
from reportlab.platypus import (Spacer, PageBreak, NextPageTemplate, Paragraph, FrameBreak)
from reportlab.lib.units import mm
from book import *   # noqa
from engine import Book, parse, structure_toc, toc_flowables, index_flowables, ChapterHead

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "content")
OUT = os.path.join(HERE, "out")


def content_files():
    return [f for f in sorted(glob.glob(os.path.join(CONTENT, "*.md")))
            if os.path.basename(f) not in ("00_front.md", "00_head.md")]


def assemble(S, toc=None, front=None, index=None):
    story = [NextPageTemplate("cover"), Spacer(1, 2),
             NextPageTemplate("front"), PageBreak()]
    if front:
        story.extend(front)
    story += [NextPageTemplate("toc2"), PageBreak()]
    if toc is None:
        story.append(Spacer(1, PAGE_H - M_TOP - M_BOT - 6))
    else:
        story.extend(toc)
    story += [NextPageTemplate("2col"), Spacer(1, 2)]
    import engine as _e
    _e.QA_N[0] = 0
    for f in content_files():
        story.extend(parse(f, S, COL_W, full_width=PAGE_W - M_OUT - M_IN))
    if index:
        story.extend(index)
    return story


def build(path, S, toc=None, index=None):
    doc = Book(path, S, toc_data=toc)
    front = parse(os.path.join(CONTENT, "00_front.md"), S,
                  PAGE_W - M_OUT - M_IN, wide=True)
    doc.build(assemble(S, toc, front, index))
    return doc


def render():
    register()
    S = styles()
    os.makedirs(OUT, exist_ok=True)
    final = os.path.join(OUT, "ticaret_hukuku_vize_calisma_kitapcigi.pdf")
    tmp = os.path.join(OUT, "_pass.pdf")
    toc = None
    for _ in range(4):
        doc = build(tmp, S, toc=toc)
        blocks = structure_toc(doc.toc_entries)
        new = toc_flowables(blocks, S)
        if toc is not None and len(new) == len(toc):
            toc = new
            break
        toc = new
    # dizin için sayfa metinleri
    import pymupdf
    from engine import COL_W as _cw
    doc0 = build(tmp, S, toc=toc)
    texts = [p.get_text() for p in pymupdf.open(tmp)]
    idx_tbl, n_terms = index_flowables(texts, S, start_page=4)
    head = ChapterHead("DİZİN", "ALFABETİK · KAVRAM – SAYFA", "Kavram Dizini",
                       "Metinde geçen kavramlar ve sayfa numaraları; %d kavram. "
                       "Sınavda aradığın terimi buradan bul, ilgili bölüme git." % n_terms,
                       width=PAGE_W - M_OUT - M_IN)
    head._toc = (0, "Kavram Dizini")
    idx = [NextPageTemplate("chapter"), PageBreak(), head, FrameBreak(),
           NextPageTemplate("2col"), Spacer(1, 8)] + idx_tbl
    doc_b = build(tmp, S, toc=toc, index=idx)
    import engine as _e2
    _e2.PAGES_LABEL[0] = "%d SAYFA" % doc_b.page
    toc2 = toc_flowables(structure_toc(doc_b.toc_entries), S)
    doc = build(final, S, toc=toc2, index=idx)
    for f in ("_pass.pdf",):
        p = os.path.join(OUT, f)
        if os.path.exists(p):
            os.remove(p)
    return final, doc.page, structure_toc(doc.toc_entries)


if __name__ == "__main__":
    final, pages, blocks = render()
    print("pages:", pages)
    print("chapters:", len(blocks), "sections:", sum(len(b["items"]) for b in blocks))
    print("out:", final)
