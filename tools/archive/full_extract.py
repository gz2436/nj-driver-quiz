#!/usr/bin/env python3
"""Full extractor: two source docx -> data/questions.json.

Lossless: every identifiable question is kept. Problematic ones get a
needs_review marker instead of being dropped. Replaces the lossy three-stage
pipeline (parse_docx -> reconcile -> drop_broken).

Outputs:
  data/questions.json       — all questions, multiple types
  data/images/              — exported images referenced by questions
  data/extract_report.json  — counts and breakdown by type / needs_review

Question types:
  mc          stem + 4 options + answer letter
  mc_image    same + stem_img
  qa          stem + answer_text (no options)
  qa_image    same + stem_img
  unknown     content preserved but format didn't fit (rare)
"""
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

ROOT = Path('/Users/gavincheung/NYU/Driver')
SOURCES = ROOT / 'sources'
DATA = ROOT / 'data'
IMAGES_DIR = DATA / 'images'

DOCX_FULL = SOURCES / '美国新泽西驾照笔试题-ch eng（完整版）.docx'
DOCX_MIST = SOURCES / '美国新泽西驾照笔试题-ch eng（易错题）.docx'

RE_ANSWER_ANY = re.compile(r'\(([A-D])\)')
RE_EMPTY_PAREN = re.compile(r'\(\s*\)')
RE_QA_ANSWER = re.compile(r'答\s*[：:]\s*(.+)')
# \b doesn't work after CJK in Python 3 default mode (CJK chars are \w).
# Option letter (A-D + period) is valid when preceded by start, whitespace,
# CJK, digit, lowercase ASCII letter, or punctuation — basically anything
# except an uppercase ASCII letter (which would make it part of an acronym).
RE_OPTION_LETTER = re.compile(r'(?:^|(?<=[^A-Z]))([ABCD])[.．。]\s*')


def read_paragraphs(docx_path):
    """Return (paragraphs, rels_map). paragraphs is a list of
    {'text': str, 'image_rids': [str]} in document order."""
    with zipfile.ZipFile(docx_path) as z:
        doc_xml = z.read('word/document.xml')
        rels_xml = z.read('word/_rels/document.xml.rels')

    rels_root = ET.fromstring(rels_xml)
    rels = {}
    for child in rels_root:
        rid = child.get('Id')
        target = child.get('Target')
        if target and target.startswith('media/'):
            rels[rid] = target

    root = ET.fromstring(doc_xml)
    paras = []
    for p in root.iter(f'{{{NS_W}}}p'):
        texts = []
        image_rids = []
        for elem in p.iter():
            tag = elem.tag.split('}')[-1]
            if tag == 't' and elem.text:
                texts.append(elem.text)
            elif tag == 'blip':
                embed = elem.get(f'{{{NS_R}}}embed')
                if embed:
                    image_rids.append(embed)
        paras.append({
            'text': ''.join(texts),
            'image_rids': image_rids,
        })
    return paras, rels


def export_image(docx_path, rels, rid, doc_label, idx):
    """Copy image out of docx zip into data/images/. Return bare filename or None.
    Site code (quiz.html) prepends '../data/images/' so stem_img is filename only."""
    target = rels.get(rid)
    if not target:
        return None
    src_path = 'word/' + target
    ext = target.split('.')[-1].lower()
    out_name = f'img_{doc_label}_{idx:03d}.{ext}'
    out_path = IMAGES_DIR / out_name
    if not out_path.exists():
        with zipfile.ZipFile(docx_path) as z:
            try:
                with z.open(src_path) as f:
                    out_path.write_bytes(f.read())
            except KeyError:
                return None
    return out_name


def split_options(line):
    """Split a line like 'A. foo B. bar C. baz D. quux' into [A, B, C, D].
    Returns 4-element list (some entries may be ''), or None if < 2 markers."""
    matches = list(RE_OPTION_LETTER.finditer(line))
    if len(matches) < 2:
        return None
    by_letter = {}
    for i, m in enumerate(matches):
        letter = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        text = line[start:end].strip()
        # keep only first occurrence of each letter
        by_letter.setdefault(letter, text)
    return [by_letter.get(L, '') for L in 'ABCD']


