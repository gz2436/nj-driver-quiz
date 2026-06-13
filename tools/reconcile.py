#!/usr/bin/env python3
"""Reconcile all parsed sources into the final data/questions.json.

Steps:
1. Load parsed_full + parsed_easy + topics.
2. Mark questions in full that match easy stems → is_common_mistake.
3. Apply verified answer corrections (from verify_conflicts.json — only high-confidence).
4. Map each question to explanation_key based on topics + stem keywords.
5. Strip broken-stem questions (length < 15 chars) and other irrecoverable.
6. Deduplicate by stem fingerprint.
7. Strip __IMG__ markers from stem, extract to stem_img field.
8. Output data/questions.json with stable IDs.

Also writes:
- data/topics.json (metadata only)
- docs/CHANGELOG.md (auto-generated change list)
"""
import json
import os
import re
import sys
from datetime import date

BUILD = '/tmp/nj_build'
DATA = '/Users/gavincheung/NYU/Driver/data'
DOCS = '/Users/gavincheung/NYU/Driver/docs'

# High-confidence corrections (from verify_facts.py output, after human-review-style filter)
# These flip the answer letter where the docx is unambiguously wrong vs. NJ Manual.
ANSWER_CORRECTIONS = {
    # original_index_in_full: (new_answer_letter, reason)
    # Q9 = original index 8: basic license age 17 → 18 (Manual p16)
    8: ('C', 'Manual p16: basic license age is 18; "17" is probationary'),
    # Q432 = idx 431: park from crosswalk 10 → 25 ft (Manual p86)
    431: ('C', 'Manual p86 / N.J.S.A. 39:4-138: 25 ft from crosswalk'),
    # Q511 = idx 510: under-21 BAC 0.00% → 0.01% (Manual p117)
    510: ('C', 'Manual p117: under-21 BAC limit is 0.01% (zero-tolerance)'),
    # Q512 = idx 511: adult BAC 0.07% → 0.08% (Manual p117)
    511: ('B', 'Manual p117: adult BAC limit is 0.08%'),
}

# Stems that look intractably broken (very short after parser fixes); drop these
# Index list will be re-derived from the parsed data, not hardcoded.

