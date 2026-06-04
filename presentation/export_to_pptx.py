#!/usr/bin/env python3
"""
Convert simple slide-markdown (split with '---') into a .pptx file.
Usage: python presentation/export_to_pptx.py
Requires: python-pptx
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pathlib import Path

SRC = Path(__file__).resolve().parents[0] / 'PRESENTATION.md'
OUT = Path(__file__).resolve().parents[0] / 'COMPLETE_SYSTEM_PRESENTATION.pptx'


def slide_from_block(prs, block: str):
    lines = [l.rstrip() for l in block.strip().splitlines() if l.strip()]
    if not lines:
        return
    # title is first line starting with '#'
    title = lines[0].lstrip('# ').strip() if lines[0].startswith('#') else 'Slide'
    body_lines = []
    notes = []
    for l in lines[1:]:
        if l.lower().startswith('speaker notes:') or l.lower().startswith('notes:'):
            notes.append(l.split(':', 1)[1].strip())
        else:
            body_lines.append(l)

    slide_layout = prs.slide_layouts[1]  # Title and Content
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = title

    # content placeholder
    body = slide.shapes.placeholders[1].text_frame
    body.clear()
    for bl in body_lines:
        text = bl
        # strip markdown bullets
        if text.lstrip().startswith('- '):
            text = text.lstrip()[2:]
        p = body.add_paragraph()
        p.text = text
        p.font.size = Pt(18)

    if notes:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = '\n'.join(notes)


if __name__ == '__main__':
    if not SRC.exists():
        raise FileNotFoundError(f'Source not found: {SRC}')
    content = SRC.read_text(encoding='utf-8')
    blocks = [b for b in content.split('\n---\n')]
    prs = Presentation()
    # remove default first slide
    if prs.slides:
        # create blank presentation then remove default slides
        pass
    prs.slides._sldIdLst.clear()

    for b in blocks:
        slide_from_block(prs, b)

    prs.save(OUT)
    print(f'Wrote: {OUT}')