def is_stem_or_qa(text):
    """True if this paragraph starts a new question (not a continuation)."""
    if RE_QA_ANSWER.search(text):
        return True
    # Standalone (X) or () at end -> new stem
    if re.search(r'\(([A-D])\)\s*$', text):
        return True
    if re.search(r'\(\s*\)\s*$', text):
        return True
    return False


def lookahead_options(paras, start_idx, max_paras=10):
    """Gather option text after `start_idx` until 4 options found or stop hit.

    Algorithm: scan up to `max_paras` paragraphs. For each line:
      - Text BEFORE first letter-marker -> goes to pending continuations queue
      - Each letter-marker -> takes text to next marker as that letter's option
      - Lines with no markers -> entire line goes to pending continuations
    Then fill any missing A/B/C/D slots from the FIFO continuations queue.
    This handles mixed-prefix sources, prefix-less sources, and bilingual splits.
    """
    options_map = {}
    pending = []
    consumed = 0
    for j in range(start_idx + 1, min(start_idx + 1 + max_paras, len(paras))):
        text = paras[j]['text'].strip()
        if not text:
            consumed = j - start_idx
            continue
        if is_stem_or_qa(text):
            consumed = j - start_idx - 1
            break
        matches = list(RE_OPTION_LETTER.finditer(text))
        if matches:
            prefix_text = text[:matches[0].start()].strip()
            if prefix_text:
                pending.append(prefix_text)
            for k, m in enumerate(matches):
                letter = m.group(1)
                seg_start = m.end()
                seg_end = matches[k + 1].start() if k + 1 < len(matches) else len(text)
                seg = text[seg_start:seg_end].strip()
                options_map.setdefault(letter, seg)
        else:
            pending.append(text)
        consumed = j - start_idx
        # Early stop: all 4 filled and we've moved past stem
        if all(L in options_map for L in 'ABCD') and not pending:
            break

    # Fill missing slots from pending queue (FIFO, in A->B->C->D order)
    for L in 'ABCD':
        if L not in options_map and pending:
            options_map[L] = pending.pop(0)

    # Any leftover continuations append to D (or last filled letter)
    if pending:
        for L in 'DCBA':
            if L in options_map and options_map[L]:
                options_map[L] = (options_map[L] + ' ' + ' '.join(pending)).strip()
                break

    if not options_map:
        return None, consumed

    return [options_map.get(L, '') for L in 'ABCD'], consumed


def make_mc(stem, options, answer, doc_label, para_idx, needs_review=None):
    return {
        'type': 'mc',
        'stem': stem,
        'stem_img': None,
        'options': options,
        'answer': answer,
        'answer_text': None,
        'topics': ['unclassified'],
        'is_common_mistake': False,
        'explanation_key': None,
        'verified': False,
        'needs_review': needs_review,
        'source_doc': doc_label,
        'source_para_idx': para_idx,
        'is_duplicate_of': None,
    }


def make_qa(stem, answer_text, doc_label, para_idx, needs_review=None):
    return {
        'type': 'qa',
        'stem': stem,
        'stem_img': None,
        'options': [],
        'answer': None,
        'answer_text': answer_text,
        'topics': ['unclassified'],
        'is_common_mistake': False,
        'explanation_key': None,
        'verified': False,
        'needs_review': needs_review,
        'source_doc': doc_label,
        'source_para_idx': para_idx,
        'is_duplicate_of': None,
    }


