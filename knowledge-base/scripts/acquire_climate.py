from acquire import fetch,ROOT
from datetime import datetime,timezone
import json
item=('nasa-gistemp','https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts%2BdSST.csv','csv','NASA GISTEMP global land-ocean temperature anomaly','https://data.giss.nasa.gov/gistemp/','GISTEMP v4 retrieved snapshot','Cite GISTEMP Team 2026 and Lenssen et al. 2024 DOI 10.1029/2023JD040179; accessed 2026-09-25')
result=fetch(item)
(ROOT/'data/climate-manifest.json').write_text(json.dumps([result],ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result.get(k) for k in ['id','status','bytes','error']}))
