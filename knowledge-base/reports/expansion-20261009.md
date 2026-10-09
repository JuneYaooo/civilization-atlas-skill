# 2026-10-09 知识库扩充

新增 8 项可检索历史指标，共 73,865 条来源记录；数据库由 146,099 条增至 219,964 条。原有五项 WDI 序列未替换，旧数值回放的样本与结果保留。

## 新增内容

| 指标 | 记录数 | 文件内观测年份 | 上游归属 |
|---|---:|---|---|
| [总和生育率](https://datahub.io/world-development-indicators/sp.dyn.tfrt.in) | 13,770 | 1960—2016 | 联合国人口司、国家统计机构、Eurostat |
| [65岁及以上人口占比](https://datahub.io/world-development-indicators/sp.pop.65up.to.zs) | 13,615 | 1960—2016 | 联合国人口司 |
| [国内私人部门信贷占GDP比重](https://datahub.io/world-development-indicators/fs.ast.prvt.gd.zs) | 9,326 | 1960—2016 | IMF、世界银行、OECD |
| [居民消费价格通胀率](https://datahub.io/world-development-indicators/fp.cpi.totl.zg) | 11,295 | 1960—2024 | IMF |
| [失业率（ILO模型估计）](https://datahub.io/world-development-indicators/sl.uem.totl.zs) | 6,291 | 1991—2017 | ILO 模型估计 |
| [研发支出占GDP比重](https://datahub.io/world-development-indicators/gb.xpd.rsdv.gd.zs) | 3,064 | 1996—2023 | UNESCO UIS |
| [医院床位](https://datahub.io/world-development-indicators/sh.med.beds.zs) | 5,861 | 1960—2021 | WHO 与国家资料 |
| [商品和服务出口占GDP比重](https://datahub.io/world-development-indicators/ne.exp.gnfs.zs) | 10,643 | 1960—2016 | 国家统计机构、中央银行与世界银行估计 |

## 数据从哪里来

八项数据通过 DataHub 的 WDI 历史镜像取得；世界银行原始指标页面用于核对定义、来源机构及许可。镜像下载成功，不代表取得了世界银行当前版本：本轮直连官方批量接口未成功。镜像文件的实际年份已逐行统计，不使用网页“更新于”字段推定观测更新。

原始文件和元数据在 `data/raw/`，下载 URL、摘要、取得时间、行数与观测边界在[扩展清单](../data/extended-manifest.json)。首次发布日期和完整修订链未知，不能冒充历史时点可得数据。与原有序列使用不同来源和变量标识，避免混用版本。

## 如何使用与避免误读

- **总和生育率**：不能当作家庭实际生育决定或当代生育率。 [世界银行定义](https://data.worldbank.org/indicator/SP.DYN.TFRT.IN)。
- **65岁及以上人口占比**：不等于抚养负担或某城市人口结构。 [世界银行定义](https://data.worldbank.org/indicator/SP.POP.65UP.TO.ZS)。
- **国内私人部门信贷占GDP比重**：不等于居民房贷余额或个人贷款资格。 [世界银行定义](https://data.worldbank.org/indicator/FS.AST.PRVT.GD.ZS)。
- **居民消费价格通胀率**：不同国家篮子与修订口径可能不同。 [世界银行定义](https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG)。
- **失业率（ILO模型估计）**：模型估计不等于当地岗位需求或失业登记数。 [世界银行定义](https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS)。
- **研发支出占GDP比重**：研发投入不等于创新产出或突破速度。 [世界银行定义](https://data.worldbank.org/indicator/GB.XPD.RSDV.GD.ZS)。
- **医院床位**：床位数不等于可部署的医护与疫情响应能力。 [世界银行定义](https://data.worldbank.org/indicator/SH.MED.BEDS.ZS)。
- **商品和服务出口占GDP比重**：出口比重不等于单个企业收入；不含进口，不能称作全部贸易依赖。 [世界银行定义](https://data.worldbank.org/indicator/NE.EXP.GNFS.ZS)。

查询示例（仓库根目录）：

```sh
python3 knowledge-base/scripts/query.py search --source wdi-mirror-SP.DYN.TFRT.IN --entity wb:CHN --start 2000 --limit 5
python3 knowledge-base/scripts/query.py search --q 研发 --limit 5
```

记录保留原始国家名称、代码、年份、数值和 CSV 行号。已知代码连接原有经济体标识；未匹配原有主体元数据的代码独立保留，类型标记为未解决，不自行指定为国家或聚合组。没有为缺失年份插值。

[整体覆盖](coverage.md) · [来源许可](../ATTRIBUTION.md)
