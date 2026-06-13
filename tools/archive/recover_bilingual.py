#!/usr/bin/env python3
"""Recover missing Chinese translations by re-scanning the source docx text lines.

For each question in current data/questions.json:
1. Find its source position via stem matching (first 30 non-space chars).
2. Scan the lines from marker forward through next-marker to gather candidate option lines.
3. Pair adjacent English/Chinese lines into full bilingual options.
4. Match parsed options to source lines and fill in missing translations.

Writes back to data/questions.json. Logs to /tmp/nj_build/recover_log.json.
"""
import json
import os
import re
import sys
from xml.etree import ElementTree as ET

DATA = '/Users/gavincheung/NYU/Driver/data/questions.json'
LINES_PATH = '/tmp/nj_full_lines.txt'
LOG = '/tmp/nj_build/recover_log.json'

CHINESE_RE = re.compile(r'[一-鿿]')
LEADING_LABEL_RE = re.compile(r'^\s*[A-D][\.．、:：]\s*')
LEADING_IMG_RE = re.compile(r'^__IMG__[^_]+(?:_[^_]+)*?__\s*')


def has_chinese(s):
    return bool(CHINESE_RE.search(s))


def has_substantial_english(s):
    words = re.findall(r'\b[A-Za-z]{2,}\b', s)
    return any(len(w) >= 4 for w in words) or len(words) >= 3


def is_chinese_only(s):
    return has_chinese(s) and not has_substantial_english(s)


def is_english_only(s):
    return has_substantial_english(s) and not has_chinese(s)


def is_bilingual(s):
    return has_substantial_english(s) and has_chinese(s)


def normalize(s):
    """Loose normalization for matching."""
    s = LEADING_IMG_RE.sub('', s)
    s = LEADING_LABEL_RE.sub('', s)
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'[^\w一-鿿]', '', s)
    return s


def strip_option_label(s):
    """Strip 'A.', 'B.' etc. label and image markers."""
    s = LEADING_IMG_RE.sub('', s)
    s = LEADING_LABEL_RE.sub('', s)
    return s.strip()


