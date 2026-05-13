#!/usr/bin/env python3
"""为 27 条 fuzzy-match 的 mistakes 题补 is_duplicate_of + is_common_mistake 同步。

mistakes 是 complete 的子集 → 每条 mistakes 题应该指向 complete 的某条。
之前我们只严格匹配 stem 拿到 91 条，27 条因 stem 文字小差异漏标。

幂等：已标 is_duplicate_of 的不动。
"""
import json
import re
from pathlib import Path

ROOT = Path('/Users/gavincheung/NYU/Driver')


def normalize(s):
    return re.sub(r'[\s\.,。、，：:?？!！"\'""()（）\-—《》<>]', '', (s or '').lower())


def main():
    qs = json.loads((ROOT / 'data' / 'questions.json').read_text())
    qs_by_id = {q['id']: q for q in qs}

    complete_qs = [q for q in qs if q.get('source_doc') == 'complete']
    mistakes_orphans = [q for q in qs if q.get('source_doc') == 'mistakes'
                         and not q.get('is_duplicate_of')]

    # 索引 complete by normalized stem prefix
    complete_by_norm_full = {}
    complete_by_norm_30 = {}
    for q in complete_qs:
        n = normalize(q.get('stem', ''))
        if n:
            complete_by_norm_full.setdefault(n, q)
            complete_by_norm_30.setdefault(n[:30], q)

    fixed = []
    still_orphan = []
    for mq in mistakes_orphans:
        nstem = normalize(mq.get('stem', ''))
        target = complete_by_norm_full.get(nstem)
        if not target and len(nstem) > 20:
            target = complete_by_norm_30.get(nstem[:30])
        if target:
            mq['is_duplicate_of'] = target['id']
            # 同步 is_common_mistake 到 complete 那条
            if not target.get('is_common_mistake'):
                target['is_common_mistake'] = True
            fixed.append((mq['id'], target['id']))
        else:
            still_orphan.append(mq['id'])

    (ROOT / 'data' / 'questions.json').write_text(
        json.dumps(qs, ensure_ascii=False, indent=2)
    )
    print(f'fixed {len(fixed)} fuzzy-duplicate mistakes')
    for m, c in fixed[:10]:
        print(f'  Q{m} -> dup_of Q{c}')
    if len(fixed) > 10:
        print(f'  ... +{len(fixed) - 10} more')
    print(f'\nstill-orphan mistakes (truly unique): {len(still_orphan)}')
    print(f'  IDs: {still_orphan}')


if __name__ == '__main__':
    main()
