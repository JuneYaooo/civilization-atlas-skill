#!/usr/bin/env python3
"""Known-outcome arithmetic dry run, not a future task settlement or forecast."""
import json
from pathlib import Path


def share_rise(old_bev, old_total, new_bev, new_total):
    """Compare exact counts; missing or invalid observations must never become 0."""
    for bev, total in ((old_bev, old_total), (new_bev, new_total)):
        if type(bev) is not int or type(total) is not int:
            raise ValueError('Counts must be integers, not missing values or booleans')
        if not 0 <= bev <= total or total <= 0:
            raise ValueError('Require 0 <= BEV <= TOTAL and TOTAL > 0')
    return int(new_bev * old_total > old_bev * new_total)


def run(data):
    if (data['mode'] != 'known_outcome_resolution_dry_run'
            or data['scope'] != 'new_passenger_car_registrations_BEV'
            or data['period'] != 'Jan-Mar'):
        raise ValueError('Wrong experiment, population or period')
    rows = []
    seen = set()
    for row in data['rows']:
        if row['country'] in seen:
            raise ValueError('Duplicate market')
        seen.add(row['country'])
        if (row['old_year'], row['new_year']) != (2025, 2026):
            raise ValueError('This dry run only accepts 2025/2026 observations')
        old, ot, new, nt = (row[k] for k in
                            ('old_bev', 'old_total', 'new_bev', 'new_total'))
        direction = share_rise(old, ot, new, nt)
        rows.append(dict(country=row['country'], share2025=round(100*old/ot, 4),
                         share2026=round(100*new/nt, 4), share_rise=direction,
                         share_change_pp=round(100*(new/nt-old/ot), 4),
                         volume_change=new-old))
    return dict(mode=data['mode'], skill_accuracy=None, future_settlements=0,
                rows=rows)


if __name__ == '__main__':
    path = Path(__file__).with_name('quarterly-input.json')
    print(json.dumps(run(json.loads(path.read_text())), ensure_ascii=False, indent=2))