def main():
    with open(LINES_PATH) as f:
        lines = [l.rstrip() for l in f if l.strip()]

    # Build index: stem-fingerprint -> source position
    marker_re = re.compile(r'\(([A-D])\)')
    marker_positions = []  # list of (line_idx, marker_letter)
    for i, line in enumerate(lines):
        m = marker_re.search(line)
        if m:
            marker_positions.append((i, m.group(1)))

    # For each marker, gather "section" lines (from marker to next marker)
    # Build stem fingerprint from preceding lines + marker line text
    source_index = {}  # fingerprint -> (marker_idx, section_lines)
    for mi_idx, (line_idx, letter) in enumerate(marker_positions):
        # Get stem: marker line text before marker + maybe previous non-option line
        line = lines[line_idx]
        marker_match = marker_re.search(line)
        stem_text = line[:marker_match.start()].strip()
        # Include up to 2 previous lines if they aren't options
        prev_lines = []
        j = line_idx - 1
        # Don't cross into another section
        section_start_floor = marker_positions[mi_idx - 1][0] + 1 if mi_idx > 0 else 0
        while j > section_start_floor and len(prev_lines) < 2:
            prev_line = lines[j]
            if LEADING_LABEL_RE.match(prev_line):
                break
            prev_lines.insert(0, prev_line)
            j -= 1
        full_stem = '\n'.join(prev_lines + [stem_text])
        fp = normalize(full_stem)[:60]
        if not fp:
            continue
        # Lines after marker through next marker
        end_idx = marker_positions[mi_idx + 1][0] if mi_idx + 1 < len(marker_positions) else len(lines)
        section_lines = lines[line_idx + 1:end_idx]
        # Also include any text after marker on marker_line itself
        post_marker_text = line[marker_match.end():].strip()
        if post_marker_text:
            section_lines = [post_marker_text] + section_lines
        source_index[fp] = (line_idx, letter, section_lines)

    print(f'Indexed {len(source_index)} source sections', file=sys.stderr)

    # Match each question to source
    with open(DATA) as f:
        qs = json.load(f)

    recovered = []
    no_match = []
    no_change = []

    for q in qs:
        if q['type'] == 'tf':
            continue
        if all(is_bilingual(o) for o in q['options'] if o):
            continue  # already complete

        q_fp = normalize(q['stem'])[:60]
        # Try exact, then prefix-match
        match = source_index.get(q_fp)
        if not match:
            # Try finding any source fp that overlaps significantly with this question's fp
            for src_fp, src_data in source_index.items():
                if q_fp[:40] and (q_fp[:40] in src_fp or src_fp[:40] in q_fp):
                    match = src_data
                    break
        if not match:
            no_match.append({'id': q['id'], 'stem': q['stem'][:80]})
            continue

        line_idx, src_letter, section_lines = match

        # Build candidate bilingual options from section lines.
        # Strategy: walk lines; pair adjacent EN+ZH lines as a single option.
        candidates = []
        i = 0
        while i < len(section_lines) and len(candidates) < 8:
            cur = strip_option_label(section_lines[i])
            if not cur:
                i += 1
                continue
            # Try pairing with next line
            if i + 1 < len(section_lines):
                nxt = strip_option_label(section_lines[i + 1])
                if is_english_only(cur) and is_chinese_only(nxt):
                    candidates.append(f'{cur} {nxt}')
                    i += 2
                    continue
                if is_chinese_only(cur) and is_english_only(nxt):
                    candidates.append(f'{nxt} {cur}')
                    i += 2
                    continue
            candidates.append(cur)
            i += 1

        # Pre-filter candidates: reject those with embedded option labels (multi-option blobs)
        # or unreasonably long (likely concatenated)
        def candidate_is_clean(cand):
            # Disallow embedded B. / C. / D. labels (suggests it's multiple options merged)
            embedded_labels = len(re.findall(r'\b[A-D][\.．、:：]\s', cand))
            if embedded_labels >= 1:
                return False
            if len(cand) > 200:
                return False
            return True

        candidates = [c for c in candidates if candidate_is_clean(c)]

        # Match: stricter — opt_norm must be a prefix of cand_norm AND cand must be a bilingual EXPANSION,
        # i.e. cand_norm length is between 1x and 2.5x of opt_norm length.
        def opt_match(opt, cand):
            opt_norm = normalize(opt)
            cand_norm = normalize(cand)
            if not opt_norm or not cand_norm:
                return False
            if not (cand_norm.startswith(opt_norm[:30]) or opt_norm[:30] in cand_norm):
                return False
            ratio = len(cand_norm) / max(1, len(opt_norm))
            if ratio < 1.0 or ratio > 2.5:
                return False
            return True

        new_options = []
        changed = False
        for opt in q['options']:
            if not opt:
                new_options.append(opt)
                continue
            if is_bilingual(opt):
                new_options.append(opt)
                continue
            for cand in candidates:
                if is_bilingual(cand) and opt_match(opt, cand):
                    new_options.append(cand)
                    changed = True
                    break
            else:
                new_options.append(opt)

        if changed:
            q['options'] = new_options
            recovered.append({'id': q['id'], 'stem': q['stem'][:80]})
        else:
            no_change.append(q['id'])

    with open(DATA, 'w') as f:
        json.dump(qs, f, ensure_ascii=False, indent=2)

    os.makedirs('/tmp/nj_build', exist_ok=True)
    with open(LOG, 'w') as f:
        json.dump({
            'recovered_count': len(recovered),
            'no_match_count': len(no_match),
            'no_change_count': len(no_change),
            'recovered_samples': recovered[:10],
            'no_match_samples': no_match[:10],
        }, f, ensure_ascii=False, indent=2)

    print(f'Recovered: {len(recovered)} | No source match: {len(no_match)} | No change: {len(no_change)}', file=sys.stderr)


if __name__ == '__main__':
    main()
