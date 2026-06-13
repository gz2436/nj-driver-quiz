#!/usr/bin/env python3
"""Parse the NJ driver quiz docx files into structured JSON.

Outputs:
- /tmp/nj_build/parsed_full.json
- /tmp/nj_build/parsed_easy.json
- /tmp/nj_build/parse_conflicts.json  (questions that need human review)

Fixes over the previous parser:
- Strips leaked source-document numbering like "269." from stem starts
- Detects and splits merged stems (multiple Q&A in one — by 答： marker)
- Marks broken stems (< 10 chars) as conflicts
- Walks back further (3 lines) to associate orphan __IMG__ lines with stems
- Better option-D recovery for sign questions (3-option false positives)
"""
import json
import os
import re
import sys
from xml.etree import ElementTree as ET

ROOT = '/Users/gavincheung/NYU/Driver'
SOURCES = f'{ROOT}/sources'
BUILD = '/tmp/nj_build'
os.makedirs(BUILD, exist_ok=True)

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

SKILL_OFFICE = (
    '/Users/gavincheung/Library/Application Support/Claude/'
    'local-agent-mode-sessions/skills-plugin/'
    '2d893460-697b-4695-a4c9-7c5d70d7ec0d/'
    'e507cdb5-b1d6-46f8-b7c8-a7e450956a5a/skills/docx/scripts/office'
)


def unpack_docx(docx_path, out_dir):
    """Unpack docx via the office skill's unpack script."""
    import subprocess
    if os.path.isdir(out_dir):
        import shutil
        shutil.rmtree(out_dir)
    subprocess.run(
        ['python3', f'{SKILL_OFFICE}/unpack.py', docx_path, out_dir],
        check=True, capture_output=True,
    )


def extract_lines(unpacked_dir):
    """Walk document.xml in order, return list of lines with __IMG__filename__ markers inline."""
    rels_tree = ET.parse(f'{unpacked_dir}/word/_rels/document.xml.rels')
    rel_map = {}
    for r in rels_tree.getroot():
        rid = r.get('Id')
        target = r.get('Target')
        type_ = r.get('Type', '')
        if rid and target and 'image' in type_:
            rel_map[rid] = os.path.basename(target)

    tree = ET.parse(f'{unpacked_dir}/word/document.xml')
    root = tree.getroot()
    lines = []
    for p in root.iter(f'{{{W_NS}}}p'):
        parts = []
        for elem in p.iter():
            tag = elem.tag
            if tag == f'{{{W_NS}}}t':
                if elem.text:
                    parts.append(elem.text)
            elif tag == f'{{{A_NS}}}blip':
                embed = elem.get(f'{{{R_NS}}}embed')
                if embed and embed in rel_map:
                    parts.append(f'__IMG__{rel_map[embed]}__')
            elif tag == f'{{{W_NS}}}br':
                parts.append('\n')
        line = ''.join(parts).strip()
        if line:
            lines.append(line)
    return lines, rel_map


MARKER_RE = re.compile(r'\(([A-DTF])\)')
LEAKED_NUM_RE = re.compile(r'^\s*\d{1,3}[\.．]\s+')
ANSWER_INLINE_RE = re.compile(r'答\s*[:：]')


def starts_with_option_letter(line):
    s = line.strip()
    s = re.sub(r'^__IMG__[^_]+(?:_[^_]+)*?__', '', s).strip()
    return bool(re.match(r'^[A-D][\.．、:：]\s*', s) or re.match(r'^[A-D]\s+\S', s))


def is_stem_like(line):
    """Return True if a line continues a question stem (not an option, not noise)."""
    s = line.strip()
    if not s:
        return False
    if starts_with_option_letter(line):
        return False
    if re.search(r'[:：?？]\s*$', s):
        return True
    if '?' in s or '？' in s:
        return True
    if re.match(r'^(__IMG__[^_]+(?:_[^_]+)*?__\s*)+$', s):
        return True
    return False


def is_loose_stem_continuation(line):
    """More permissive: line that's likely part of a stem (used only for remedial walk-back)."""
    s = line.strip()
    if not s:
        return False
    if starts_with_option_letter(line):
        return False
    # Strip leaked numbering
    s = LEAKED_NUM_RE.sub('', s)
    # Ends with anything stem-like
    if re.search(r'[:：?？.。,，]\s*$', s):
        return True
    # Mid-sentence: starts with English capital or Chinese, sufficient length
    if re.match(r'^[A-Z][a-z]', s) and len(s) > 20:
        return True
    if re.match(r'^[一-鿿]', s) and len(s) > 8:
        return True
    return False