def extract_from_docx(docx_path, doc_label):
    paras, rels = read_paragraphs(docx_path)
    questions = []

    i = 0
    while i < len(paras):
        text = paras[i]['text'].strip()
        if not text:
            i += 1
            continue

        # Try MC with (X) answer marker (anywhere in line, prefer end)
        answer_matches = list(RE_ANSWER_ANY.finditer(text))
        valid_markers = []
        for m in answer_matches:
            tail = text[m.end():].strip()
            if not tail or re.match(r'[ABCD][.．。]\s', tail):
                valid_markers.append(m)
        if valid_markers:
            m = valid_markers[-1]
            answer = m.group(1)
            stem = text[:m.start()].rstrip(' :：，,')
            after = text[m.end():].strip()
            consumed = 0
            options = None

            # If stem is empty or just trailing punctuation, look BACK for the
            # actual stem (English line above, often with Chinese continuation)
            stem_is_thin = (not stem) or len(stem.strip(' :：，,。.')) <= 3
            if stem_is_thin:
                back_parts = []
                for k in range(i - 1, max(-1, i - 4), -1):
                    prev = paras[k]['text'].strip()
                    if not prev:
                        if back_parts:
                            break
                        continue
                    # Stop on a previous stem or Q&A — don't steal it
                    if is_stem_or_qa(prev):
                        break
                    if RE_OPTION_LETTER.search(prev):
                        break
                    # Skip if previous line looks like a Q&A answer
                    if RE_QA_ANSWER.search(prev):
                        break
                    back_parts.insert(0, prev)
                    # Stop if we collected enough text
                    if sum(len(p) for p in back_parts) > 20:
                        break
                if back_parts:
                    stem = (' '.join(back_parts) + ' ' + stem).strip()

            # If still empty, look ahead for stem
            if not stem:
                for k in range(i + 1, min(i + 4, len(paras))):
                    nxt = paras[k]['text'].strip()
                    if not nxt:
                        continue
                    if RE_OPTION_LETTER.search(nxt):
                        break
                    if is_stem_or_qa(nxt):
                        break
                    stem = nxt
                    consumed = k - i
                    break

            # Bilingual stem continuation: if the next non-empty paragraph is
            # mostly CJK (echoing the English stem in Chinese) AND the line
            # after it has option markers, merge it into stem. A bilingual
            # OPTION line (English + Chinese on same line) is NOT a continuation.
            scan = i + 1 + consumed
            while scan < len(paras):
                nxt = paras[scan]['text'].strip()
                if not nxt:
                    scan += 1
                    continue
                if RE_OPTION_LETTER.search(nxt) or is_stem_or_qa(nxt):
                    break
                # Must be mostly CJK (option lines are bilingual = significant ASCII)
                cjk = len(re.findall(r'[一-鿿]', nxt))
                ascii_letters = len(re.findall(r'[A-Za-z]', nxt))
                if cjk < 5 or ascii_letters > 4:
                    break
                # Look further: does the next non-empty paragraph have option markers?
                has_opt_after = False
                for l in range(scan + 1, min(scan + 4, len(paras))):
                    ltxt = paras[l]['text'].strip()
                    if not ltxt:
                        continue
                    if RE_OPTION_LETTER.search(ltxt):
                        has_opt_after = True
                    break
                if has_opt_after:
                    stem = (stem + ' ' + nxt).strip()
                    consumed = scan - i
                break

            if after:
                options = split_options(after)

            if not options or sum(1 for o in options if o.strip()) < 4:
                la_opts, la_consumed = lookahead_options(paras, i + consumed)
                if la_opts:
                    if options and sum(1 for o in options if o.strip()) >= 2:
                        # Merge: keep partials from inline, fill gaps from lookahead
                        merged = list(options)
                        for k, v in enumerate(la_opts):
                            if v.strip() and not merged[k].strip():
                                merged[k] = v
                        options = merged
                    else:
                        options = la_opts
                    consumed += la_consumed

            if not options:
                options = ['', '', '', '']
                needs = 'no_options'
            else:
                filled = sum(1 for o in options if o.strip())
                if filled == 4:
                    needs = None
                elif filled >= 1:
                    needs = 'orphan_answer'
                else:
                    needs = 'no_options'

            # Check stem length — different threshold for CJK vs ASCII.
            # Pure CJK sentence of 6+ chars is fine; pure ASCII needs 12+.
            if needs is None:
                clean = stem.strip(' :：，,。.')
                cjk_count = len(re.findall(r'[一-鿿]', clean))
                ascii_count = len(re.findall(r'[A-Za-z]', clean))
                if cjk_count >= 6:
                    pass  # fine, CJK has enough content
                elif ascii_count >= 12:
                    pass  # fine, English has enough words
                elif cjk_count + ascii_count >= 10:
                    pass  # mixed and sufficient
                else:
                    needs = 'stem_too_short'

            q = make_mc(stem, options, answer, doc_label, i, needs_review=needs)
            questions.append(q)
            i += 1 + consumed
            continue

        # MC with empty () marker — missing answer letter
        empty = list(RE_EMPTY_PAREN.finditer(text))
        if empty and re.search(r'\(\s*\)\s*$', text):
            m = empty[-1]
            stem = text[:m.start()].rstrip(' :：')
            la_opts, consumed = lookahead_options(paras, i)
            options = la_opts or ['', '', '', '']
            q = make_mc(stem, options, None, doc_label, i,
                        needs_review='missing_answer')
            questions.append(q)
            i += 1 + consumed
            continue

        # Q&A: 答：...
        m_qa = RE_QA_ANSWER.search(text)
        if m_qa:
            answer_text = m_qa.group(1).strip()
            stem = text[:m_qa.start()].rstrip(' :：')
            # If stem empty, look back
            if not stem:
                for k in range(i - 1, max(-1, i - 4), -1):
                    prev = paras[k]['text'].strip()
                    if not prev:
                        continue
                    # Don't consume a stem that was already used by a prior MC
                    if RE_ANSWER_ANY.search(prev) or RE_EMPTY_PAREN.search(prev):
                        continue
                    if RE_QA_ANSWER.search(prev):
                        continue
                    if re.match(r'^[ABCD][.．。]', prev):
                        continue
                    stem = prev
                    break
            needs = None
            if not stem:
                needs = 'stem_too_short'
                stem = '(无题干)'
            q = make_qa(stem, answer_text, doc_label, i, needs_review=needs)
            questions.append(q)
            i += 1
            continue

        i += 1

    return questions, paras, rels


