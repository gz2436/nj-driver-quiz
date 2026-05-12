#!/usr/bin/env python3
"""Tag each question with topic clusters based on stem keywords.

Output: /tmp/nj_build/topics.json (per-question topic tags)
"""
import json
import re
import sys

BUILD = '/tmp/nj_build'

# Topics (key) → (Chinese label, English label, stem-keyword regex)
# A question can match multiple topics. Order matters only for `general` fallback.
TOPICS = {
    'signs': {
        'zh': '交通标志',
        'en': 'Traffic Signs',
        'patterns': [
            r'__IMG__',  # any inline image
            r'this\s+sign',
            r'this\s+signal',
            r'sign\s+mean',
            r'pavement\s+marking',
            r'(标志|标记|路面标线)',
        ],
    },
    'alcohol_equivalent': {
        'zh': '酒精等量换算',
        'en': 'Alcohol Equivalence',
        'patterns': [
            r'ounces?\s+of\s+(beer|wine|whiskey|liquor)',
            r'(beer|wine|whiskey|liquor).*ounces?',
            r'(\d+\s*盎司|盎司.*酒)',
            r'a\s+drink\s+(of|equals?)',
        ],
    },
    'bac_levels': {
        'zh': 'BAC 血液酒精',
        'en': 'BAC Levels',
        'patterns': [
            r'\bBAC\b',
            r'血液酒精',
            r'blood\s+alcohol',
        ],
    },
    'dui_offenses': {
        'zh': '酒驾处罚',
        'en': 'DUI Penalties',
        'patterns': [
            r'\bDUI\b',
            r'(first|second|third).*DUI',
            r'(初犯|第[二三]次).*酒驾',
            r'酒驾.*(罚款|拘役|吊销)',
            r'driving\s+under\s+the\s+influence',
            r'(refus|拒绝).*chemical\s+test',
            r'breathalyzer',
            r'呼气.*测试',
            r'ignition\s+interlock',
            r'点火.*互锁',
        ],
    },
    'parking_distance': {
        'zh': '停车距离',
        'en': 'Parking Distances',
        'patterns': [
            r'park\s+within.*feet',
            r'park.*feet.*of',
            r'(crosswalk|fire\s+hydrant|stop\s+sign|fire\s+station|railroad).*park',
            r'park.*(crosswalk|fire\s+hydrant|stop\s+sign|fire\s+station|railroad)',
            r'离.*(消防|人行|停车标志|停止信号|铁路).*停车',
            r'泊车应离',
        ],
    },
    'stopping_distance': {
        'zh': '制动距离',
        'en': 'Stopping Distance',
        'patterns': [
            r'stopping\s+distance',
            r'缓冲距离',
            r'完全停车',
            r'完全停止',
            r'miles\s+per\s+hour.*distance',
        ],
    },
    'gdl_stages': {
        'zh': 'GDL 阶段',
        'en': 'Graduated License',
        'patterns': [
            r'\bGDL\b',
            r'graduated\s+driver',
            r'special\s+learner.*permit',
            r'examination\s+permit',
            r'probationary',
            r'学员驾照',
            r'实习驾照',
            r'红牌|红色反光',
            r'(minimum\s+age|year[s]?\s+old).*license',
            r'minimum\s+age.*(driver|license)',
            r'最(小|低)\s*年龄',
        ],
    },
    'insurance': {
        'zh': '车辆保险',
        'en': 'Insurance',
        'patterns': [
            r'insurance',
            r'uninsured',
            r'保险',
            r'no.?fault',
        ],
    },
    'speed_points': {
        'zh': '超速 / 扣分',
        'en': 'Speed & Points',
        'patterns': [
            r'speed\s+limit',
            r'miles\s+per\s+hour\s+over',
            r'\b(?:points?|point\s+addition)\b',
            r'(tailgating|racing|reckless\s+driving)',
            r'(超速|限速|时速|罚款|增加.*分)',
            r'紧贴跟车',
            r'鲁莽驾驶',
        ],
    },
    'right_of_way': {
        'zh': '让行规则',
        'en': 'Right of Way',
        'patterns': [
            r'right.?of.?way',
            r'yield(\s|$)',
            r'让行|让路|让步',
            r'(intersection|crossroad).*(turn|go\s+first|yield)',
            r'两辆车.*同时.*路口',
        ],
    },
    'emergency_vehicle': {
        'zh': '紧急车辆 / 校车',
        'en': 'Emergency & School Buses',
        'patterns': [
            r'emergency\s+vehicle',
            r'(police|fire\s+truck|ambulance).*siren',
            r'school\s+bus',
            r'警车|消防车|救护车|校车|教会巴士',
        ],
    },
    'hand_signals': {
        'zh': '手势信号',
        'en': 'Hand Signals',
        'patterns': [
            r'hand\s+(and\s+arm\s+)?signal',
            r'手臂.*信号',
            r'手势',
        ],
    },
    'seat_belt': {
        'zh': '安全带 / 儿童座椅',
        'en': 'Seat Belt & Child Seat',
        'patterns': [
            r'seat\s+belt',
            r'child\s+(restraint|safety|seat)',
            r'(安全带|儿童保护|儿童座椅|小孩.*车座)',
        ],
    },
    'night_driving': {
        'zh': '夜间驾驶',
        'en': 'Night Driving',
        'patterns': [
            r'(headlight|high\s+beam|low\s+beam|night|dark)',
            r'(车灯|远光灯|近光灯|夜间|晚上开车)',
        ],
    },
    'license_admin': {
        'zh': '驾照 / 注册管理',
        'en': 'License & Registration',
        'patterns': [
            r'(register|registration|license\s+plate|vehicle\s+inspection|address|name\s+change)',
            r'(注册|车牌|地址|姓名|验车|车辆检查)',
            r'minimum\s+age.*(register|license)',
        ],
    },
    'skid_blowout': {
        'zh': '打滑 / 爆胎',
        'en': 'Skid & Blowout',
        'patterns': [
            r'(skid|blowout|tire\s+blow)',
            r'(打滑|爆胎)',
        ],
    },
    'turning_lanes': {
        'zh': '转向 / 车道',
        'en': 'Turning & Lanes',
        'patterns': [
            r'(turn\s+(left|right)|U-turn|merge|lane\s+change)',
            r'(转弯|左转|右转|并道|换道|车道)',
        ],
    },
    'curves_hills': {
        'zh': '弯道 / 坡道',
        'en': 'Curves & Hills',
        'patterns': [
            r'(curve|hill|downhill|uphill|grade)',
            r'(弯道|弯路|坡道|下坡|上坡)',
        ],
    },
}


