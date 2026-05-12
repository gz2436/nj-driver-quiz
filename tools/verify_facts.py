#!/usr/bin/env python3
"""Cross-check docx answers against canonical facts (from NJ manual) and PDF Q&A pairs.

Outputs:
- /tmp/nj_build/canonical_facts.json   — structured facts table
- /tmp/nj_build/verify_conflicts.json  — per-question conflicts requiring resolution
"""
import json
import os
import re
import sys

BUILD = '/tmp/nj_build'

# ---------------------------------------------------------------------------
# Canonical facts (from docs/canonical_facts.md, p.117-162 of NJ manual)
# ---------------------------------------------------------------------------
CANONICAL_FACTS = {
    'adult_bac': {
        'value': '0.08', 'unit': '%', 'page': 'p117',
        'topic': 'bac_levels',
        'stem_keywords': [r'21\s*years.*older.*BAC', r'21\s*岁.*以上.*BAC', r'legal\s+BAC.*adult'],
    },
    'under21_bac': {
        'value': '0.01', 'unit': '%', 'page': 'p117',
        'topic': 'bac_levels',
        'stem_keywords': [r'under.*twenty.?one', r'under\s*21', r'21\s*岁\s*以下'],
    },
    'park_fire_hydrant': {
        'value': '10', 'unit': 'ft', 'page': 'p86',
        'topic': 'parking_distance',
        'stem_keywords': [r'fire\s+hydrant', r'消防(栓|龙头)'],
    },
    'park_crosswalk': {
        'value': '25', 'unit': 'ft', 'page': 'p86',
        'topic': 'parking_distance',
        'stem_keywords': [r'crosswalk.*intersection', r'人行(横道|道).*路口'],
    },
    'park_stop_sign': {
        'value': '50', 'unit': 'ft', 'page': 'p86',
        'topic': 'parking_distance',
        'stem_keywords': [r'park.*stop\s+sign', r'stop\s+sign.*park', r'(停车标志|停止信号).*泊?车'],
    },
    'speed_11_over_points': {
        'value': '2', 'unit': 'points', 'page': 'p140',
        'topic': 'speed_points',
        'stem_keywords': [r'eleven\s+miles\s+per\s+hour\s+over', r'11.*英里.*超', r'1.14\s*mph.*over'],
    },
    'speed_27_over_points': {
        'value': '4', 'unit': 'points', 'page': 'p140',
        'topic': 'speed_points',
        'stem_keywords': [r'twenty.?seven\s+miles\s+per\s+hour\s+over', r'27.*英里.*超'],
    },
    'speed_30_over_points': {
        'value': '5', 'unit': 'points', 'page': 'p140',
        'topic': 'speed_points',
        'stem_keywords': [r'thirty\s+or\s+more\s+miles\s+per\s+hour', r'30.*英里.*超.*更多'],
    },
    'tailgating_points': {
        'value': '5', 'unit': 'points', 'page': 'p141',
        'topic': 'speed_points',
        'stem_keywords': [r'[Tt]ailgating.*point', r'紧贴跟车.*分'],
    },
    'racing_points': {
        'value': '5', 'unit': 'points', 'page': 'p140',
        'topic': 'speed_points',
        'stem_keywords': [r'racing\s+on\s+a?\s*highway.*point', r'高速上赛车.*分'],
    },
    'address_change_window': {
        'value': '1 week', 'unit': '', 'page': 'p6',
        'topic': 'license',
        'stem_keywords': [r'change.*address.*report', r'地址.*变更.*报告', r'address.*Motor\s+Vehicle'],
    },
    'name_change_window': {
        'value': '2 weeks', 'unit': '', 'page': 'p6',
        'topic': 'license',
        'stem_keywords': [r'name\s+change.*report', r'legal\s+name\s+change', r'更改姓名.*报告'],
    },
    'inspection_after_move': {
        'value': '14 days', 'unit': '', 'page': 'p162',
        'topic': 'license',
        'stem_keywords': [r'move\s+into\s+New\s+Jersey.*inspect', r'外州.*验车'],
    },
    'inspection_freq': {
        'value': '2 years', 'unit': '', 'page': 'p162',
        'topic': 'license',
        'stem_keywords': [r'vehicle\s+inspection.*frequency', r'执行\s*车辆\s*检查.*年限'],
    },
    'basic_license_age': {
        'value': '18', 'unit': '', 'page': 'p16',
        'topic': 'gdl_stages',
        'stem_keywords': [r'minimum\s+age.*basic\s+driver\s+license', r'获取.*驾照\s*最小\s*年龄'],
    },
    'register_vehicle_age': {
        'value': '17', 'unit': '', 'page': 'p17',
        'topic': 'gdl_stages',
        'stem_keywords': [r'register\s+a?\s*motor\s+vehicle.*years\s+old', r'年满.*岁.*登记开车'],
    },
    'gdl_decal_color': {
        'value': 'red', 'unit': '', 'page': 'p21',
        'topic': 'gdl_stages',
        'stem_keywords': [r'GDL.*decal\s+color', r'红牌.*学员'],
    },
    'first_dui_fine_low_bac': {
        'value': '$250-$400', 'unit': '', 'page': 'p125',
        'topic': 'dui_offenses',
        'stem_keywords': [r'first\s+conviction.*DUI', r'first\s+DUI', r'初犯.*酒驾', r'第一次.*酒驾'],
        'note': 'Applies when BAC < 0.10%; for BAC ≥ 0.10%, fine is $300-$500',
    },
    'second_dui_fine': {
        'value': '$1,000', 'unit': '', 'page': 'p127',
        'topic': 'dui_offenses',
        'stem_keywords': [r'second\s+DUI.*fine', r'第二次.*酒驾.*罚款'],
    },
    'second_dui_jail': {
        'value': '90', 'unit': 'days', 'page': 'p127',
        'topic': 'dui_offenses',
        'stem_keywords': [r'second\s+DUI.*jail', r'第二次.*酒驾.*拘役'],
    },
    'third_dui_jail': {
        'value': '180', 'unit': 'days', 'page': 'p128',
        'topic': 'dui_offenses',
        'stem_keywords': [r'third\s+DUI.*jail', r'第三次.*酒驾.*拘役'],
    },
    'refusal_surcharge': {
        'value': '$1,000', 'unit': 'per year', 'page': 'p129',
        'topic': 'dui_offenses',
        'stem_keywords': [r'refus.*chemical.*surcharge', r'拒绝.*化学测试.*附加费'],
    },
    'three_dui_surcharge': {
        'value': '$1,500', 'unit': 'per year', 'page': 'p129',
        'topic': 'dui_offenses',
        'stem_keywords': [r'three\s+DUI.*surcharge', r'三次.*酒驾.*附加费'],
    },
    'uninsured_1st_fine': {
        'value': '$1,000', 'unit': '', 'page': 'p127',
        'topic': 'insurance',
        'stem_keywords': [r'first\s+offence.*maintain.*auto\s+insurance', r'第一次.*不买车险.*罚款'],
    },
    'uninsured_2nd_fine': {
        'value': '$5,000', 'unit': '', 'page': 'p127',
        'topic': 'insurance',
        'stem_keywords': [r'second\s+conviction.*auto\s+insurance.*fine', r'第二次.*不买车险.*罚款'],
    },
    'uninsured_2nd_jail': {
        'value': '14', 'unit': 'days', 'page': 'p127',
        'topic': 'insurance',
        'stem_keywords': [r'second\s+conviction.*auto\s+insurance.*imprisonment', r'第二次.*不买车险.*拘役'],
    },
    'uninsured_license_loss': {
        'value': '1 year', 'unit': '', 'page': 'p127',
        'topic': 'insurance',
        'stem_keywords': [r'driving\s+without\s+insurance.*loss', r'无保险.*吊销'],
    },
}


