#!/usr/bin/env python3
"""Copy images from docx + (optionally) render driver-manual signs pages to data/images/.

Outputs:
- /Users/gavincheung/NYU/Driver/data/images/*.{jpg,png}  (docx inline images)
- /Users/gavincheung/NYU/Driver/data/images/manual_signs/*.jpg  (rendered pages 213-224)
"""
import os
import shutil
import subprocess
import sys

BUILD = '/tmp/nj_build'
DATA_IMAGES = '/Users/gavincheung/NYU/Driver/data/images'
MANUAL_PDF = '/Users/gavincheung/NYU/Driver/sources/drivermanual.pdf'


def copy_docx_images():
    """Copy images from both docx media dirs to data/images/."""
    os.makedirs(DATA_IMAGES, exist_ok=True)
    sources = [
        f'{BUILD}/full_unpacked/word/media',
        f'{BUILD}/easy_unpacked/word/media',
    ]
    copied = 0
    for src in sources:
        if not os.path.isdir(src):
            continue
        for fname in os.listdir(src):
            target = f'{DATA_IMAGES}/{fname}'
            if not os.path.exists(target):
                shutil.copy(f'{src}/{fname}', target)
                copied += 1
    print(f'Copied {copied} new docx images to {DATA_IMAGES}', file=sys.stderr)


def render_manual_signs_pages():
    """Render manual pages 213-224 as PNG using pdfplumber + Pillow.

    These pages contain the official road sign reference. We render them as page-level
    images for use in signs.html. We do NOT try to extract individual sign images
    because they are interleaved with text and labels.
    """
    out_dir = f'{DATA_IMAGES}/manual_signs'
    os.makedirs(out_dir, exist_ok=True)

    try:
        import pdfplumber
        from PIL import Image
    except ImportError as e:
        print(f'Skipping manual page render: {e}', file=sys.stderr)
        return

    rendered = 0
    with pdfplumber.open(MANUAL_PDF) as pdf:
        for page_num in range(213, 225):  # inclusive 213-224
            if page_num > len(pdf.pages):
                break
            page = pdf.pages[page_num - 1]  # 0-indexed
            try:
                img = page.to_image(resolution=144).original
                out_path = f'{out_dir}/manual_p{page_num}.jpg'
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(out_path, 'JPEG', quality=80, optimize=True)
                rendered += 1
            except Exception as e:
                print(f'  Failed page {page_num}: {e}', file=sys.stderr)
    print(f'Rendered {rendered} manual sign pages to {out_dir}', file=sys.stderr)


def main():
    copy_docx_images()
    render_manual_signs_pages()


if __name__ == '__main__':
    main()
