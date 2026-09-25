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

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
 x=sub.add_parser('search');x.add_argument('--q',default='');x.add_argument('--source',default='');x.add_argument('--topic',default='');x.add_argument('--entity',default='');x.add_argument('--start',type=int);x.add_argument('--end',type=int);x.add_argument('--limit',type=int,default=30);x.add_argument('--offset',type=int,default=0)
 x=sub.add_parser('record');x.add_argument('id')
 x=sub.add_parser('entities');x.add_argument('--q',default='');x.add_argument('--limit',type=int,default=50)
 sub.add_parser('coverage')
 a=vars(p.parse_args());cmd=a.pop('cmd')
 if cmd=='search':result=search(**a)
 elif cmd=='record':result=detail(a['id'])
 elif cmd=='entities':result=entities(**a)
 else:result=json.loads((ROOT/'reports/coverage.json').read_text())
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
