#!/usr/bin/env python3
"""Deterministic time-split baseline replay; not a test of LLM historical reasoning."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import argparse,hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'knowledge-base/scripts'))
from query import connect
ORIGINS=(2000,2005,2010,2015,2020)
SELECTED=(('wb:CHN','wb:SP.URB.TOTL.IN.ZS',2010),('wb:JPN','wb:SP.POP.TOTL',2010),('wb:BRA','wb:NY.GDP.PCAP.KD',2015))
def linear_forecast(training,origin,variable):
 assert len(training)==5 and [y for y,_ in training]==list(range(origin-4,origin+1))
 xs=[y-origin for y,_ in training];ys=[v for _,v in training]
 xm=sum(xs)/5;ym=sum(ys)/5
 slope=sum((x-xm)*(y-ym) for x,y in zip(xs,ys))/sum((x-xm)**2 for x in xs)
 pred=ym+slope*(5-xm)
 if variable in ('wb:SP.URB.TOTL.IN.ZS','wb:IT.NET.USER.ZS'):pred=min(100,max(0,pred))
 return pred

def replay():
 series=defaultdict(dict);names={};units={}
 with connect() as db:
  for row in db.execute("SELECT r.entity_id,e.name,r.start_year,o.variable_id,o.value_numeric,v.unit FROM observations o JOIN records r ON r.id=o.record_id JOIN entities e ON e.id=r.entity_id JOIN variables v ON v.id=o.variable_id WHERE e.kind='country_or_economy' AND o.variable_id LIKE 'wb:%'"):
   key=(row['entity_id'],row['variable_id']);year=row['start_year'];assert year not in series[key]
   series[key][year]=row['value_numeric'];names[key[0]]=row['name'];units[key[1]]=row['unit']
 forecasts=[];excluded=[]
 # Generate using prefix values only; attach outcomes in a separate pass.
 for (eid,var),values in sorted(series.items()):
  for origin in ORIGINS:
   train=[(y,values.get(y)) for y in range(origin-4,origin+1)]
   if any(v is None for _,v in train):excluded.append(dict(entity=eid,variable=var,origin=origin,reason='incomplete_training'));continue
   pred=linear_forecast(train,origin,var)
   forecasts.append(dict(entity=eid,name=names[eid],variable=var,origin=origin,target=origin+5,training=train,linear=pred,persistence=train[-1][1]))
 resolved=[]
 for row in forecasts:
  actual=series[(row['entity'],row['variable'])].get(row['target'])
  if actual is None:excluded.append(dict(entity=row['entity'],variable=row['variable'],origin=row['origin'],reason='missing_outcome'));continue
  row.update(actual=actual,linear_absolute_error=abs(row['linear']-actual),persistence_absolute_error=abs(row['persistence']-actual));resolved.append(row)
 metrics=[]
 for var in sorted(units):
  rows=[x for x in resolved if x['variable']==var];n=len(rows)
  metrics.append(dict(variable=var,unit=units[var],n=n,linear_mae=math.fsum(x['linear_absolute_error'] for x in rows)/n if n else None,persistence_mae=math.fsum(x['persistence_absolute_error'] for x in rows)/n if n else None,linear_wins=sum(x['linear_absolute_error']<x['persistence_absolute_error'] for x in rows),ties=sum(x['linear_absolute_error']==x['persistence_absolute_error'] for x in rows),linear_losses=sum(x['linear_absolute_error']>x['persistence_absolute_error'] for x in rows)))
 examples=[]
 for key in SELECTED:
  matches=[x for x in resolved if (x['entity'],x['variable'],x['origin'])==key]
  examples.extend(matches or [dict(entity=key[0],variable=key[1],origin=key[2],status='unavailable')])
 return dict(evaluation_type='historical_reconstruction_of_numeric_baselines',generated_at=datetime.now(timezone.utc).isoformat(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),database_bundle=json.loads((ROOT/'knowledge-base/data/bundle.json').read_text()),origins=ORIGINS,horizon_years=5,training_years=5,registered_tasks=len(series)*len(ORIGINS),resolved_tasks=len(resolved),excluded_tasks=len(excluded),metrics=metrics,selected=examples,exclusions=excluded,rows=resolved,limitations=['Uses later-revised values, not original historical data vintages.','No LLM or historical mechanism enhancement is scored.','No confidence intervals: countries, indicators and forecast origins are dependent.','Three display cases are fixed; full panel results and exclusions are retained.','Results do not establish precise prospective forecasting.'])
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 result=replay()
 with args.output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
 print(json.dumps({k:result[k] for k in ['registered_tasks','resolved_tasks','excluded_tasks','metrics','selected']},ensure_ascii=False,indent=2))
