from acquire import fetch,ROOT
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
SOURCES=[('wb-countries','https://api.worldbank.org/v2/country?format=json&per_page=400','json','World Bank country and aggregate metadata','https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation','retrieved snapshot','World Bank terms apply')]
for indicator,title in [('SP.POP.TOTL','Population total'),('NY.GDP.PCAP.KD','GDP per capita constant 2015 US$'),('SP.DYN.LE00.IN','Life expectancy'),('SP.URB.TOTL.IN.ZS','Urban population share'),('IT.NET.USER.ZS','Internet users share')]:
 SOURCES.append(('wb-'+indicator,'https://api.worldbank.org/v2/country/all/indicator/'+indicator+'?source=2&date=1960:2025&format=json&per_page=20000','json','WDI '+title,'https://data.worldbank.org/indicator/'+indicator,'retrieved snapshot; 1960-2025','World Bank terms apply; upstream attribution in metadata'))
 SOURCES.append(('wb-meta-'+indicator,'https://api.worldbank.org/v2/indicator/'+indicator+'?format=json','json','WDI metadata '+indicator,'https://data.worldbank.org/indicator/'+indicator,'retrieved snapshot','World Bank terms apply'))
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,SOURCES))
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
(ROOT/'data'/f'modern-acquisition-{stamp}.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
(ROOT/'data/modern-manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{k:r.get(k) for k in ['id','status','bytes','error']} for r in results]))