# Explanation routing: (topic, stem-regex) → explanation_key
# Checked in order; first match wins.
EXPLANATION_ROUTES = [
    # BAC
    ('bac_levels', r'21\s*years\s*of\s*age\s*or\s*older|adult.*BAC|drivers\s+who\s+are\s+21', 'adult_bac'),
    ('bac_levels', r'under.*twenty.?one|under\s*21|21\s*岁\s*以下', 'under21_bac'),
    # Alcohol equivalents
    ('alcohol_equivalent', r'.*', 'alcohol_equivalent'),
    # DUI offense by ordinal
    ('dui_offenses', r'first\s+conviction|first\s+offense|first\s+DUI|initial\s+DUI|初犯|第一次', 'dui_first_offense'),
    ('dui_offenses', r'second\s+conviction|second\s+DUI|second\s+offense|第二次', 'dui_second_offense'),
    ('dui_offenses', r'third\s+DUI|third\s+conviction|第三次', 'dui_third_offense'),
    ('dui_offenses', r'refus.*chemical|拒绝.*化学测试|breathalyzer.*refus|拒绝.*呼气', 'dui_refusal'),
    ('dui_offenses', r'.*', 'dui_first_offense'),  # fallback
    # Parking
    ('parking_distance', r'fire\s+hydrant|消防(栓|龙头)', 'park_fire_hydrant'),
    ('parking_distance', r'crosswalk|人行(横道|道)', 'park_crosswalk'),
    ('parking_distance', r'stop\s+sign|停车标志|停止信号', 'park_stop_sign'),
    ('parking_distance', r'fire\s+station|消防站', 'park_fire_station'),
    ('parking_distance', r'railroad|铁路', 'park_railroad'),
    # Speed/points
    ('speed_points', r'tailgating|紧贴跟车', 'tailgating_points'),
    ('speed_points', r'racing|reckless|赛车|鲁莽', 'reckless_racing_points'),
    ('speed_points', r'improper\s+passing|不正确超车|不当超车', 'improper_passing_points'),
    ('speed_points', r'slow\s+speed|wrong\s+way|crosswalk.*stop|低速.*阻碍', 'slow_speed_points'),
    ('speed_points', r'speed\s+limit.*posted|超速.*分|miles.*per.*hour.*over', 'speed_points'),
    ('speed_points', r'.*', 'speed_limits'),  # fallback
    # Stopping distance
    ('stopping_distance', r'.*', 'stopping_distance'),
    # GDL
    ('gdl_stages', r'red\s+(reflective\s+)?decal|红牌|红色反光', 'gdl_decal'),
    ('gdl_stages', r'practice|supervis|监督.*驾驶', 'gdl_practice'),
    ('gdl_stages', r'.*', 'gdl_age_summary'),  # fallback
    # License admin
    ('license_admin', r'change.*address|地址.*变更', 'address_change'),
    ('license_admin', r'name\s+change|更改姓名|legal\s+name', 'name_change'),
    ('license_admin', r'move\s+into.*inspect|外州.*验车', 'inspection_after_move'),
    ('license_admin', r'inspection|验车|车辆检查', 'inspection_freq'),
    ('license_admin', r'.*', 'inspection_freq'),  # fallback
    # Insurance
    ('insurance', r'.*', 'uninsured'),
    # Skid/blowout
    ('skid_blowout', r'skid|打滑', 'skid_recovery'),
    ('skid_blowout', r'blowout|爆胎', 'blowout_action'),
    # Hill parking
    ('turning_lanes', r'hill|downhill|uphill|坡|curb|路沿', 'hill_parking_wheels'),
    # Emergency vehicles
    ('emergency_vehicle', r'school\s+bus|校车', 'school_bus_stopped'),
    ('emergency_vehicle', r'.*', 'emergency_vehicle'),
    # Signals
    ('right_of_way', r'flashing\s+red|闪烁红灯|flashing\s+yellow|闪烁黄灯', 'flashing_red_signal'),
    ('right_of_way', r'right\s+on\s+red|红灯右转|red\s+light.*turn', 'right_on_red'),
    ('right_of_way', r'.*', 'right_of_way_intersection'),
    # Hand signals
    ('hand_signals', r'.*', 'hand_signals'),
    # Seat belt
    ('seat_belt', r'.*', 'seat_belt_law'),
    # Night driving
    ('night_driving', r'.*', 'headlight_use'),
    # Curves/hills
    ('curves_hills', r'curve|弯', 'curve_driving'),
    ('curves_hills', r'hill|坡', 'hill_parking_wheels'),
    # Signs (generic, very common; specific sign meaning is in image, not text)
    ('signs', r'shape|形状|octagon|triangle|diamond|pentagon|八边形|三角|菱形', 'sign_shapes'),
    ('signs', r'color|颜色|red\s+sign|yellow\s+sign|green\s+sign|orange', 'sign_colors'),
]


def normalize_stem_for_dedup(stem):
    """Stem fingerprint for dedup. Keeps image filename so sign questions stay distinct."""
    # Extract image filename if present
    img_match = re.search(r'__IMG__([^_]+(?:_[^_]+)*?)__', stem)
    img_part = img_match.group(1) if img_match else ''
    text = re.sub(r'__IMG__[^_]+(?:_[^_]+)*?__', '', stem)
    text = re.sub(r'[\s\W_]+', '', text.lower())
    return f'{img_part}|{text[:140]}'


def split_stem_image(stem):
    """Extract first __IMG__ marker (if any) and return (text_only_stem, image_filename_or_None)."""
    m = re.search(r'__IMG__([^_]+(?:_[^_]+)*?)__', stem)
    if not m:
        return stem.strip(), None
    img = m.group(1)
    text_only = stem[:m.start()] + stem[m.end():]
    text_only = re.sub(r'\s+', ' ', text_only).strip()
    return text_only, img


def route_explanation(topics, stem):
    """Pick the best explanation_key based on topics + stem patterns."""
    # If we have specific topics, use route table; otherwise None
    for topic, pat, key in EXPLANATION_ROUTES:
        if topic in topics and re.search(pat, stem, re.I):
            return key
    return None