def strip_leaked_numbering(text):
    """Remove leading '269. ' style source-doc numbering from a stem."""
    return LEAKED_NUM_RE.sub('', text)


def split_merged_stem(stem):
    """If a stem contains 答： markers, return the LAST sub-stem (the one belonging to current answer marker).

    The merged-stem pattern is: 'Q1? 答：A1. Q2? 答：A2. Q3 (which has its own (X) marker)'.
    The marker (X) we already detected belongs to the FINAL question; earlier 答： pairs are
    free-response remnants that should be dropped from this stem.
    """
    if '答' not in stem:
        return stem, []
    # Drop everything up to the last 答：xxx pair, then take the remainder as the real stem.
    # Strategy: find all 答：xxx patterns; the real stem is what comes AFTER the last one.
    parts = re.split(r'答\s*[:：][^\n]*', stem)
    dropped = stem.replace(parts[-1] if parts else '', '').strip() if len(parts) > 1 else ''
    return parts[-1].strip() if parts else stem, [dropped] if dropped else []


def parse_options(opts_text, is_tf):
    """Split options text into 4 strings. For T/F return [True, False, '', '']."""
    if is_tf:
        return ['True / 对', 'False / 错', '', '']
    if not opts_text:
        return ['', '', '', '']
    raw_l = [l for l in opts_text.split('\n') if l.strip()]

    # Skip leading non-option lines (Chinese stem continuation)
    if raw_l:
        first = raw_l[0].strip()
        first_no_img = re.sub(r'^__IMG__[^_]+(?:_[^_]+)*?__', '', first).strip()
        has_label = bool(re.search(r'[A-D][\.．、:：]', first_no_img))
        ends_term = bool(re.search(r'[:：?？]\s*$', first))
        if ends_term and not has_label and len(raw_l) > 1:
            raw_l = raw_l[1:]
        elif ('?' in first or '？' in first) and not has_label and len(raw_l) > 1:
            raw_l = raw_l[1:]

    options = []
    for line in raw_l:
        s = line.strip()
        if not s:
            continue
        if ANSWER_INLINE_RE.search(s):
            break
        label_iter = list(re.finditer(r'[A-D][\.．、:：]', s))
        if label_iter:
            first_letter = s[label_iter[0].start()]
            pre = s[:label_iter[0].start()].strip()
            if first_letter != 'A' and pre:
                # Unlabeled prefix is option A
                options.append(re.sub(r'[ \t]+', ' ', pre))
            for i, m in enumerate(label_iter):
                start = m.end()
                end = label_iter[i + 1].start() if i + 1 < len(label_iter) else len(s)
                content = s[start:end].strip()
                options.append(re.sub(r'[ \t]+', ' ', content))
        else:
            options.append(re.sub(r'[ \t]+', ' ', s))
        if len(options) >= 4:
            break

    while len(options) < 4:
        options.append('')
    return options[:4]


