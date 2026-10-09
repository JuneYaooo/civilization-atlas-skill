#!/usr/bin/env python3
"""Descriptive arithmetic; never a Skill forecast score."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent
a=json.loads((p/'historical.json').read_text())
rows=[]
for x in a['rows']:
    old=100*x['bev2023']/x['total2023'];new=100*x['bev2024']/x['total2024']
    rows.append(dict(country=x['country'],share2023=round(old,4),share2024=round(new,4),share_change_pp=round(new-old,4),bev_volume_change_percent=round(100*(x['bev2024']/x['bev2023']-1),4)))
f=a['uk_external_forecast']
print(json.dumps(dict(mode=a['mode'],skill_accuracy=None,rows=rows,uk_external_forecast_error_pp=round(f['forecast_share_percent']-f['observed_share_percent'],4)),ensure_ascii=False,indent=2))