def tag_question(stem):
    """Return list of topic keys matching this stem. May be empty (will be filled with 'general')."""
    tags = []
    for topic, info in TOPICS.items():
        for pat in info['patterns']:
            if re.search(pat, stem, re.I):
                tags.append(topic)
                break
    return tags if tags else ['general']


def main():
    with open(f'{BUILD}/parsed_full.json') as f:
        full = json.load(f)
    with open(f'{BUILD}/parsed_easy.json') as f:
        easy = json.load(f)

    full_tags = []
    easy_tags = []
    for q in full:
        full_tags.append(tag_question(q['stem']))
    for q in easy:
        easy_tags.append(tag_question(q['stem']))

    # Topic distribution
    from collections import Counter
    dist = Counter()
    for tags in full_tags:
        for t in tags:
            dist[t] += 1
    print('Topic distribution (full):', file=sys.stderr)
    for t, n in dist.most_common():
        print(f'  {t}: {n}', file=sys.stderr)

    # Save tag lists keyed by index
    out = {
        'topics_meta': {k: {'zh': v['zh'], 'en': v['en']} for k, v in TOPICS.items()},
        'general': {'zh': '综合', 'en': 'General'},
        'full_tags': full_tags,
        'easy_tags': easy_tags,
    }
    out['topics_meta']['general'] = {'zh': '综合', 'en': 'General'}
    with open(f'{BUILD}/topics.json', 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('Saved /tmp/nj_build/topics.json', file=sys.stderr)


if __name__ == '__main__':
    main()
