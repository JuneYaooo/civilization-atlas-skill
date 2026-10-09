# 数据来源与许可

原有快照取得于 2026-09-25；八项 WDI 历史镜像于 2026-10-09 追加。采集日期不是观测截止年份。来源文件摘要、版本与链接保存在 `data/*manifest.json`；数据库对原始资料作结构化映射，没有把本项目的程序许可套用于所有外部数据。

| 来源 | 使用与归属 |
|---|---|
| [Seshat Polaris 2026](https://github.com/Seshat-Global-History-Databank/build_polaris_dataset) | 随上游仓库发布；[MIT 许可与署名](https://github.com/Seshat-Global-History-Databank/build_polaris_dataset/blob/main/LICENSE)。保留了原始 LICENSE 快照。Copyright © 2025 Seshat Global History Databank。 |
| [世界银行 WDI](https://datacatalog.worldbank.org/public-licenses) | 默认开放数据许可为 CC BY 4.0，并附额外条件；各指标的原始提供机构与定义保存在对应元数据快照中。使用时同时引用变量及上游机构。这里按国家年度重新组织原始记录。 |
| [NASA GISTEMP v4](https://data.giss.nasa.gov/gistemp/) | 引用 GISTEMP Team（2026），以及 Lenssen 等（2024），doi:10.1029/2023JD040179；读取全球温度距平表，保留原始字段。 |
| 历史事件编纂 | 本项目的编纂与解释；记录所列机构资料是依据来源，不代表第三方全文已获得再许可。 |

## WDI 历史镜像

追加数据来自 DataHub 的 World Development Indicators 镜像。八个 `datapackage.json` 均声明 CC BY 4.0；各指标的世界银行页面也已核对许可及上游归属。分发保留原始 CSV、元数据与文件摘要，使用时署名 World Bank、对应上游机构及 DataHub。逐项链接与年代见[本次扩充](reports/expansion-20261009.md)。

镜像的处理版本与首次发布日期未恢复；不能用于声称当时已可获得的数据回测。此次未把镜像值与原有同主题序列拼成一个“最新”序列。

## 另行获取的资料

[COW 数据条款](https://correlatesofwar.org/data-sets/)要求未经书面许可不得向第三方再分发。其[国家系统](https://correlatesofwar.org/data-sets/state-system-membership/)、[战争](https://correlatesofwar.org/data-sets/COW-war/)和[正式联盟](https://correlatesofwar.org/data-sets/formal-alliances/)可从官方入口了解和获取；当前内嵌快照不含这些数据及其派生行。
