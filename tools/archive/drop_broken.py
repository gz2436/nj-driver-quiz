#!/usr/bin/env python3
"""Drop questions that are too broken to display correctly.

Removes:
  - Questions with _needs_review flag (answer letter points to lost option)
  - Questions where stem is < 15 chars
  - Questions with no filled options
"""
import json
import sys
from datetime import date

DATA = '/Users/gavincheung/NYU/Driver/data/questions.json'
CHANGELOG = '/Users/gavincheung/NYU/Driver/docs/CHANGELOG.md'


def main():
    with open(DATA) as f:
        qs = json.load(f)
    before = len(qs)

    dropped = []
    kept = []
    for q in qs:
        reason = None
        if q.get('_needs_review'):
            reason = q['_needs_review']
        elif len(q['stem']) < 15:
            reason = 'stem_too_short'
        elif not any(q['options']):
            reason = 'no_options'
        if reason:
            dropped.append({'id': q['id'], 'reason': reason, 'stem': q['stem'][:120]})
        else:
            # Clean up internal flag
            q.pop('_needs_review', None)
            kept.append(q)

    # Re-id for clean sequential
    for i, q in enumerate(kept, start=1):
        q['id'] = i

    with open(DATA, 'w') as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    print(f'Before: {before}, after: {len(kept)}, dropped: {len(dropped)}', file=sys.stderr)
    from collections import Counter
    print('Drop reasons:', dict(Counter(d['reason'] for d in dropped)), file=sys.stderr)

    today = date.today().isoformat()
    with open(CHANGELOG, 'a') as f:
        f.write(f'\n## {today} — dropped {len(dropped)} broken questions\n\n')
        for d in dropped:
            f.write(f"- Q{d['id']} ({d['reason']}): {d['stem']}\n")


if __name__ == '__main__':
    main()