def bind_images(questions, paras, docx_path, rels, doc_label, image_counter):
    """For each paragraph containing images, attach to the nearest question
    by source_para_idx. Skip if question already has an image (one image per Q)."""
    q_by_para = {q['source_para_idx']: q for q in questions}
    q_paras = sorted(q_by_para.keys())

    for i, p in enumerate(paras):
        if not p['image_rids']:
            continue
        # Find nearest question paragraph idx (preceding within 5 paragraphs preferred,
        # otherwise nearest following)
        before = [pi for pi in q_paras if pi <= i and i - pi <= 5]
        candidate = None
        if before:
            candidate = q_by_para[before[-1]]
        else:
            after = [pi for pi in q_paras if pi > i and pi - i <= 5]
            if after:
                candidate = q_by_para[after[0]]
        if candidate is None or candidate.get('stem_img'):
            continue
        for rid in p['image_rids']:
            image_counter[0] += 1
            rel = export_image(docx_path, rels, rid, doc_label, image_counter[0])
            if rel:
                candidate['stem_img'] = rel
                if candidate['type'] == 'mc':
                    candidate['type'] = 'mc_image'
                elif candidate['type'] == 'qa':
                    candidate['type'] = 'qa_image'
                break


def normalize_stem(s):
    return re.sub(r'\s+', '', s or '')[:50]


