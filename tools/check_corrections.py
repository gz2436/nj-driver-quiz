#!/usr/bin/env python3
"""Guard the question bank against losing hand corrections.

data/questions.json is the source of truth; question ids are frozen (never renumber).
Every hand correction is logged in data/corrections.json (id, field, old, new, source).

  python3 tools/check_corrections.py            # verify + refresh data/version.json
  python3 tools/check_corrections.py --table    # also print the log as a Markdown table

Exits 1 if questions.json no longer matches the latest correction for any field,
if ids are not unique, or if an answer letter points at an empty option.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QP = os.path.join(ROOT, 'data', 'questions.json')
CP = os.path.join(ROOT, 'data', 'corrections.json')
VP = os.path.join(ROOT, 'data', 'version.json')


def get(question, field):
    m = re.fullmatch(r'(\w+)\[(\d+)\]', field)
    if m:
        return question[m.group(1)][int(m.group(2))]
    return question.get(field)


def main():
    questions = json.load(open(QP, encoding='utf-8'))
    log = json.load(open(CP, encoding='utf-8'))
    by_id = {q['id']: q for q in questions}
    errors = []

    if len(by_id) != len(questions):
        errors.append('duplicate question ids')

    latest = {}
    for rec in log['records']:
        latest[(rec['id'], rec['field'])] = rec
    for (qid, field), rec in sorted(latest.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if qid not in by_id:
            errors.append(f'Q{qid}: question missing (ids are frozen, do not delete or renumber)')
            continue
        current = get(by_id[qid], field)
        if current != rec['new']:
            errors.append(f'Q{qid} {field}: expected {rec["new"]!r}, found {current!r}')

    squash = lambda text: re.sub(r'\s+', '', text or '')
    for q in questions:
        # The site renders stem_en/stem_zh and options_en/options_zh; the combined
        # stem/options strings are kept for older readers and must say the same thing.
        if squash(q['stem']) != squash(q['stem_en'] + q['stem_zh']):
            errors.append(f'Q{q["id"]}: stem differs from stem_en + stem_zh')
        for i, combined in enumerate(q['options']):
            if squash(combined) != squash(q['options_en'][i] + q['options_zh'][i]):
                errors.append(f'Q{q["id"]}: options[{i}] differs from options_en + options_zh')
        # A wrong split boundary leaves a number/letter at the end of the English
        # (e.g. "2 months 2" + "个月"); the site shows the split fields as stored.
        pairs = [('stem', q['stem_en'], q['stem_zh'])] + [
            (f'options[{i}]', q['options_en'][i], q['options_zh'][i]) for i in range(len(q['options']))]
        for label, en, zh in pairs:
            if (re.search(r'\s[A-Z0-9]{1,2}$', en or '') and re.match(r'[\u4e00-\u9fff]', zh or '')
                    and not re.search(r'(&|\bor|\band)\s[A-Z]$', en)):  # "Both A & B" is fine
                errors.append(f'Q{q["id"]} {label}: English ends with a token that belongs to the Chinese: {en[-12:]!r} | {zh[:6]!r}')
        letters = 'ABCD'
        idx = letters.find(q.get('answer') or '?')
        if idx < 0 or idx >= len(q['options']) or not q['options'][idx].strip():
            errors.append(f'Q{q["id"]}: answer {q.get("answer")!r} points at an empty option')
        if q.get('stem_img') and not os.path.exists(os.path.join(ROOT, 'data', 'images', q['stem_img'])):
            errors.append(f'Q{q["id"]}: image {q["stem_img"]} not found')

    counts = {'verified': 0, 'not_in_manual': 0, 'unverified': 0}
    for q in questions:
        status = (q.get('review') or {}).get('status', 'unverified')
        counts[status] = counts.get(status, 0) + 1
    dates = [r['date'] for r in log['records']] + [
        (q.get('review') or {}).get('date', '') for q in questions]
    version = {
        'bank_version': max(d for d in dates if d),
        'manual_edition': log['_meta']['manual_edition'],
        'manual_url': log['_meta']['manual_url'],
        'total': len(questions),
        'checked_against_manual': counts['verified'],
        'not_in_manual': counts['not_in_manual'],
        'unverified': counts['unverified'],
        'corrections': len(latest),
    }
    if not errors:
        with open(VP, 'w', encoding='utf-8') as f:
            f.write(json.dumps(version, ensure_ascii=False, indent=2) + '\n')

    if '--table' in sys.argv:
        print('| 题号 | 字段 | 原值 | 新值 | 出处 | 说明 |')
        print('|---|---|---|---|---|---|')
        for rec in log['records']:
            cell = lambda v: str(v).replace('|', '\\|').replace('\n', ' ')
            print(f'| {rec["id"]} | {rec["field"]} | {cell(rec["old"])} | {cell(rec["new"])} | {cell(rec["source"])} | {cell(rec.get("note", ""))} |')

    if errors:
        print('\n'.join(errors), file=sys.stderr)
        sys.exit(1)
    print(f'ok: {len(latest)} corrections hold; {counts}', file=sys.stderr)


if __name__ == '__main__':
    main()
