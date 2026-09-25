#!/usr/bin/env python3
"""Build a provenance-preserving, queryable historical knowledge base from local snapshots."""
from pathlib import Path
from datetime import datetime,timezone
import csv,io,json,sqlite3,hashlib,zipfile,os
from collections import Counter
from xlsx_reader import sheets
ROOT=Path(__file__).resolve().parents[1]
def dumps(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,allow_nan=False)
def integer(v):
 try:
  n=float(v)
  return int(n) if n.is_integer() else None
 except (ValueError,TypeError):return None

def main():
 manifests=[]
 for name in ['manifest.json','modern-manifest.json','legacy-manifest.json','climate-manifest.json']:
  p=ROOT/'data'/name
  if p.exists():manifests.extend(json.loads(p.read_text()))
 sources={s['id']:s for s in manifests if s['status']=='acquired'}
 for s in sources.values():
  assert hashlib.sha256((ROOT/s['path']).read_bytes()).hexdigest()==s['sha256'],s['id']
 tmp=ROOT/'data/history.building.sqlite'
 if tmp.exists():tmp.unlink()
 db=sqlite3.connect(tmp);db.executescript('''
 PRAGMA foreign_keys=ON;
 CREATE TABLE sources(id TEXT PRIMARY KEY,title TEXT,url TEXT,retrieved_at TEXT,sha256 TEXT,path TEXT,metadata_json TEXT NOT NULL);
 CREATE TABLE entities(id TEXT PRIMARY KEY,name TEXT NOT NULL,kind TEXT NOT NULL,region TEXT,source_id TEXT REFERENCES sources(id),metadata_json TEXT NOT NULL);
 CREATE TABLE records(id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES sources(id),collection TEXT NOT NULL,locator TEXT NOT NULL,title TEXT NOT NULL,entity_id TEXT REFERENCES entities(id),start_year INTEGER,end_year INTEGER,time_semantics TEXT NOT NULL,topic TEXT NOT NULL,review_status TEXT NOT NULL,payload_json TEXT NOT NULL,search_text TEXT NOT NULL);
 CREATE TABLE observations(id TEXT PRIMARY KEY,record_id TEXT NOT NULL REFERENCES records(id),variable_id TEXT NOT NULL,value_json TEXT,value_numeric REAL,status TEXT NOT NULL);
 CREATE TABLE variables(id TEXT PRIMARY KEY,label TEXT,unit TEXT,metadata_json TEXT);
 CREATE TABLE relations(id TEXT PRIMARY KEY,record_id TEXT REFERENCES records(id),subject_id TEXT REFERENCES entities(id),predicate TEXT,object_id TEXT REFERENCES entities(id),start_year INTEGER,end_year INTEGER,metadata_json TEXT);
 CREATE INDEX record_time ON records(start_year,end_year);
 CREATE INDEX record_source ON records(source_id);
 CREATE INDEX record_entity ON records(entity_id);
 CREATE INDEX record_topic ON records(topic);
 CREATE INDEX observation_variable ON observations(variable_id);
 CREATE INDEX relation_subject ON relations(subject_id);
 CREATE INDEX relation_object ON relations(object_id);
 ''')
 for s in sources.values():db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?)',(s['id'],s['title'],s.get('landing_url',s['url']),s['retrieved_at'],s['sha256'],s['path'],dumps(s)))
 def entity(eid,name,kind,source,region=None,meta=None):
  db.execute('INSERT OR IGNORE INTO entities VALUES (?,?,?,?,?,?)',(eid,name,kind,region,source,dumps(meta or {})));return eid
 def record(sid,coll,loc,title,payload,eid=None,start=None,end=None,topic='unclassified',semantics='source_years; no annual expansion',status='imported_source_assertion'):
  rid=sid+':'+hashlib.sha256((coll+'|'+loc).encode()).hexdigest()[:20]
  text=' '.join([title,eid or '',topic,dumps(payload)])
  db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,sid,coll,loc,title,eid,start,end,semantics,topic,status,dumps(payload),text));return rid
 def variable(vid,label,unit='',meta=None):db.execute('INSERT OR IGNORE INTO variables VALUES (?,?,?,?)',(vid,label,unit,dumps(meta or {})))
 def observation(rid,vid,value,numeric=None,status='source_value'):
  db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?)',(rid+'|'+vid,rid,vid,dumps(value),numeric,status))
 def relation(rid,subject,predicate,obj,start,end,meta):
  db.execute('INSERT INTO relations VALUES (?,?,?,?,?,?,?,?)',(rid+'|'+predicate+'|'+subject+'|'+obj,rid,subject,predicate,obj,start,end,dumps(meta)))
 def json_source(sid):return json.loads((ROOT/sources[sid]['path']).read_text())
 def csv_source(sid,contains=None):
  path=ROOT/sources[sid]['path']
  if path.suffix=='.zip':
   with zipfile.ZipFile(path) as z:
    names=[n for n in z.namelist() if '__MACOSX' not in n and n.lower().endswith('.csv') and contains.lower() in n.lower()]
    assert len(names)==1,(sid,names)
    name=names[0];data=z.read(name)
  else:name=path.name;data=path.read_bytes()
  try:text=data.decode('utf-8-sig')
  except UnicodeDecodeError:text=data.decode('cp1252')
  rows=list(csv.DictReader(io.StringIO(text, newline="")))
  for i,row in enumerate(rows,2):
   assert None not in row,(sid,i,'malformed csv')
   yield name+':row='+str(i),row
 # Country metadata is contemporary; historical identifiers deliberately remain separate.
 wb_codes={}
 if 'wb-countries' in sources:
  data=json_source('wb-countries');assert data[0]['pages']==1 and len(data[1])==data[0]['total']
  for row in data[1]:
   assert row['iso2Code'] not in wb_codes
   wb_codes[row['iso2Code']]=row['id']
   entity('wb:'+row['id'],row['name'],'aggregate' if row['region']['value']=='Aggregates' else 'country_or_economy','wb-countries',row['region']['value'],row)
 topics={'SP.POP.TOTL':('demography','人口总量','persons'),'NY.GDP.PCAP.KD':('economy','人均 GDP','constant 2015 US$'),'SP.DYN.LE00.IN':('health','预期寿命','years'),'SP.URB.TOTL.IN.ZS':('urbanization','城市人口占比','percent'),'IT.NET.USER.ZS':('technology','互联网使用人口占比','percent')}
 for code,(topic,label,unit) in topics.items():
  sid='wb-'+code
  if sid not in sources:continue
  data=json_source(sid);assert data[0]['pages']==1 and len(data[1])==data[0]['total'],sid
  meta=json_source('wb-meta-'+code) if 'wb-meta-'+code in sources else {}
  variable('wb:'+code,label,unit,meta)
  seen=set()
  for i,row in enumerate(data[1]):
   assert row['indicator']['id']==code
   country=row['countryiso3code'] or wb_codes[row['country']['id']];eid='wb:'+country
   assert db.execute('SELECT 1 FROM entities WHERE id=?',(eid,)).fetchone(),eid
   year=int(row['date']);key=(eid,year);assert key not in seen;seen.add(key)
   rid=record(sid,'country_year_indicator','json[1]['+str(i)+']',row['country']['value']+' · '+label,row,eid,year,year,topic,'CE calendar year; source snapshot, revisions possible')
   value=row['value'];observation(rid,'wb:'+code,value,value,'missing' if value is None else 'source_value')
 if 'cow-states' in sources:
  for loc,row in csv_source('cow-states','statelist2024.csv'):
   eid=entity('cow:'+row['ccode'],row['statenme'],'state_system_member','cow-states')
   record('cow-states','state_membership',loc,row['statenme'],row,eid,int(row['styear']),int(row['endyear']),'institutions','COW membership spell; ending at dataset limit can be censored, not dissolution')
 if 'cow-alliances' in sources:
  for loc,row in csv_source('cow-alliances','alliance_v4.1_by_member.csv'):
   eid=entity('cow:'+row['ccode'],row['state_name'],'state_system_member','cow-alliances')
   aid=entity('cow-alliance:'+row['version4id'],'COW alliance '+row['version4id'],'alliance','cow-alliances')
   start=integer(row['mem_st_year']);end=integer(row['mem_end_year'])
   rid=record('cow-alliances','alliance_membership',loc,row['state_name']+' · '+aid,row,eid,start,end,'diplomacy','Membership spell; empty end is censored at source horizon 2012, not proof of current membership')
   relation(rid,eid,'alliance_member',aid,start,end,row)
 if 'cow-interstate' in sources:
  for loc,row in csv_source('cow-interstate'):
   eid=entity('cow:'+row['ccode'],row['StateName'],'state_system_member','cow-interstate')
   wid=entity('cow-interwar:'+row['WarNum'],row['WarName'],'war','cow-interstate')
   starts=[integer(row[k]) for k in ['StartYear1','StartYear2'] if integer(row[k]) is not None and integer(row[k])>0]
   ends=[integer(row[k]) for k in ['EndYear1','EndYear2'] if integer(row[k]) is not None and integer(row[k])>0]
   rid=record('cow-interstate','war_participation',loc,row['WarName']+' · '+row['StateName'],row,eid,min(starts) if starts else None,max(ends) if ends else None,'war','Outer participation bounds; interruptions and unknown date codes retained in payload')
   relation(rid,eid,'war_participant',wid,min(starts) if starts else None,max(ends) if ends else None,row)
 if 'cow-intrastate' in sources:
  for loc,row in csv_source('cow-intrastate','INTRA-STATE WARS v5.1 CSV.csv'):
   wid=entity('cow-intrawar:'+row['WarNum'],row['WarName'],'war','cow-intrastate')
   start=integer(row['StartYr1']);ends=[integer(row['EndYr'+str(i)]) for i in range(1,5) if integer(row['EndYr'+str(i)]) is not None and integer(row['EndYr'+str(i)])>0]
   record('cow-intrastate','war',loc,row['WarName'],row,wid,start,max(ends) if ends else None,'war','Outer episode bounds; multiple spells and unknown date codes retained in payload')
 if 'nasa-gistemp' in sources:
  sid='nasa-gistemp';eid=entity('nasa:global','Global land-ocean mean','global_aggregate',sid)
  data=(ROOT/sources[sid]['path']).read_text().splitlines()
  assert data[1].startswith('Year,')
  variable('nasa:J-D','Global annual temperature anomaly','degrees C relative to 1951-1980',{'citation':'GISTEMP Team 2026; Lenssen et al. 2024 doi:10.1029/2023JD040179'})
  for i,row in enumerate(csv.DictReader(data[1:]),3):
   year=int(row['Year']);value=row['J-D']
   rid=record(sid,'global_temperature',f'csv:row={i}','全球地表年均温度距平',row,eid,year,year,'climate','Annual J-D anomaly relative to 1951-1980; monthly and seasonal values retained in payload; incomplete annual value remains missing')
   try:number=float(value)
   except ValueError:number=None
   observation(rid,'nasa:J-D',value,number,'missing' if number is None else 'source_value')
 # Legacy curation is preserved as inherited claims, not upgraded to newly verified facts.
 if 'legacy-events' in sources:
  old=json_source('legacy-events');entity_data=json_source('legacy-entities')
  for row in entity_data['entities']:entity('legacy:'+row['id'],row['name'],row['type'],'legacy-entities',meta=row)
  for i,row in enumerate(old):
   event_id=entity('legacy-event:'+row['id'],row['title'],'historical_event','legacy-events')
   actors=row.get('actors',[]);eid='legacy:'+actors[0]['entity_id'] if actors else None
   rid=record('legacy-events','curated_event',f'json[{i}]',row['title'],row,eid,row['date']['start'],row['date']['end'],';'.join(row['categories']),'Historical signed years, no year zero; '+row['date']['kind'],status='inherited_review_not_reverified')
   for actor in actors:
    aid='legacy:'+actor['entity_id']
    if db.execute('SELECT 1 FROM entities WHERE id=?',(aid,)).fetchone():relation(rid,aid,'event_actor',event_id,row['date']['start'],row['date']['end'],actor)
 # Seshat preserves uncertain/disputed codes and value bounds without averaging.
 if 'seshat-polaris' in sources:
  workbook=list(sheets(ROOT/sources['seshat-polaris']['path']))
  def table(rows):
   headers=rows[0][1]
   assert len(headers)==len(set(headers))
   for rownum,vals in rows[1:]:
    if any(v!='' for v in vals):yield rownum,{str(h or 'column_'+str(i)):vals[i] if i<len(vals) else '' for i,h in enumerate(headers)}
  polity_sheet=next(rows for name,rows in workbook if name=='Polities')
  for _,row in table(polity_sheet):
   entity('seshat:'+row['polity_id'],row['long_name'],'historical_polity','seshat-polaris',row['seshat_region'],row)
  for sheet,rows in workbook:
   if not rows:continue
   for rownum,payload in table(rows):
    eid='seshat:'+payload['polity_id'] if payload.get('polity_id') else None
    if eid:assert db.execute('SELECT 1 FROM entities WHERE id=?',(eid,)).fetchone(),eid
    var=payload.get('variable_name')
    if sheet=='Variables':
     variable('seshat:'+var,var,'source-defined; see codebook',payload)
    start=integer(payload.get('start_year',payload.get('year_from')))
    end=integer(payload.get('end_year',payload.get('year_to')))
    title=payload.get('long_name') or var or sheet
    topic={'General':'institutions','Social complexity':'social_complexity','Warfare':'military_technology','Luxury goods':'economy','Religion':'religion','CrisisDB - Crisis consequences':'crisis','Polities':'historical_geography','Variables':'metadata'}[sheet]
    rid=record('seshat-polaris',sheet,f'{sheet}!row={rownum}',title,payload,eid,start,end,topic,'Source signed year fields; blanks remain undated, polity span is not copied to assertions; BCE year-zero convention not independently verified')
    if sheet not in ('Variables','Polities') and var:
     variable('seshat:'+var,var,'source-defined; see codebook')
     if sheet.startswith('CrisisDB'):
      observation(rid,'seshat:'+var,payload,None,'source_categorical_bundle')
     else:
      lo,hi=payload.get('value_from',''),payload.get('value_to','')
      flags={k:payload.get(k) for k in ['is_disputed','is_uncertain']}
      status='missing' if lo==hi=='' else 'source_code_or_value'
      if flags['is_disputed']=='1':status='disputed'
      elif flags['is_uncertain']=='1':status='uncertain'
      observation(rid,'seshat:'+var,dict(value_from=lo,value_to=hi,**flags),None,status)
 db.commit()
 counts={t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['sources','entities','records','observations','relations','variables']}
 per_source=[dict(zip(['source_id','collection','rows','start','end'],r)) for r in db.execute('SELECT source_id,collection,count(*),min(start_year),max(end_year) FROM records GROUP BY source_id,collection ORDER BY source_id,collection')]
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 assert not db.execute('PRAGMA foreign_key_check').fetchall()
 db.close();os.replace(tmp,ROOT/'data/history.sqlite')
 report={'built_at':datetime.now(timezone.utc).isoformat(),'counts':counts,'collections':per_source,'scope':'Imported source claims; counts do not establish historical completeness','source_failures':[s for s in manifests if s['status']!='acquired']}
 (ROOT/'reports/coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
