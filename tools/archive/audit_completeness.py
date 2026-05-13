#!/usr/bin/env python3
"""阶段 A：审计 data/questions.json vs 源 docx。

输出 data/audit_report.md (人读) + data/audit_report.json (机读)。
不修改 questions.json — 只产报告。

审计四件事：
  1. 还原 Word 渲染题号，给每条 question 算一个 source_label
  2. 漏题：源里的题段 -> 是否都有对应的 question
  3. 答案字母一致性：源 stem 末尾 (X) vs 我们 answer 字段
  4. Q&A 答案文本：源 '答：' 后文本 vs 我们 answer_text 字段
  5. complete 内部 5 条重复，单独列出方便人审
"""
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path('/Users/gavincheung/NYU/Driver')
NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

DOCX = {
    'complete': ROOT / 'sources' / '美国新泽西驾照笔试题-ch eng（完整版）.docx',
    'mistakes': ROOT / 'sources' / '美国新泽西驾照笔试题-ch eng（易错题）.docx',
}

# 段尾 (X) 是典型；但部分题 (X) 在 stem 中间紧跟选项("…？(D) A. …B. ")，也要识别。
RE_ANSWER_LETTER = re.compile(r'\(([A-D])\)(?:\s*$|\s+[A-D]\.)')
RE_ANSWER_EMPTY = re.compile(r'\(\s*\)\s*$')
RE_QA_MARKER = re.compile(r'答\s*[：:]\s*(.*)$')
RE_MANUAL_NUM = re.compile(r'^\s*(\d{1,4})[\.．]\s+\S')


NS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'


def load_docx(path):
    """Return list of paragraphs with numbering + drawing info.

    Each entry: dict(idx, text, num_id, ilvl, num_ord, drawings)
    """
    with zipfile.ZipFile(path) as z:
        doc = ET.fromstring(z.read('word/document.xml'))
        try:
            rels = ET.fromstring(z.read('word/_rels/document.xml.rels'))
            rel_target = {r.get('Id'): r.get('Target')
                          for r in rels.iter(f'{{{NS_PKG}}}Relationship')}
        except KeyError:
            rel_target = {}

    counters = defaultdict(lambda: defaultdict(int))
    paras = []
    for pi, p in enumerate(doc.iter(f'{{{NS}}}p')):
        text = ''.join(t.text or '' for t in p.iter(f'{{{NS}}}t'))
        npr = p.find(f'.//{{{NS}}}numPr')
        num_id = ilvl = num_ord = None
        if npr is not None:
            n_e = npr.find(f'{{{NS}}}numId')
            i_e = npr.find(f'{{{NS}}}ilvl')
            if n_e is not None:
                num_id = n_e.get(f'{{{NS}}}val')
                ilvl = i_e.get(f'{{{NS}}}val') if i_e is not None else '0'
                counters[num_id][ilvl] += 1
                num_ord = counters[num_id][ilvl]
        drawings = []
        for d in p.iter(f'{{{NS}}}drawing'):
            for b in d.iter(f'{{{NS_A}}}blip'):
                rid = b.get(f'{{{NS_R}}}embed')
                if rid and rid in rel_target:
                    drawings.append(rel_target[rid])
        paras.append({
            'idx': pi, 'text': text,
            'num_id': num_id, 'ilvl': ilvl, 'num_ord': num_ord,
            'drawings': drawings,
        })
    return paras


def find_nearest_drawing(paras, pi, max_dist=4):
    """Search within ±max_dist for a paragraph with drawings; return media target or None."""
    for d in range(0, max_dist + 1):
        for delta in (-d, d):
            ix = pi + delta
            if 0 <= ix < len(paras) and paras[ix]['drawings']:
                return paras[ix]['drawings'][0], ix
    return None, None


