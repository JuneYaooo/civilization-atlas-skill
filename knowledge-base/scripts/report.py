from query import ROOT,connect
import json,csv
from collections import Counter
with connect() as db:
 coverage=json.loads((ROOT/'reports/coverage.json').read_text())
 quality={'observation_status':[dict(x) for x in db.execute('SELECT status,count(*) AS n FROM observations GROUP BY status')],
 'undated_by_collection':[dict(x) for x in db.execute('SELECT source_id,collection,count(*) AS n FROM records WHERE start_year IS NULL GROUP BY source_id,collection')],
 'dated_assertions_reversed':db.execute('SELECT count(*) FROM records WHERE start_year>end_year').fetchone()[0],
 'zero_year_records':db.execute('SELECT count(*) FROM records WHERE start_year=0 OR end_year=0').fetchone()[0],
 'seshat_polities':db.execute("SELECT count(*) FROM entities WHERE id LIKE 'seshat:%'").fetchone()[0],
 'seshat_regions':db.execute("SELECT count(distinct region) FROM entities WHERE id LIKE 'seshat:%'").fetchone()[0],
 'wb_observed_entity_kinds':[dict(x) for x in db.execute("SELECT e.kind,count(distinct e.id) AS n FROM records r JOIN entities e ON e.id=r.entity_id WHERE r.source_id LIKE 'wb-%' GROUP BY e.kind")],
 'seshat_blank_values':db.execute("SELECT count(*) FROM observations WHERE variable_id LIKE 'seshat:%' AND status='missing'").fetchone()[0],
 'seshat_special_codes':dict(db.execute("SELECT json_extract(value_json,'$.value_from'),count(*) FROM observations WHERE variable_id LIKE 'seshat:%' AND json_extract(value_json,'$.value_from') IN ('SU','IP','IA','unknown','suspected unknown') GROUP BY 1").fetchall()),
 'first_publication_dates':'Not recovered for acquired snapshots; retrieval dates must not be used as historical availability dates',
 'review':'Structural import verified; no blanket independent verification of source facts'}
 (ROOT/'reports/quality.json').write_text(json.dumps(quality,ensure_ascii=False,indent=2)+'\n')
 periods=[(-3500,-2001),(-2000,-1001),(-1000,-1),(1,499),(500,999),(1000,1499),(1500,1799),(1800,1899),(1900,1999),(2000,2026)]
 # This is dated-record coverage, not proof that all facts within a polity are dated.
 regions=[r[0] for r in db.execute("SELECT DISTINCT region FROM entities WHERE id LIKE 'seshat:%' ORDER BY region")]
 with (ROOT/'reports/region-period-coverage.csv').open('w',newline='') as f:
  w=csv.writer(f,lineterminator="\n");w.writerow(['source','region','period_start','period_end','overlapping_polity_rows','overlapping_dated_assertions','undated_assertions_in_region'])
  for region in regions:
   undated=db.execute("SELECT count(*) FROM records r JOIN entities e ON e.id=r.entity_id WHERE r.source_id='seshat-polaris' AND e.region=? AND r.collection!='Polities' AND r.start_year IS NULL",(region,)).fetchone()[0]
   for lo,hi in periods:
    ps=db.execute("SELECT count(*) FROM records r JOIN entities e ON e.id=r.entity_id WHERE r.source_id='seshat-polaris' AND e.region=? AND r.collection='Polities' AND r.start_year<=? AND r.end_year>=?",(region,hi,lo)).fetchone()[0]
    ns=db.execute("SELECT count(*) FROM records r JOIN entities e ON e.id=r.entity_id WHERE r.source_id='seshat-polaris' AND e.region=? AND r.collection!='Polities' AND r.start_year<=? AND r.end_year>=?",(region,hi,lo)).fetchone()[0]
    w.writerow(['seshat-polaris',region,lo,hi,ps,ns,undated])
 text=['# 当前知识库覆盖','',f"构建时间：{coverage['built_at']}",'','记录数是来源行数，含缺测和元数据；不等于独立史实数、事件总数或历史覆盖率。','','| 来源 | 集合 | 行数 | 有日期记录的边界 |','|---|---|---:|---|']
 for x in coverage['collections']:text.append(f"| {x['source_id']} | {x['collection']} | {x['rows']:,} | {x['start']} 至 {x['end']} |")
 text+=['','## 数据质量与解释','',f"Seshat：{quality['seshat_polities']} 个政体标识、{quality['seshat_regions']} 个来源区域。区域并非现代国家。多数属性行未单列年代，不能把政体持续期当作该属性在每一年都有观察。",'',f"观察状态：{json.dumps(quality['observation_status'],ensure_ascii=False)}。代码值不等于独立核验的数值；SU、IP、IA 等保留来源编码，当前不转换成布尔或概率。",'',f"倒置年代区间 {quality['dated_assertions_reversed']} 条；年零记录 {quality['zero_year_records']} 条。BCE 的年零规范尚需按源代码簿校准；不同资料的精确跨纪年联接尚未开展。",'','世界银行的国家／经济体与区域、收入组聚合值分开；历史分组不能由当前成员名单回填。COW 的联盟结束空值按 2012 年观察截止限制检索，不解释为一直延续到现在。','', '来源获取时间与首次公开时间分开；当前导入是后来版本的历史重建，不可直接作为无泄漏预测回测资料。','', '范围矩阵见 [region-period-coverage.csv](region-period-coverage.csv)，详细质量计数见 [quality.json](quality.json)。矩阵记录重叠出现次数，不把跨期记录重复视为独立证据。','', '## 主要缺口','', '历史叙事和逐条原始证据仍以既有 72 条编纂为起点；尚未形成各地区逐时期的系统史料库。前现代经济人口、疾病传播、古气候、灾害、教育文化、科学突破与当代资料更新需继续采集。Seshat 采样政体及 COW 门槛定义都不覆盖全部社会。']
 (ROOT/'reports/coverage.md').write_text('\n'.join(text)+'\n')
print(json.dumps(quality,ensure_ascii=False))
