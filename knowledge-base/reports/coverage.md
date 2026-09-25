# 当前知识库覆盖

构建时间：2026-09-25T11:54:39.523400+00:00

记录数是来源行数，含缺测和元数据；不等于独立史实数、事件总数或历史覆盖率。

| 来源 | 集合 | 行数 | 有日期记录的边界 |
|---|---|---:|---|
| legacy-events | curated_event | 72 | -3500 至 2025 |
| nasa-gistemp | global_temperature | 147 | 1880 至 2026 |
| seshat-polaris | CrisisDB - Crisis consequences | 166 | -2200 至 1942 |
| seshat-polaris | General | 7,239 | -1200 至 1991 |
| seshat-polaris | Luxury goods | 1,191 | -100 至 1926 |
| seshat-polaris | Polities | 626 | -13600 至 2020 |
| seshat-polaris | Religion | 5,466 | -9600 至 1942 |
| seshat-polaris | Social complexity | 26,033 | -7000 至 1991 |
| seshat-polaris | Variables | 173 | None 至 None |
| seshat-polaris | Warfare | 17,536 | -6000 至 1948 |
| wb-IT.NET.USER.ZS | country_year_indicator | 17,490 | 1960 至 2025 |
| wb-NY.GDP.PCAP.KD | country_year_indicator | 17,490 | 1960 至 2025 |
| wb-SP.DYN.LE00.IN | country_year_indicator | 17,490 | 1960 至 2025 |
| wb-SP.POP.TOTL | country_year_indicator | 17,490 | 1960 至 2025 |
| wb-SP.URB.TOTL.IN.ZS | country_year_indicator | 17,490 | 1960 至 2025 |

## 数据质量与解释

Seshat：626 个政体标识、42 个来源区域。区域并非现代国家。多数属性行未单列年代，不能把政体持续期当作该属性在每一年都有观察。

观察状态：[{"status": "disputed", "n": 390}, {"status": "missing", "n": 15988}, {"status": "source_categorical_bundle", "n": 166}, {"status": "source_code_or_value", "n": 54756}, {"status": "source_value", "n": 73481}, {"status": "uncertain", "n": 447}]。代码值不等于独立核验的数值；SU、IP、IA 等保留来源编码，当前不转换成布尔或概率。

倒置年代区间 0 条；年零记录 5 条。BCE 的年零规范尚需按源代码簿校准；不同资料的精确跨纪年联接尚未开展。

世界银行的国家／经济体与区域、收入组聚合值分开；历史分组不能由当前成员名单回填。COW 的联盟结束空值按 2012 年观察截止限制检索，不解释为一直延续到现在。

来源获取时间与首次公开时间分开；当前导入是后来版本的历史重建，不可直接作为无泄漏预测回测资料。

范围矩阵见 [region-period-coverage.csv](region-period-coverage.csv)，详细质量计数见 [quality.json](quality.json)。矩阵记录重叠出现次数，不把跨期记录重复视为独立证据。

## 主要缺口

历史叙事和逐条原始证据仍以既有 72 条编纂为起点；尚未形成各地区逐时期的系统史料库。前现代经济人口、疾病传播、古气候、灾害、教育文化、科学突破与当代资料更新需继续采集。Seshat 采样政体及 COW 门槛定义都不覆盖全部社会。