def source_label(p, doc_label):
    """Make a human-friendly source label for a paragraph."""
    if doc_label == 'mistakes':
        # mistakes 主题号流是 numId=123
        if p['num_id'] == '123' and p['ilvl'] == '0':
            return f'M{p["num_ord"]}'
        return f'M-pi{p["idx"]}'
    # complete: 优先看段首是否有手输 "268." / "640."
    m = RE_MANUAL_NUM.match(p['text'])
    if m:
        return f'C-manual{m.group(1)}'
    if p['num_id'] and p['ilvl'] == '0':
        return f'C-list{p["num_id"]}.{p["num_ord"]}'
    return f'C-pi{p["idx"]}'


def find_source_questions(paras, doc_label):
    """Identify question-start paragraphs in the docx.

    A paragraph is a question if it has any of:
      - ends with (X) or () answer marker
      - contains 答：... (Q&A)
      - is a numbered list ilvl=0 item that introduces options (heuristic)
    Returns list of dicts.
    """
    questions = []
    for i, p in enumerate(paras):
        text = p['text'].strip()
        if not text:
            continue
        m_ans = RE_ANSWER_LETTER.search(text)
        m_empty = RE_ANSWER_EMPTY.search(text)
        m_qa = RE_QA_MARKER.search(text)
        is_question = False
        kind = None
        answer_letter = None
        answer_text = None
        if m_ans:
            is_question = True
            kind = 'mc'
            answer_letter = m_ans.group(1)
        elif m_empty:
            is_question = True
            kind = 'mc_empty'
        elif m_qa:
            is_question = True
            kind = 'qa'
            answer_text = m_qa.group(1).strip()
        if not is_question:
            continue
        questions.append({
            'doc': doc_label,
            'para_idx': p['idx'],
            'source_label': source_label(p, doc_label),
            'kind': kind,
            'source_answer_letter': answer_letter,
            'source_answer_text': answer_text,
            'text': text,
        })
    return questions


def normalize_text(s):
    if not s:
        return ''
    return re.sub(r'\s+', '', s).lower()