def preserve_old_metadata(new_questions, old_path):
    """Carry over topics, explanation_key, is_common_mistake from a previous bank
    where stems match — so we don't lose the curation work."""
    if not old_path.exists():
        return
    try:
        old = json.loads(old_path.read_text())
    except Exception:
        return
    old_by_key = {}
    for q in old:
        k = normalize_stem(q.get('stem', ''))
        if k:
            old_by_key.setdefault(k, q)
    carried = 0
    for q in new_questions:
        k = normalize_stem(q['stem'])
        if k in old_by_key:
            old_q = old_by_key[k]
            if old_q.get('topics') and old_q['topics'] != ['general']:
                q['topics'] = old_q['topics']
            elif old_q.get('topics'):
                q['topics'] = old_q['topics']
            if old_q.get('explanation_key'):
                q['explanation_key'] = old_q['explanation_key']
            if old_q.get('verified'):
                q['verified'] = old_q['verified']
            carried += 1
    print(f'  Preserved metadata for {carried} questions from old bank', file=sys.stderr)


def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    image_counter = [0]

    print('Extracting from 完整版.docx ...', file=sys.stderr)
    full_qs, full_paras, full_rels = extract_from_docx(DOCX_FULL, 'complete')
    print(f'  -> {len(full_qs)} questions', file=sys.stderr)
    bind_images(full_qs, full_paras, DOCX_FULL, full_rels, 'complete', image_counter)

    print('Extracting from 易错题.docx ...', file=sys.stderr)
    mist_qs, mist_paras, mist_rels = extract_from_docx(DOCX_MIST, 'mistakes')
    print(f'  -> {len(mist_qs)} questions', file=sys.stderr)
    bind_images(mist_qs, mist_paras, DOCX_MIST, mist_rels, 'mistakes', image_counter)

    # Combine in source order: 完整版 first, then 易错题
    all_qs = full_qs + mist_qs

    # Mark is_common_mistake: any stem that also appears in 易错题
    mistake_keys = {normalize_stem(q['stem']) for q in mist_qs if q.get('stem')}
    for q in all_qs:
        if normalize_stem(q['stem']) in mistake_keys:
            q['is_common_mistake'] = True

    # Detect duplicates (preserve all; mark links).
    # Dedup key includes stem_img so that sign questions sharing
    # "What does this sign mean?" stem but different images aren't conflated.
    first_seen = {}
    for idx, q in enumerate(all_qs):
        stem_key = normalize_stem(q['stem'])
        if not stem_key:
            continue
        # For image questions, include image filename in key
        if q.get('stem_img'):
            key = (stem_key, q['stem_img'])
        else:
            key = (stem_key, None)
        if key in first_seen:
            q['is_duplicate_of'] = first_seen[key] + 1  # id is 1-based
        else:
            first_seen[key] = idx

    # Preserve metadata from old bank
    preserve_old_metadata(all_qs, DATA / 'questions.pre_full_extract.json')

    # Assign sequential IDs
    for i, q in enumerate(all_qs, 1):
        q['id'] = i
    # Reorder dict so id is first key
    all_qs = [
        {'id': q['id'], **{k: v for k, v in q.items() if k != 'id'}}
        for q in all_qs
    ]

    # Write
    (DATA / 'questions.json').write_text(
        json.dumps(all_qs, ensure_ascii=False, indent=2)
    )

    # Report
    type_counts = Counter(q['type'] for q in all_qs)
    nr_counts = Counter(q['needs_review'] for q in all_qs if q.get('needs_review'))
    report = {
        'total': len(all_qs),
        'by_type': dict(type_counts),
        'needs_review': dict(nr_counts),
        'duplicates': sum(1 for q in all_qs if q.get('is_duplicate_of')),
        'common_mistake': sum(1 for q in all_qs if q.get('is_common_mistake')),
        'with_image': sum(1 for q in all_qs if q.get('stem_img')),
        'sources': {
            'complete': len(full_qs),
            'mistakes': len(mist_qs),
        },
    }
    (DATA / 'extract_report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )

    print('\n=== Extract Report ===', file=sys.stderr)
    print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)


if __name__ == '__main__':
    main()