def value_matches_option(expected_value, option_text):
    """Check if expected value appears in option text."""
    if not option_text:
        return False
    ev = str(expected_value).lower().strip()
    ot = option_text.lower().strip()
    # Direct substring
    if ev in ot:
        return True
    # Handle "0.08" vs ".08" — strip leading 0
    if ev.startswith('0.') and ev[1:] in ot:
        return True
    # Spelled-out: "one year" vs "1 year"
    word_map = {'1': r'\bone\b', '2': r'\btwo\b', '3': r'\bthree\b', '4': r'\bfour\b', '5': r'\bfive\b', '6': r'\bsix\b', '7': r'\bseven\b', '8': r'\beight\b', '9': r'\bnine\b', '10': r'\bten\b'}
    if ev in word_map and re.search(word_map[ev], ot):
        return True
    return False


def find_matching_fact(stem):
    """Return list of canonical fact keys whose stem_keywords match this question's stem."""
    out = []
    for key, fact in CANONICAL_FACTS.items():
        for kw in fact['stem_keywords']:
            if re.search(kw, stem, re.I):
                out.append(key)
                break
    return out


def main():
    os.makedirs(BUILD, exist_ok=True)
    with open(f'{BUILD}/parsed_full.json') as f:
        qs = json.load(f)

    # Save canonical facts as JSON
    with open(f'{BUILD}/canonical_facts.json', 'w') as f:
        json.dump(CANONICAL_FACTS, f, ensure_ascii=False, indent=2)

    conflicts = []
    for i, q in enumerate(qs):
        if q['tf']:
            continue
        ans_letter = q['answer']
        if ans_letter not in 'ABCD':
            continue
        ans_idx = 'ABCD'.index(ans_letter)
        ans_text = q['options'][ans_idx] if ans_idx < len(q['options']) else ''

        matching = find_matching_fact(q['stem'])
        for key in matching:
            fact = CANONICAL_FACTS[key]
            if not value_matches_option(fact['value'], ans_text):
                # Find which option has the expected value
                correct_letter = None
                for j, opt in enumerate(q['options']):
                    if value_matches_option(fact['value'], opt):
                        correct_letter = 'ABCD'[j]
                        break
                conflicts.append({
                    'index': i,
                    'stem': q['stem'][:120],
                    'options': q['options'],
                    'current_answer': ans_letter,
                    'current_answer_text': ans_text,
                    'matched_fact': key,
                    'expected_value': fact['value'],
                    'expected_unit': fact.get('unit', ''),
                    'suggested_answer': correct_letter,
                    'manual_page': fact['page'],
                    'note': fact.get('note', ''),
                })

    with open(f'{BUILD}/verify_conflicts.json', 'w') as f:
        json.dump(conflicts, f, ensure_ascii=False, indent=2)

    print(f'Verified {len(qs)} questions; found {len(conflicts)} potential conflicts', file=sys.stderr)
    if conflicts:
        print('\nSample conflicts:', file=sys.stderr)
        for c in conflicts[:5]:
            print(f"\n  Q{c['index']+1} [{c['matched_fact']}]", file=sys.stderr)
            print(f"    stem: {c['stem']}", file=sys.stderr)
            print(f"    current: {c['current_answer']} = '{c['current_answer_text']}'", file=sys.stderr)
            print(f"    expected: {c['expected_value']} (manual {c['manual_page']})", file=sys.stderr)
            print(f"    suggest: {c['suggested_answer']}", file=sys.stderr)
            if c['note']:
                print(f"    note: {c['note']}", file=sys.stderr)


if __name__ == '__main__':
    main()