def main():
    docs = {label: load_docx(path) for label, path in DOCX.items()}
    src_questions = {label: find_source_questions(paras, label)
                     for label, paras in docs.items()}

    qs = json.loads((ROOT / 'data' / 'questions.json').read_text())
    by_doc_and_pi = defaultdict(dict)
    for q in qs:
        by_doc_and_pi[q.get('source_doc')][q.get('source_para_idx')] = q

    # ---------- 1. 还原题号 ----------
    id_to_label = {}
    for q in qs:
        doc_label = q.get('source_doc')
        pi = q.get('source_para_idx')
        if doc_label in docs and pi is not None and pi < len(docs[doc_label]):
            id_to_label[q['id']] = source_label(docs[doc_label][pi], doc_label)
        else:
            id_to_label[q['id']] = None

    # ---------- 2. 漏题检测 ----------
    unmatched = []  # 源里有但 questions.json 没对应的题段
    matched_pi = defaultdict(set)
    for label, srcq in src_questions.items():
        for sq in srcq:
            if sq['para_idx'] in by_doc_and_pi[label]:
                matched_pi[label].add(sq['para_idx'])
            else:
                unmatched.append(sq)

    # 我们有但源没匹配上的（多提的题）
    extras = []
    for q in qs:
        label = q.get('source_doc')
        pi = q.get('source_para_idx')
        # 是不是源有这个 pi 对应题段？
        src_pi_set = {sq['para_idx'] for sq in src_questions.get(label, [])}
        if pi not in src_pi_set:
            extras.append({
                'id': q['id'],
                'source_doc': label,
                'source_para_idx': pi,
                'type': q.get('type'),
                'stem': (q.get('stem') or '')[:80],
                'is_duplicate_of': q.get('is_duplicate_of'),
            })

    # ---------- 3. 答案字母一致性 ----------
    answer_mismatches = []
    answer_empty_in_source = []
    for sq in [s for ssq in src_questions.values() for s in ssq]:
        q = by_doc_and_pi[sq['doc']].get(sq['para_idx'])
        if not q:
            continue
        if sq['kind'] == 'mc':
            ours = (q.get('answer') or '').strip().upper()
            theirs = sq['source_answer_letter']
            if ours != theirs:
                answer_mismatches.append({
                    'id': q['id'],
                    'source_label': id_to_label.get(q['id']),
                    'our_answer': q.get('answer'),
                    'src_answer': theirs,
                    'stem_preview': (q.get('stem') or '')[:80],
                })
        elif sq['kind'] == 'mc_empty':
            answer_empty_in_source.append({
                'id': q['id'],
                'source_label': id_to_label.get(q['id']),
                'our_answer': q.get('answer'),
                'stem_preview': (q.get('stem') or '')[:80],
            })

    # ---------- 4. Q&A 答案文本核对 ----------
    qa_mismatches = []
    for sq in [s for ssq in src_questions.values() for s in ssq]:
        if sq['kind'] != 'qa':
            continue
        q = by_doc_and_pi[sq['doc']].get(sq['para_idx'])
        if not q:
            continue
        ours_text = (q.get('answer_text') or '').strip()
        src_text = (sq['source_answer_text'] or '').strip()
        if normalize_text(ours_text)[:50] != normalize_text(src_text)[:50]:
            qa_mismatches.append({
                'id': q['id'],
                'source_label': id_to_label.get(q['id']),
                'our_answer_text': ours_text[:120],
                'src_answer_text': src_text[:120],
                'stem_preview': (q.get('stem') or '')[:80],
            })

    # ---------- 5. complete 内部重复 ----------
    # 对每个重复项，看是不是因为图没绑上导致的「假重复」(找一下附近源段有无 drawing)
    internal_dups = []
    for q in qs:
        dup_of = q.get('is_duplicate_of')
        if not dup_of or q.get('source_doc') != 'complete':
            continue
        orig = next((x for x in qs if x['id'] == dup_of), None)
        if orig and orig.get('source_doc') == 'complete':
            # 重复项 + 原题各自找附近的 drawing
            nearby_dup_img, near_pi_d = (None, None)
            nearby_orig_img, near_pi_o = (None, None)
            if q.get('stem_img') is None:
                nearby_dup_img, near_pi_d = find_nearest_drawing(docs['complete'], q['source_para_idx'])
            if orig.get('stem_img') is None:
                nearby_orig_img, near_pi_o = find_nearest_drawing(docs['complete'], orig['source_para_idx'])
            internal_dups.append({
                'duplicate_id': q['id'],
                'original_id': dup_of,
                'duplicate_label': id_to_label.get(q['id']),
                'original_label': id_to_label.get(dup_of),
                'stem_preview': (q.get('stem') or '')[:80],
                'duplicate_img': q.get('stem_img'),
                'original_img': orig.get('stem_img'),
                'nearby_drawing_for_duplicate': nearby_dup_img,
                'nearby_drawing_for_original': nearby_orig_img,
                'likely_false_dup': bool(nearby_dup_img and nearby_orig_img
                                          and nearby_dup_img != nearby_orig_img),
            })

    # ---------- 写报告 ----------
    report = {
        'summary': {
            'total_questions': len(qs),
            'src_complete_questions': len(src_questions['complete']),
            'src_mistakes_questions': len(src_questions['mistakes']),
            'unmatched_in_source': len(unmatched),
            'extra_in_ours': len(extras),
            'answer_letter_mismatches': len(answer_mismatches),
            'answer_empty_in_source': len(answer_empty_in_source),
            'qa_answer_mismatches': len(qa_mismatches),
            'complete_internal_dups': len(internal_dups),
        },
        'id_to_source_label': id_to_label,
        'unmatched_in_source': unmatched,
        'extras_in_ours': extras,
        'answer_letter_mismatches': answer_mismatches,
        'answer_empty_in_source': answer_empty_in_source,
        'qa_answer_mismatches': qa_mismatches,
        'complete_internal_dups': internal_dups,
    }

    out_json = ROOT / 'data' / 'audit_report.json'
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    # Markdown
    lines = ['# 审计报告', '']
    s = report['summary']
    lines.append('## 概览')
    lines.append('')
    lines.append(f'- questions.json 总题数: **{s["total_questions"]}**')
    lines.append(f'- 源 complete 识别题段: **{s["src_complete_questions"]}** '
                 f'(MC 带答案 + 空答案 + Q&A)')
    lines.append(f'- 源 mistakes 识别题段: **{s["src_mistakes_questions"]}**')
    lines.append('')
    lines.append('| 项 | 数量 |')
    lines.append('|---|---|')
    lines.append(f'| 漏题（源里有 / 我们没对应） | {s["unmatched_in_source"]} |')
    lines.append(f'| 多提（我们有 / 源里无对应题段） | {s["extra_in_ours"]} |')
    lines.append(f'| 答案字母不一致（MC） | {s["answer_letter_mismatches"]} |')
    lines.append(f'| 源里就是空答案（()） | {s["answer_empty_in_source"]} |')
    lines.append(f'| Q&A 答案文本不一致 | {s["qa_answer_mismatches"]} |')
    lines.append(f'| complete 内部重复 | {s["complete_internal_dups"]} |')
    lines.append('')

    def section(title, items, fmt):
        lines.append(f'## {title}（{len(items)}）')
        lines.append('')
        if not items:
            lines.append('_无_')
            lines.append('')
            return
        for it in items[:50]:
            lines.append(fmt(it))
        if len(items) > 50:
            lines.append(f'_... 还有 {len(items)-50} 条，详见 audit_report.json_')
        lines.append('')

    section('漏题清单', unmatched,
            lambda x: f'- {x["doc"]}/pi={x["para_idx"]} `{x["source_label"]}` '
                      f'kind={x["kind"]}  text=`{x["text"][:80]}`')
    section('多提清单', extras,
            lambda x: f'- Q{x["id"]} ({x["source_doc"]}/pi={x["source_para_idx"]}, '
                      f'type={x["type"]})  stem=`{x["stem"]}` '
                      f'{"(dup_of=" + str(x["is_duplicate_of"]) + ")" if x["is_duplicate_of"] else ""}')
    section('答案字母不一致', answer_mismatches,
            lambda x: f'- Q{x["id"]} `{x["source_label"]}` 我们={x["our_answer"]!r} '
                      f'源={x["src_answer"]!r}  stem=`{x["stem_preview"]}`')
    section('源里空答案', answer_empty_in_source,
            lambda x: f'- Q{x["id"]} `{x["source_label"]}` 我们={x["our_answer"]!r}  '
                      f'stem=`{x["stem_preview"]}`')
    section('Q&A 答案文本不一致', qa_mismatches,
            lambda x: f'- Q{x["id"]} `{x["source_label"]}`\n'
                      f'  - 我们: `{x["our_answer_text"]}`\n'
                      f'  - 源:   `{x["src_answer_text"]}`\n'
                      f'  - stem: `{x["stem_preview"]}`')
    section('complete 内部重复', internal_dups,
            lambda x: (
                f'- Q{x["duplicate_id"]} `{x["duplicate_label"]}` '
                f'(img={x["duplicate_img"]}) 重复于 Q{x["original_id"]} '
                f'`{x["original_label"]}` (img={x["original_img"]})\n'
                f'  stem=`{x["stem_preview"]}`\n'
                + (f'  ⚠️ 附近源段有不同图片 → 应该是漏绑图导致的假重复\n'
                   f'    dup 应绑: `{x["nearby_drawing_for_duplicate"]}`\n'
                   f'    orig 应绑: `{x["nearby_drawing_for_original"]}`'
                   if x['likely_false_dup'] else '')))

    out_md = ROOT / 'data' / 'audit_report.md'
    out_md.write_text('\n'.join(lines))

    print(f'wrote {out_md}')
    print(f'wrote {out_json}')
    print()
    for k, v in s.items():
        print(f'  {k}: {v}')


if __name__ == '__main__':
    main()
