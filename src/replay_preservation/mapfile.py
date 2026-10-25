"""ddrescue byte ranges; '+' means read, not independently verified authenticity."""
from collections import Counter

STATUSES = '?*/-+'
CURRENT_STATUSES = STATUSES + '%FG'


def parse_mapfile(text):
    ranges = []
    current_seen = False
    for number, line in enumerate(text.splitlines(), 1):
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        fields = line.split()
        # Header: current_pos current_status [current_pass].
        if len(fields) in (2, 3) and fields[1] in CURRENT_STATUSES:
            if current_seen or ranges:
                raise ValueError(f'Unexpected current-position line {number}')
            if int(fields[0], 0) < 0 or (len(fields) == 3 and int(fields[2], 0) < 1):
                raise ValueError(f'Invalid current-position line {number}')
            current_seen = True
            continue
        if len(fields) != 3 or fields[2] not in STATUSES:
            raise ValueError(f'Invalid mapfile line {number}')
        start, length = int(fields[0], 0), int(fields[1], 0)
        if start < 0 or length <= 0:
            raise ValueError(f'Invalid range on line {number}')
        if ranges and start < ranges[-1]['offset'] + ranges[-1]['length']:
            raise ValueError(f'Overlapping or unordered range on line {number}')
        ranges.append({'offset': start, 'length': length, 'status': fields[2]})
    if not ranges:
        raise ValueError('Mapfile has no data ranges')
    return ranges


def summarize(ranges):
    totals = Counter()
    gaps = []
    end = 0
    for item in ranges:
        if item['offset'] > end:
            gaps.append({'offset': end, 'length': item['offset']-end})
        totals[item['status']] += item['length']
        end = item['offset'] + item['length']
    return {'bytes_by_status': dict(totals), 'read_bytes': totals['+'],
            'unrecovered_bytes': sum(v for k,v in totals.items() if k != '+'),
            'unmapped_ranges': gaps, 'covered_end': end,
            'completion': 'unknown_without_expected_source_size',
            'integrity': 'reading_success_is_not_independent_integrity_verification'}


def affected_extents(ranges, offset, length):
    return [dict(item, overlap_start=max(offset, item['offset']),
                 overlap_length=min(offset+length, item['offset']+item['length'])-max(offset,item['offset']))
            for item in ranges if item['status'] != '+' and
            max(offset,item['offset']) < min(offset+length,item['offset']+item['length'])]
