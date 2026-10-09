#!/usr/bin/env python3
"""Acquire explicitly identified historical WDI mirrors; not a current-data refresh."""
from acquire import fetch, ROOT
from concurrent.futures import ThreadPoolExecutor
import csv, io, json


def main():
    indicators=json.loads((ROOT/'data/extended-indicators.json').read_text())
    tasks=[]
    for item in indicators:
        code=item['code'];base='https://datahub.io/world-development-indicators/'+code.lower()
        for suffix,ext in [('data.csv','csv'),('datapackage.json','json')]:
            sid='wdi-mirror-'+code+('-meta' if ext=='json' else '')
            tasks.append((sid,base+'/_r/-/'+suffix,ext,'Historical WDI mirror · '+item['label']+(' metadata' if ext=='json' else ''),base,'Historical DataHub mirror; observation years validated from file','CC BY 4.0 as stated by DataHub and World Bank indicator page; attribute World Bank, upstream agencies and DataHub'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(fetch,tasks))
    for source in results:
        if source['status']=='acquired' and source['path'].endswith('.csv'):
            rows=list(csv.DictReader(io.StringIO((ROOT/source['path']).read_text())))
            if not rows or set(rows[0])!={'Country Name','Country Code','Year','Value'}:
                raise ValueError('Unexpected mirror CSV schema: '+source['id'])
            years=[int(x['Year']) for x in rows]
            source.update(observation_start=min(years),observation_end=max(years),row_count=len(rows),review_status='mirror_schema_checked_not_independently_verified',first_public_at=None)
    failures=[r for r in results if r['status']!='acquired']
    if failures:
        raise RuntimeError(json.dumps([{k:r.get(k) for k in ('id','error')} for r in failures]))
    (ROOT/'data/extended-manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:r.get(k) for k in ('id','status','row_count','observation_start','observation_end')} for r in results],ensure_ascii=False))

if __name__=='__main__':main()