def main():
    with open(f'{BUILD}/parsed_full.json') as f:
        full = json.load(f)
    with open(f'{BUILD}/parsed_easy.json') as f:
        easy = json.load(f)
    with open(f'{BUILD}/topics.json') as f:
        topics_data = json.load(f)

    full_tags = topics_data['full_tags']
    easy_tags = topics_data['easy_tags']

    # Easy-quiz stems for is_common_mistake matching
    easy_fingerprints = {normalize_stem_for_dedup(q['stem']) for q in easy}

    out = []
    seen_fingerprints = set()
    changelog = []
    next_id = 1

    for i, q in enumerate(full):
        # Skip clearly broken
        if len(q['stem']) < 15:
            continue
        # Apply corrections
        original_answer = q['answer']
        if i in ANSWER_CORRECTIONS:
            new_ans, reason = ANSWER_CORRECTIONS[i]
            q['answer'] = new_ans
            changelog.append({
                'id_will_be': next_id,
                'old_answer': original_answer,
                'new_answer': new_ans,
                'reason': reason,
                'stem': q['stem'][:100],
            })
        # Dedup
        fp = normalize_stem_for_dedup(q['stem'])
        if fp in seen_fingerprints:
            continue
        seen_fingerprints.add(fp)

        # Split stem + image
        stem_text, stem_img = split_stem_image(q['stem'])
        if not stem_text:
            continue

        topics = full_tags[i]
        explanation_key = route_explanation(topics, stem_text)

        is_common = fp in easy_fingerprints

        out.append({
            'id': next_id,
            'type': 'tf' if q['tf'] else 'mc',
            'stem': stem_text,
            'stem_img': stem_img,
            'options': q['options'],
            'answer': q['answer'],
            'topics': topics,
            'is_common_mistake': is_common,
            'explanation_key': explanation_key,
            'verified': i in ANSWER_CORRECTIONS or explanation_key is not None,
        })
        next_id += 1

    # Save
    os.makedirs(DATA, exist_ok=True)
    with open(f'{DATA}/questions.json', 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Save topics.json (metadata for UI)
    with open(f'{DATA}/topics.json', 'w') as f:
        json.dump(topics_data['topics_meta'], f, ensure_ascii=False, indent=2)

    # Save images.json (basic — alt text uses filename + topic for now)
    images_data = {}
    images_dir = f'{DATA}/images'
    if os.path.isdir(images_dir):
        for fname in os.listdir(images_dir):
            if fname.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                images_data[fname] = {'alt': f'Sign image {fname}'}
    with open(f'{DATA}/images.json', 'w') as f:
        json.dump(images_data, f, ensure_ascii=False, indent=2)

    # Save changelog
    today = date.today().isoformat()
    log = [
        '# 题库变更日志 / Question Bank Changelog',
        '',
        f'## {today}',
        '',
        f'Initial release. {len(out)} questions. Below: answer corrections vs. source docx.',
        '',
    ]
    for entry in changelog:
        log.append(f"- **Q{entry['id_will_be']}** {entry['old_answer']} → **{entry['new_answer']}** — {entry['reason']}")
        log.append(f"  > {entry['stem']}")
    log.append('')
    with open(f'{DOCS}/CHANGELOG.md', 'w') as f:
        f.write('\n'.join(log))

    # Stats
    print(f'Final question count: {len(out)}', file=sys.stderr)
    print(f'  Common-mistake tagged: {sum(1 for q in out if q["is_common_mistake"])}', file=sys.stderr)
    print(f'  T/F: {sum(1 for q in out if q["type"] == "tf")}', file=sys.stderr)
    print(f'  With image: {sum(1 for q in out if q["stem_img"])}', file=sys.stderr)
    print(f'  With explanation: {sum(1 for q in out if q["explanation_key"])}', file=sys.stderr)
    print(f'  Verified (corrected or explained): {sum(1 for q in out if q["verified"])}', file=sys.stderr)
    print(f'  Corrections applied: {len(changelog)}', file=sys.stderr)

    from collections import Counter
    topic_dist = Counter()
    for q in out:
        for t in q['topics']:
            topic_dist[t] += 1
    print('\nTopic distribution (final):', file=sys.stderr)
    for t, n in topic_dist.most_common():
        print(f'  {t}: {n}', file=sys.stderr)


if __name__ == '__main__':
    main()
