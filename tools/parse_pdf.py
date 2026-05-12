#!/usr/bin/env python3
"""Parse the 24-page bilingual PDF (Q+answer format) for cross-validation.

Source: 美国新泽西驾照笔试题 ch eng.pdf
Format per entry: 'N. <English Q>: N.<Chinese Q> ︰ A: <English Answer>. 答 ︰ <Chinese Answer>.'

This PDF gives ONE correct answer per question (no A/B/C/D options).
We use it to cross-check docx answers via fuzzy stem matching.

Output: /tmp/nj_build/pdf_qa.json — list of {num, q_en, q_zh, ans_en, ans_zh}
"""
import json
import os
import re
import sys

import pdfplumber

ROOT = '/Users/gavincheung/NYU/Driver'
SOURCES = f'{ROOT}/sources'
BUILD = '/tmp/nj_build'
PDF_PATH = f'{SOURCES}/美国新泽西驾照笔试题 ch eng.pdf'

# The PDF uses ' ︰ ' (full-width colon variant) between Q and A in Chinese
# Pattern: 'N. <En Q>: N.<Zh Q> ︰ A: <En A>. 答 ︰ <Zh A>.'
# Numbers can repeat (N.<EnQ>: N.<ZhQ>) — the Chinese half restarts the number.
# Answer marker '答' uses 'colon variant ︰'

# Extract all text first, normalize, then split by numeric prefix
def extract_full_text():
    parts = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ''
            parts.append(txt)
    return '\n'.join(parts)


def parse_entries(text):
    """Split into per-question entries by numeric prefix."""
    # Normalize whitespace but keep line breaks
    # Each question starts with 'N. ' where N is 1-200ish (at start of line or after lots of whitespace)
    # We'll split on lookahead for '\nN. ' or start of string.
    entries = []
    # Find all positions where a new entry starts
    pattern = re.compile(r'(?:^|\n)(\d{1,3})\.\s')
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        num = int(m.group(1))
        entries.append((num, block))
    return entries


def parse_one(block):
    """Parse a single block into {num, q_en, q_zh, ans_en, ans_zh}."""
    # Remove leading number
    m = re.match(r'(\d+)\.\s*', block)
    num = int(m.group(1)) if m else None
    body = block[m.end():] if m else block

    # The body should contain:
    #   <English Q ending with :> <Chinese number>.<Chinese Q ending with ︰> A: <English A> 答 ︰ <Chinese A>
    # But the Chinese number sometimes restarts (e.g., '1.农业的执照...').

    # First, locate ' 答 ' marker — Chinese answer starts there.
    zh_ans_match = re.search(r'答\s*[︰:：]\s*', body)
    if not zh_ans_match:
        return None
    pre_zh_ans = body[:zh_ans_match.start()].strip()
    zh_ans = body[zh_ans_match.end():].strip()
    # Strip trailing period
    zh_ans = re.sub(r'[。.\s]+$', '', zh_ans)

    # Locate 'A:' or 'A：' for English answer
    en_ans_match = re.search(r'\bA\s*[:：]\s*', pre_zh_ans)
    if not en_ans_match:
        return None
    pre_en_ans = pre_zh_ans[:en_ans_match.start()].strip()
    en_ans = pre_zh_ans[en_ans_match.end():].strip()
    en_ans = re.sub(r'[.。\s]+$', '', en_ans)

    # pre_en_ans now contains: <English Q>: <Chinese number>.<Chinese Q> ︰
    # Find the ' ︰' separator (Chinese full-width colon)
    sep_match = re.search(r'[︰:：]\s*$', pre_en_ans)
    if sep_match:
        pre_en_ans = pre_en_ans[:sep_match.start()].rstrip()

    # Now split into English Q + Chinese Q by finding the Chinese restart
    # Pattern: '<English Q ending with :> <N>.<Chinese Q>'
    zh_split = re.search(r'(:|：)\s*(\d+)[\.．]\s*', pre_en_ans)
    if zh_split:
        q_en = pre_en_ans[:zh_split.start()].strip() + ':'
        q_zh = pre_en_ans[zh_split.end():].strip()
    else:
        # Fall back: assume entire pre_en_ans is bilingual mixed
        q_en = pre_en_ans
        q_zh = ''

    return {
        'num': num,
        'q_en': re.sub(r'\s+', ' ', q_en).strip(),
        'q_zh': re.sub(r'\s+', ' ', q_zh).strip(),
        'ans_en': re.sub(r'\s+', ' ', en_ans).strip(),
        'ans_zh': re.sub(r'\s+', ' ', zh_ans).strip(),
    }


def main():
    os.makedirs(BUILD, exist_ok=True)
    text = extract_full_text()
    entries = parse_entries(text)
    print(f'Found {len(entries)} numbered entries', file=sys.stderr)

    parsed = []
    for num, block in entries:
        rec = parse_one(block)
        if rec:
            parsed.append(rec)

    print(f'Parsed {len(parsed)} Q+A pairs', file=sys.stderr)
    with open(f'{BUILD}/pdf_qa.json', 'w') as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    # Show first 3
    for r in parsed[:3]:
        print(f"\nQ{r['num']}: {r['q_en'][:80]}", file=sys.stderr)
        print(f"  ZH: {r['q_zh'][:60]}", file=sys.stderr)
        print(f"  Ans EN: {r['ans_en'][:80]}", file=sys.stderr)
        print(f"  Ans ZH: {r['ans_zh'][:50]}", file=sys.stderr)


if __name__ == '__main__':
    main()
