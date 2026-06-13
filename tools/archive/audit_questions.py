#!/usr/bin/env python3
"""Audit the parsed question bank for known parsing issues.

Refined detection to reduce false positives.

Categories (ordered by severity):
  A. stem_chinese_continuation_in_optA  — Chinese stem leaked into option A position
  B. bilingual_options_split            — 4 options where lines alternate EN-only / ZH-only
  C. option_d_contaminated              — option D contains a question keyword + ? (next q leaked in)
  D. answer_marker_in_option            — option text contains '答：'
  E. empty_option_non_sign              — non-sign question with empty option(s)
  F. duplicate_options
  G. stem_too_short                     — stem < 20 chars after image strip
  H. stem_chinese_only_no_english       — stem has Chinese but missing English half (and not just a number-fill blank)
"""
import json
import os
import re
import sys
from collections import defaultdict

DATA = '/Users/gavincheung/NYU/Driver/data/questions.json'

with open(DATA) as f:
    qs = json.load(f)

CHINESE_RE = re.compile(r'[一-鿿]')
# An option is "english-content-bearing" if it has 4+ consecutive letters or 2+ English words of 2+ letters
ENGLISH_WORD_RE = re.compile(r'\b[A-Za-z]{2,}\b')


def chinese_chars(s):
    return len(CHINESE_RE.findall(s))


def english_letters(s):
    return len(re.findall(r'[A-Za-z]', s))


def english_words(s):
    return ENGLISH_WORD_RE.findall(s)


def has_substantial_english(s):
    """Return True if option contains meaningful English text (not just abbreviations like '10mph')."""
    words = english_words(s)
    # At least 1 word of 4+ letters, OR 3+ words of 2+ letters
    if any(len(w) >= 4 for w in words):
        return True
    if len(words) >= 3:
        return True
    return False


def has_chinese(s):
    return bool(CHINESE_RE.search(s))


def is_chinese_only(s):
    """Has Chinese chars AND no substantial English."""
    return has_chinese(s) and not has_substantial_english(s)


def is_english_only(s):
    """Has substantial English AND no Chinese."""
    return has_substantial_english(s) and not has_chinese(s)


def strip_img(s):
    return re.sub(r'__IMG__[^_]+(?:_[^_]+)*?__', '', s).strip()


STEM_KEYWORDS = re.compile(r'\b(If|When|What|How|Why|Where|Driver|Vehicle|Two cars|You\b)', re.I)
SIGN_RE = re.compile(r'sign|signal|marking|这个|标志', re.I)

issues = defaultdict(list)

for q in qs:
    qid = q['id']
    if q['type'] == 'tf':
        continue
    stem_raw = q['stem']
    stem = strip_img(stem_raw)
    opts = q['options']
    is_sign = bool(q.get('stem_img')) and SIGN_RE.search(stem_raw)

    # G. stem too short
    if len(stem) < 20 and not is_sign:
        issues['G_stem_too_short'].append({
            'id': qid, 'stem': stem, 'opts': opts, 'answer': q['answer'],
        })

    # D. answer marker leak (答：)
    for i, o in enumerate(opts):
        if o and ('答：' in o or '答:' in o):
            issues['D_answer_marker_in_option'].append({
                'id': qid, 'stem': stem[:80], 'opt': 'ABCD'[i], 'text': o[:120],
                'answer': q['answer'],
            })
            break

    # A. option A is Chinese stem continuation
    # Triggers:
    # - optA is substantial Chinese with NO english (>15 chars Chinese, no English words ≥3)
    # - stem ends with `:`/`：`/`?`/`？` (incomplete, expects continuation)
    # - the Chinese-only optA doesn't look like a real answer (real answers are usually shorter/with numbers)
    if opts[0]:
        opt_a = opts[0]
        if (chinese_chars(opt_a) >= 12
            and not has_substantial_english(opt_a)
            and re.search(r'[:：?？]\s*$', stem.rstrip())
            and not re.search(r'\d', opt_a)):  # exclude options like "10 英尺"
            issues['A_stem_chinese_in_optA'].append({
                'id': qid, 'stem': stem[:80], 'optA': opt_a[:120],
                'optB': opts[1][:80] if opts[1] else '',
                'optC': opts[2][:80] if opts[2] else '',
                'optD': opts[3][:80] if opts[3] else '',
                'answer': q['answer'],
            })

    # B. bilingual options split — option pairs alternate EN-only / ZH-only
    if all(opts):
        eo = [is_english_only(o) for o in opts]
        co = [is_chinese_only(o) for o in opts]
        if (eo[0] and co[1] and eo[2] and co[3]) or (co[0] and eo[1] and co[2] and eo[3]):
            issues['B_bilingual_options_split'].append({
                'id': qid, 'stem': stem[:80], 'opts': opts, 'answer': q['answer'],
            })

    # C. option D contaminated — D is long AND contains a new stem keyword + ?
    if opts[3] and len(opts[3]) > 80:
        if STEM_KEYWORDS.search(opts[3]) and ('?' in opts[3] or '？' in opts[3]):
            issues['C_option_d_contaminated'].append({
                'id': qid, 'stem': stem[:80], 'optD': opts[3][:160], 'answer': q['answer'],
            })

    # E. empty non-sign option
    if not is_sign:
        filled = sum(1 for o in opts if o)
        if filled < 4:
            issues['E_empty_non_sign'].append({
                'id': qid, 'stem': stem[:80], 'filled': filled, 'opts': opts,
                'answer': q['answer'],
            })

    # F. duplicates
    nonempty = [o for o in opts if o]
    if len(nonempty) != len(set(nonempty)) and len(nonempty) > 1:
        issues['F_duplicate_options'].append({
            'id': qid, 'stem': stem[:80], 'opts': opts, 'answer': q['answer'],
        })

    # H. stem chinese-only (missing english)
    if not is_sign and is_chinese_only(stem) and chinese_chars(stem) > 10:
        issues['H_stem_chinese_only'].append({
            'id': qid, 'stem': stem[:120], 'opts': opts, 'answer': q['answer'],
        })


print(f'Total questions: {len(qs)}', file=sys.stderr)
order = ['A_stem_chinese_in_optA', 'B_bilingual_options_split', 'C_option_d_contaminated',
         'D_answer_marker_in_option', 'E_empty_non_sign', 'F_duplicate_options',
         'G_stem_too_short', 'H_stem_chinese_only']
print('\nDistribution:', file=sys.stderr)
for cat in order:
    n = len(issues.get(cat, []))
    if n:
        print(f'  {cat}: {n}', file=sys.stderr)

# Total unique question IDs affected
affected = set()
for cat in order:
    for item in issues.get(cat, []):
        affected.add(item['id'])
print(f'\nUnique affected questions: {len(affected)} / {len(qs)} ({100*len(affected)/len(qs):.1f}%)', file=sys.stderr)

os.makedirs('/tmp/nj_build', exist_ok=True)
with open('/tmp/nj_build/audit_report.json', 'w') as f:
    json.dump(issues, f, ensure_ascii=False, indent=2)
print('\nFull report → /tmp/nj_build/audit_report.json', file=sys.stderr)