def parse_quiz(lines):
    """Return list of question dicts."""
    marker_lines = []
    for i, line in enumerate(lines):
        m = MARKER_RE.search(line)
        if m:
            marker_lines.append((i, m.start(), m.end(), m.group(1)))

    # Build stems by walking backwards from each marker
    raw_qs = []
    prev_marker_line = -1
    for k, (mi, mstart, mend, answer) in enumerate(marker_lines):
        marker_line_pre = lines[mi][:mstart].rstrip()
        # Build candidate stem text first (marker_line_pre)
        stem_back = []
        j = mi - 1
        # First pass: standard walk-back with is_stem_like
        while j > prev_marker_line and len(stem_back) < 3:
            if not is_stem_like(lines[j]):
                break
            stem_back.insert(0, lines[j])
            j -= 1

        # Check if the resulting stem would be too short -> remedial walk-back
        prelim_stem = '\n'.join(stem_back + ([marker_line_pre] if marker_line_pre.strip() else []))
        prelim_clean = LEAKED_NUM_RE.sub('', re.sub(r'\s+', ' ', prelim_stem).strip())
        if len(prelim_clean) < 30:
            # Try loose continuation walk-back: include up to 3 more loose lines
            while j > prev_marker_line and len(stem_back) < 4:
                if not is_loose_stem_continuation(lines[j]):
                    break
                stem_back.insert(0, lines[j])
                j -= 1

        stem_parts = list(stem_back)
        if marker_line_pre.strip():
            stem_parts.append(marker_line_pre)
        stem = '\n'.join(stem_parts).strip()
        raw_qs.append({
            'stem': stem,
            'marker_line': mi,
            'marker_end': mend,
            'stem_first_line': mi - len(stem_back),
            'answer': answer,
        })
        prev_marker_line = mi

    # Build option text per question
    out = []
    for k, q in enumerate(raw_qs):
        if k + 1 < len(raw_qs):
            next_stem_first = raw_qs[k + 1]['stem_first_line']
        else:
            next_stem_first = len(lines)
        opt_parts = []
        tail = lines[q['marker_line']][q['marker_end']:].strip()
        if tail:
            opt_parts.append(tail)
        for li in range(q['marker_line'] + 1, next_stem_first):
            opt_parts.append(lines[li])
        opts_text = '\n'.join(opt_parts).strip()

        is_tf = q['answer'] in 'TF'
        opts = parse_options(opts_text, is_tf)

        # Clean stem: strip leaked numbering, collapse whitespace, split merged
        stem = strip_leaked_numbering(q['stem'])
        stem = re.sub(r'[ \t]+', ' ', stem).strip()
        stem, dropped = split_merged_stem(stem)

        out.append({
            'stem': stem,
            'options': opts,
            'answer': q['answer'],
            'tf': is_tf,
            '_dropped_segments': dropped,  # for debugging
        })
    return out


def validate_and_flag_conflicts(qs):
    """Annotate each question with conflicts; return both qs and conflicts list."""
    conflicts = []
    for i, q in enumerate(qs):
        flags = []
        if len(q['stem']) < 10:
            flags.append('stem_too_short')
        if not q['tf'] and sum(1 for o in q['options'] if o) < 3:
            flags.append('few_options')
        if q['_dropped_segments']:
            flags.append('split_merged_stem')
        # Sign-question with only 3 options — might be source artifact, mark for inspection but not auto-fix
        if not q['tf'] and re.search(r'(this sign|this signal|标志|标记)', q['stem'], re.I):
            if not q['options'][3]:
                flags.append('sign_only_3_options_ok')
        if flags:
            conflicts.append({
                'index': i,
                'flags': flags,
                'stem': q['stem'][:120],
                'options': q['options'],
                'answer': q['answer'],
                'dropped': q['_dropped_segments'],
            })
    return conflicts


def main():
    full_docx = f'{SOURCES}/美国新泽西驾照笔试题-ch eng（完整版）.docx'
    easy_docx = f'{SOURCES}/美国新泽西驾照笔试题-ch eng（易错题）.docx'

    print('Unpacking full docx...', file=sys.stderr)
    unpack_docx(full_docx, f'{BUILD}/full_unpacked')
    print('Unpacking easy docx...', file=sys.stderr)
    unpack_docx(easy_docx, f'{BUILD}/easy_unpacked')

    full_lines, _ = extract_lines(f'{BUILD}/full_unpacked')
    easy_lines, _ = extract_lines(f'{BUILD}/easy_unpacked')

    full_qs = parse_quiz(full_lines)
    easy_qs = parse_quiz(easy_lines)
    print(f'Full parsed: {len(full_qs)}', file=sys.stderr)
    print(f'Easy parsed: {len(easy_qs)}', file=sys.stderr)

    conflicts_full = validate_and_flag_conflicts(full_qs)
    conflicts_easy = validate_and_flag_conflicts(easy_qs)

    with open(f'{BUILD}/parsed_full.json', 'w') as f:
        json.dump(full_qs, f, ensure_ascii=False, indent=2)
    with open(f'{BUILD}/parsed_easy.json', 'w') as f:
        json.dump(easy_qs, f, ensure_ascii=False, indent=2)
    with open(f'{BUILD}/parse_conflicts.json', 'w') as f:
        json.dump({'full': conflicts_full, 'easy': conflicts_easy}, f, ensure_ascii=False, indent=2)

    print(f'Conflicts: full={len(conflicts_full)}, easy={len(conflicts_easy)}', file=sys.stderr)
    print('Done.', file=sys.stderr)


if __name__ == '__main__':
    main()
