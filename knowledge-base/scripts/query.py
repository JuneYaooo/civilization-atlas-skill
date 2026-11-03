#!/usr/bin/env python3
"""Read-only retrieval with source locators. No inference or historical gap filling."""
from pathlib import Path
import argparse,json,sqlite3
from runtime import database_path
ROOT=Path(__file__).resolve().parents[1]
def connect():
 db=sqlite3.connect(database_path().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;return db

def search(q='',source='',topic='',entity='',start=None,end=None,limit=30,offset=0):
 limit=max(1,min(int(limit),100));offset=max(0,int(offset));parts=[];values=[]
 if start is not None and end is not None and int(start)>int(end):raise ValueError('Start year must not exceed end year')
 for token in q.split():
  escaped=token.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
  parts.append("(r.search_text LIKE ? ESCAPE '\\' OR e.name LIKE ? ESCAPE '\\')");values.extend(['%'+escaped+'%']*2)
 for col,val in [('r.source_id',source),('r.topic',topic)]:
  if val:parts.append(col+'=?');values.append(val)
 if entity:
  parts.append('(r.entity_id=? OR EXISTS (SELECT 1 FROM relations rel WHERE rel.record_id=r.id AND (rel.subject_id=? OR rel.object_id=?)))');values.extend([entity]*3)
 # Undated assertions do not acquire dates from their polity; censored ends are source-limited.
 if start is not None:
  parts.append("(r.end_year>=? OR (r.end_year IS NULL AND r.source_id='cow-alliances' AND r.start_year IS NOT NULL AND 2012>=?))");values.extend([int(start)]*2)
 if end is not None:parts.append('r.start_year<=?');values.append(int(end))
 where=' WHERE '+' AND '.join(parts) if parts else ''
 joins=' FROM records r LEFT JOIN entities e ON e.id=r.entity_id JOIN sources s ON s.id=r.source_id'
 with connect() as db:
  total=db.execute('SELECT COUNT(*)'+joins+where,values).fetchone()[0]
  rows=db.execute('SELECT r.id,r.title,r.entity_id,e.name AS entity_name,r.collection,r.topic,r.start_year,r.end_year,r.review_status,r.source_id,s.title AS source_title,s.url AS source_url,r.locator,r.time_semantics'+joins+where+' ORDER BY r.start_year IS NULL,r.start_year,r.id LIMIT ? OFFSET ?',values+[limit,offset]).fetchall()
 return dict(total=total,limit=limit,offset=offset,records=[dict(row) for row in rows],temporal_note='Undated assertions excluded by date filters; dated records are source claims, not a complete timeline')

def detail(rid):
 with connect() as db:
  row=db.execute('SELECT r.*,s.url AS source_url,s.sha256 AS source_sha256,s.retrieved_at,s.path AS source_path FROM records r JOIN sources s ON s.id=r.source_id WHERE r.id=?',(rid,)).fetchone()
  if row is None:raise ValueError('Record not found')
  result=dict(row);result.pop('search_text');result['payload']=json.loads(result.pop('payload_json'))
  result['observations']=[dict(x) for x in db.execute('SELECT * FROM observations WHERE record_id=?',(rid,))]
  result['relations']=[dict(x) for x in db.execute('SELECT * FROM relations WHERE record_id=?',(rid,))]
  if result['source_id']=='legacy-events':
   src=db.execute("SELECT path FROM sources WHERE id='legacy-sources'").fetchone()
   refs={x['id']:x for x in json.loads((ROOT/src['path']).read_text())}
   result['original_references']=[refs[x['source_id']] for x in result['payload'].get('citations',[]) if x['source_id'] in refs]
 return result

def entities(q='',limit=50):
 with connect() as db:return [dict(x) for x in db.execute('SELECT id,name,kind,region FROM entities WHERE name LIKE ? OR id LIKE ? ORDER BY name LIMIT ?',('%'+q+'%','%'+q+'%',min(200,max(1,int(limit)))))]

INDICATOR_HELP='Indicator code such as SP.DYN.TFRT.IN; run "indicators" to list them'

def indicators():
 """List numeric country-year series with their year span and vintage note."""
 with connect() as db:
  rows=db.execute("SELECT r.source_id,s.title,MIN(r.start_year) AS first,MAX(r.start_year) AS last,COUNT(DISTINCT r.entity_id) AS entities FROM records r JOIN sources s ON s.id=r.source_id WHERE r.collection IN ('country_year_indicator','historical_indicator_mirror') GROUP BY r.source_id ORDER BY r.source_id").fetchall()
 out=[]
 for r in rows:
  code=r['source_id'].split('-',2)[-1] if r['source_id'].startswith('wdi-mirror-') else r['source_id'][3:]
  out.append(dict(indicator=code,source_id=r['source_id'],title=r['title'],first_year=r['first'],last_year=r['last'],entities=r['entities'],vintage='historical mirror, observations end %s; not current data'%r['last'] if r['source_id'].startswith('wdi-mirror-') else 'World Bank API snapshot; check latest values online for current questions'))
 return out

def _resolve_entity(db,token):
 token=token.strip()
 if ':' in token:
  row=db.execute('SELECT id,name FROM entities WHERE id=?',(token,)).fetchone()
 else:
  row=db.execute("SELECT id,name FROM entities WHERE id=? OR lower(name)=lower(?) ORDER BY kind!='country_or_economy' LIMIT 1",('wb:'+token.upper(),token)).fetchone()
  if row is None:
   rows=db.execute("SELECT id,name FROM entities WHERE kind='country_or_economy' AND name LIKE ? ORDER BY length(name) LIMIT 5",('%'+token+'%',)).fetchall()
   if len(rows)>1:raise ValueError('Ambiguous entity %r: %s'%(token,', '.join(r['id']+' '+r['name'] for r in rows)))
   row=rows[0] if rows else None
 if row is None:raise ValueError('Unknown entity %r; use "entities --q" to look it up'%token)
 return row['id'],row['name']

def series(indicator,entity,start=None,end=None,years='',nearest=None):
 """Return year-value tables for one indicator and several countries, keeping record locators."""
 wanted={int(y) for y in years.split(',') if y.strip()} if years else None
 with connect() as db:
  srcs=[r['id'] for r in db.execute('SELECT id FROM sources WHERE id IN (?,?)',('wb-'+indicator,'wdi-mirror-'+indicator))]
  if not srcs:raise ValueError('No numeric series for %s; run "indicators"'%indicator)
  result=dict(indicator=indicator,series=[],note='Values are source assertions with locators, not independently verified. Mirror series are historical vintages and cannot stand in for current data.')
  for token in [x for x in entity.split(',') if x.strip()]:
   eid,name=_resolve_entity(db,token)
   for src in srcs:
    q='SELECT r.id,r.start_year,r.locator,o.value_numeric,o.status FROM records r JOIN observations o ON o.record_id=r.id WHERE r.source_id=? AND r.entity_id=?'
    args=[src,eid]
    if start is not None:q+=' AND r.start_year>=?';args.append(int(start))
    if end is not None:q+=' AND r.start_year<=?';args.append(int(end))
    rows=[dict(year=r['start_year'],value=r['value_numeric'],record_id=r['id'],locator=r['locator']) for r in db.execute(q+' ORDER BY r.start_year',args) if r['value_numeric'] is not None]
    if not rows:continue
    s=db.execute('SELECT title,url,retrieved_at FROM sources WHERE id=?',(src,)).fetchone()
    entry=dict(entity_id=eid,entity_name=name,source_id=src,source_title=s['title'],source_url=s['url'],retrieved_at=s['retrieved_at'],first_year=rows[0]['year'],last_year=rows[-1]['year'])
    if nearest is not None:
     best=min(rows,key=lambda r:abs(r['value']-float(nearest)));entry['nearest']=dict(target=float(nearest),**best)
    entry['values']=[r for r in rows if wanted is None or r['year'] in wanted]
    result['series'].append(entry)
 return result

def series_table(result):
 lines=['indicator %s'%result['indicator']]
 for s in result['series']:
  lines.append('\n%s (%s) · %s · %s–%s · %s'%(s['entity_name'],s['entity_id'],s['source_id'],s['first_year'],s['last_year'],s['source_url']))
  for r in s['values']:
   cur='' if 'current' not in r else ('\tcurrent=%s'%('missing' if r['current'] is None else round(r['current'],3)))
   lines.append('  %s\t%s%s\t%s'%(r['year'],round(r['value'],3),cur,r['locator']))
  if s.get('years_differing'):lines.append('  vintage differs (>0.5) in shown years: %s'%', '.join(map(str,s['years_differing'])))
  if s.get('current_after_mirror'):
   tail=list(s['current_after_mirror'].items())[-3:];lines.append('  current vintage after mirror end: %s'%', '.join('%s=%s'%(y,round(v,3)) for y,v in tail))
  if 'nearest' in s:n=s['nearest'];lines.append('  nearest to %s: %s (%s) %s'%(n['target'],n['year'],round(n['value'],3),n['locator']))
 cv=result.get('current_vintage')
 if cv:lines.append('\ncurrent vintage: '+(cv.get('error','') and 'UNAVAILABLE '+cv['error'] or '%s (last updated %s)'%(cv['url'],cv['last_updated'])))
 lines.append('\n'+result['note'])
 return '\n'.join(lines)

def current_wdi(indicator,entity_ids,start=None,end=None,timeout=30):
 """Fetch the live World Bank API vintage for comparison. Needs network; failures are reported, not hidden."""
 import urllib.request
 codes=';'.join(e.split(':',1)[1] for e in entity_ids if e.startswith('wb:'))
 url='https://api.worldbank.org/v2/country/%s/indicator/%s?format=json&per_page=20000'%(codes,indicator)
 if start is not None or end is not None:url+='&date=%s:%s'%(start or 1960,end or 2100)
 try:
  with urllib.request.urlopen(url,timeout=timeout) as r:data=json.loads(r.read().decode())
 except Exception as exc:return dict(url=url,error=str(exc))
 if not isinstance(data,list) or len(data)<2 or data[1] is None:return dict(url=url,error='no data returned',raw=data[0] if data else None)
 out={}
 for row in data[1]:
  if row.get('value') is None:continue
  out.setdefault('wb:'+row['countryiso3code'],{})[int(row['date'])]=row['value']
 return dict(url=url,last_updated=data[0].get('lastupdated'),values=out)

def compare(result,current,threshold=0.5):
 """Attach current-vintage values and flag years where the vintages differ."""
 if 'error' in current:result['current_vintage']=current;return result
 result['current_vintage']=dict(url=current['url'],last_updated=current['last_updated'])
 for s in result['series']:
  cur=current['values'].get(s['entity_id'],{})
  diffs=[]
  for r in s['values']:
   c=cur.get(r['year']);r['current']=c
   if c is None:r['current_status']='missing_in_current'
   elif abs(c-r['value'])>threshold:diffs.append(r['year'])
  s['years_differing']=diffs
  later=sorted(y for y in cur if y>s['last_year'])
  if later:s['current_after_mirror']={str(y):cur[y] for y in later}
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
 x=sub.add_parser('search');x.add_argument('--q',default='');x.add_argument('--source',default='');x.add_argument('--topic',default='');x.add_argument('--entity',default='');x.add_argument('--start',type=int);x.add_argument('--end',type=int);x.add_argument('--limit',type=int,default=30);x.add_argument('--offset',type=int,default=0)
 x=sub.add_parser('record');x.add_argument('id')
 x=sub.add_parser('entities');x.add_argument('--q',default='');x.add_argument('--limit',type=int,default=50)
 sub.add_parser('coverage')
 sub.add_parser('indicators',help='List numeric country-year indicators and their year spans')
 x=sub.add_parser('series',help='Year-value table for one indicator across countries, with locators')
 x.add_argument('--indicator',required=True,help=INDICATOR_HELP);x.add_argument('--entity',required=True,help='Comma-separated ISO3 codes, wb: ids or country names, e.g. JPN,KOR,CHN')
 x.add_argument('--start',type=int);x.add_argument('--end',type=int);x.add_argument('--years',default='',help='Only show these years, e.g. 1990,2000,2016')
 x.add_argument('--nearest',type=float,help='Also report the year whose value is closest to this number')
 x.add_argument('--compare-current',action='store_true',help='Fetch the live World Bank API (needs network) and flag vintage differences')
 x.add_argument('--format',choices=['table','json'],default='table')
 a=vars(p.parse_args());cmd=a.pop('cmd')
 if cmd=='search':result=search(**a)
 elif cmd=='record':result=detail(a['id'])
 elif cmd=='entities':result=entities(**a)
 elif cmd=='indicators':result=indicators()
 elif cmd=='series':
  fmt=a.pop('format');cmp=a.pop('compare_current')
  result=series(**a)
  if cmp:result=compare(result,current_wdi(a['indicator'],[x['entity_id'] for x in result['series']],a.get('start'),a.get('end')))
  if fmt=='table':print(series_table(result));return
 else:result=json.loads((ROOT/'reports/coverage.json').read_text())
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
