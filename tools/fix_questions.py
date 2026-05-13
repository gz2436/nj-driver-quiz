#!/usr/bin/env python3
"""Apply automated fixes for known parsing patterns.

Reads:  data/questions.json
Writes: data/questions.json (in place)
Logs:   /tmp/nj_build/fix_log.json
        docs/CHANGELOG.md  (append)

Fixes applied:
  CAT A (Chinese stem leaked into optA):
    - drop position-A content, shift B→A, C→B, D→C, leave D empty
    - answer letter unchanged (source labeling stays aligned)
    - EXCEPT when current answer is 'D' — real D is irrecoverably lost; flag for review

  CAT B (bilingual options split into 4):
    - merge pairs into 2 bilingual options
    - map answer: A/B → A, C/D → B

  CAT E, G, H (small counts): flag for manual review only — not auto-fixed
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import date

DATA = '/Users/gavincheung/NYU/Driver/data/questions.json'
LOG = '/tmp/nj_build/fix_log.json'
CHANGELOG = '/Users/gavincheung/NYU/Driver/docs/CHANGELOG.md'

CHINESE_RE = re.compile(r'[一-鿿]')
ENGLISH_WORD_RE = re.compile(r'\b[A-Za-z]{2,}\b')


def chinese_chars(s):
    return len(CHINESE_RE.findall(s))


def has_substantial_english(s):
    words = ENGLISH_WORD_RE.findall(s)
    if any(len(w) >= 4 for w in words):
        return True
    if len(words) >= 3:
        return True
    return False


def has_chinese(s):
    return bool(CHINESE_RE.search(s))


def is_chinese_only(s):
    return has_chinese(s) and not has_substantial_english(s)


def is_english_only(s):
    return has_substantial_english(s) and not has_chinese(s)


def strip_img(s):
    return re.sub(r'__IMG__[^_]+(?:_[^_]+)*?__', '', s).strip()


def detect_cat_a(q):
    """Cat A: Chinese stem leaked into optA."""
    if q['type'] == 'tf':
        return False
    opts = q['options']
    if not opts[0]:
        return False
    opt_a = opts[0]
    stem = strip_img(q['stem'])
    if not (chinese_chars(opt_a) >= 12
            and not has_substantial_english(opt_a)
            and re.search(r'[:：?？]\s*$', stem.rstrip())
            and not re.search(r'\d', opt_a)):
        return False
    return True


def detect_cat_b(q):
    """Cat B: bilingual options split — A/B and C/D are EN/ZH pairs."""
    if q['type'] == 'tf':
        return False
    opts = q['options']
    if not all(opts):
        return False
    eo = [is_english_only(o) for o in opts]
    co = [is_chinese_only(o) for o in opts]
    if (eo[0] and co[1] and eo[2] and co[3]) or (co[0] and eo[1] and co[2] and eo[3]):
        return True
    return False


def fix_cat_a(q, log):
    """Drop optA, shift options up. Flag answer=D as broken."""
    orig_opts = q['options'][:]
    orig_answer = q['answer']
    # Move optA content into stem (preserve image marker if present)
    chinese_stem = orig_opts[0]
    # Append to stem with newline (keep image marker leading)
    if '\n' not in q['stem']:
        q['stem'] = q['stem'].rstrip() + '\n' + chinese_stem
    else:
        q['stem'] = q['stem'].rstrip() + ' ' + chinese_stem
    # Shift options
    q['options'] = [orig_opts[1], orig_opts[2], orig_opts[3], '']
    # Answer letter stays the same (source labeling A/B/C/D aligns to new positions),
    # except if it was D — that option is irrecoverably lost.
    broken = False
    if orig_answer == 'D':
        broken = True
        q['_needs_review'] = 'cat_a_answer_d_lost'
    log['cat_a'].append({
        'id': q['id'],
        'orig_answer': orig_answer,
        'broken': broken,
        'stem_preview': q['stem'][:80],
    })
    return broken


def fix_cat_b(q, log):
    """Merge bilingual pairs into 2 options. Adjust answer."""
    orig_opts = q['options'][:]
    orig_answer = q['answer']
    eo = [is_english_only(o) for o in orig_opts]
    # Determine pair order
    if eo[0]:  # EN/ZH/EN/ZH
        new_a = f'{orig_opts[0]} {orig_opts[1]}'.strip()
        new_b = f'{orig_opts[2]} {orig_opts[3]}'.strip()
    else:  # ZH/EN/ZH/EN
        new_a = f'{orig_opts[1]} {orig_opts[0]}'.strip()
        new_b = f'{orig_opts[3]} {orig_opts[2]}'.strip()
    q['options'] = [new_a, new_b, '', '']
    # Map answer
    if orig_answer in ('A', 'B'):
        q['answer'] = 'A'
    else:  # C or D
        q['answer'] = 'B'
    log['cat_b'].append({
        'id': q['id'],
        'orig_answer': orig_answer,
        'new_answer': q['answer'],
        'stem_preview': strip_img(q['stem'])[:80],
    })


def main():
    with open(DATA) as f:
        qs = json.load(f)

    log = {'cat_a': [], 'cat_b': [], 'broken': []}

    for q in qs:
        if detect_cat_a(q):
            broken = fix_cat_a(q, log)
            if broken:
                log['broken'].append(q['id'])
        elif detect_cat_b(q):
            fix_cat_b(q, log)

    # Write back
    with open(DATA, 'w') as f:
        json.dump(qs, f, ensure_ascii=False, indent=2)

    os.makedirs('/tmp/nj_build', exist_ok=True)
    with open(LOG, 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f'Cat A fixed: {len(log["cat_a"])} (of which {len(log["broken"])} have answer=D irrecoverable)', file=sys.stderr)
    print(f'Cat B merged: {len(log["cat_b"])}', file=sys.stderr)

    # Append to CHANGELOG
    today = date.today().isoformat()
    block = [
        '',
        f'## {today} — automated parsing fixes',
        '',
        f'- Cat A: dropped Chinese stem leak from optA, shifted options, on {len(log["cat_a"])} questions.',
        f'  Of these, {len(log["broken"])} had answer=D which referenced an option lost during initial parsing; marked `_needs_review`.',
        f'- Cat B: merged 4-line bilingual option pairs into 2 bilingual options, on {len(log["cat_b"])} questions.',
        f'- Total auto-fixed: {len(log["cat_a"]) + len(log["cat_b"])} questions.',
    ]
    with open(CHANGELOG, 'a') as f:
        f.write('\n'.join(block) + '\n')


if __name__ == '__main__':
    main()
