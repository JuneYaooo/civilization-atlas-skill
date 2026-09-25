#!/usr/bin/env python3
"""Acquire explicitly catalogued public sources with immutable content hashes."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, urllib.request
ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
 ('seshat-polaris','https://raw.githubusercontent.com/Seshat-Global-History-Databank/build_polaris_dataset/main/Polaris2026.xlsx','xlsx','Seshat Polaris 2026','https://seshatdatabank.info/data','2026','see upstream license'),
 ('seshat-readme','https://raw.githubusercontent.com/Seshat-Global-History-Databank/build_polaris_dataset/main/README.md','md','Seshat snapshot documentation','https://seshatdatabank.info/data','retrieved snapshot','see upstream license'),
 ('seshat-license','https://raw.githubusercontent.com/Seshat-Global-History-Databank/build_polaris_dataset/main/LICENSE','txt','Seshat repository license','https://seshatdatabank.info/data','retrieved snapshot','license text'),
 ('cow-states','https://correlatesofwar.org/wp-content/uploads/States2024.zip','zip','COW state system membership','https://correlatesofwar.org/data-sets/state-system-membership/','2024','redistribution not assessed; attribution required'),
 ('cow-alliances','https://correlatesofwar.org/wp-content/uploads/version4.1_csv.zip','zip','COW formal alliances','https://correlatesofwar.org/data-sets/formal-alliances/','4.1','redistribution not assessed; attribution required'),
 ('cow-interstate','https://correlatesofwar.org/wp-content/uploads/Inter-StateWarData_v4.0.csv','csv','COW interstate war participants','https://correlatesofwar.org/data-sets/COW-war/','4.0','redistribution not assessed; attribution required'),
 ('cow-intrastate','https://correlatesofwar.org/wp-content/uploads/Intra-State-Wars-v5.1.zip','zip','COW intrastate wars','https://correlatesofwar.org/data-sets/COW-war/','5.1','redistribution not assessed; attribution required'),
]
SOURCES=[item for item in SOURCES if not item[0].startswith("cow-")]

def fetch(item):
 sid,url,ext,title,landing,version,rights=item
 result=dict(id=sid,title=title,url=url,landing_url=landing,version=version,rights=rights,first_public_at=None,retrieved_at=datetime.now(timezone.utc).isoformat())
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'HistoricalKnowledgeBase/0.1 research'})
  with urllib.request.urlopen(req,timeout=50) as f:
   data=f.read();result['final_url']=f.url;result['content_type']=f.headers.get('Content-Type')
  sha=hashlib.sha256(data).hexdigest();path=ROOT/'data/raw'/f'{sid}-{sha[:16]}.{ext}'
  if not path.exists():path.write_bytes(data)
  result.update(status='acquired',sha256=sha,bytes=len(data),path=str(path.relative_to(ROOT)))
 except Exception as e:result.update(status='failed',error=str(e))
 return result
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(fetch,SOURCES))
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
 (ROOT/'data'/f'acquisition-{stamp}.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 (ROOT/'data/manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([{k:r.get(k) for k in ['id','status','bytes','error']} for r in results],ensure_ascii=False))
