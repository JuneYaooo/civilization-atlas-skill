# 历史与社会知识库

以来源可追溯的历史记录、政体与国家、联盟关系和社会指标，支持跨时期检索、比较历史研究与趋势分析。

当前包含 Seshat Polaris 2026、世界银行五项长期指标、NASA GISTEMP 全球温度序列，以及既有历史条目的迁移。实际规模和缺口以 [覆盖报告](reports/coverage.md) 为准。

## 浏览与检索

本目录随 Skill 提供可查询快照。首次查询自动验证摘要并解压至用户缓存；在本目录运行：

```sh
python3 scripts/serve.py
```

打开 `http://127.0.0.1:8765`，按关键词、来源、主体、主题和年代检索。点击记录查看原始字段、来源页面、文件摘要和行号。外文资料优先使用原文名称搜索；中文主题与名称映射尚未完整建立。

命令行入口：`python3 scripts/query.py --help`。提供 `search`、`record`、`entities`、`coverage` 子命令，各自支持 `--help`。结果为 JSON，适合研究 Skill 调用。

记录采用来源专属标识：Seshat 政体、COW 国家、COW 联盟与世界银行经济体分开。不同来源同名对象尚未声明为同一历史实体。日期筛选只使用有日期的断言，未注明年代的资料仍可通过政体检索找到。

## 数据层

- `data/raw/`：实际取得的来源快照，以内容摘要命名。
- `data/*manifest.json`：来源、获取时间、版本、摘要与获取状态。
- `data/history.sqlite.gz`：主体、来源记录、变量、观察和关系的压缩数据库。
- `reports/`：覆盖、缺测、日期质量以及地区—时期矩阵。
- `docs/collection-program.md`：各主题尚需采集的信息与验收方式。

历史事实与解释分开。来源原始代码、缺测、争议标记和时间区间均保留；导入成功不表示逐条独立核实。原始文献引文链仍需补齐，不能将数据库中的作者编码直接称为一手史料。

## 获取与重建

`acquire.py`、`acquire_modern.py`、`acquire_climate.py` 分别获取历史结构、现代指标和全球温度快照。首次构建还使用已迁移的编纂快照。采集脚本完成后检查 manifest 的获取状态；来源发生结构变化时应先复核适配器。

```sh
python3 scripts/build.py
python3 scripts/report.py
```

构建先校验来源摘要，再生成临时 SQLite 数据库，检查外键和完整性后替换查询库。原始快照保留；已有数据库不是历史所有版本的合并视图。当前重建使用后来发布或修订的资料，不可直接当作预测起点时可得的数据。

## 来源与引用

- [Seshat 数据入口](https://seshatdatabank.info/data)：Polaris 2026 的政体、社会复杂性、军事技术、宗教与危机编码；快照未提供每项断言的完整文献段落。
- [COW 国家系统](https://correlatesofwar.org/data-sets/state-system-membership/)：State System Membership v2024；请引用 Correlates of War Project（2025）。
- [COW 战争资料](https://correlatesofwar.org/data-sets/COW-war/)：Inter-State v4.0、Intra-State v5.1；参见 Sarkees 与 Wayman（2010）及相应版本说明。
- [COW 正式联盟](https://correlatesofwar.org/data-sets/formal-alliances/)：v4.1；Gibler（2009）。
- [世界银行指标 API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation)：各变量定义与上游机构保存在元数据快照中。
- [NASA GISTEMP](https://data.giss.nasa.gov/gistemp/)：GISTEMP Team（2026）；Lenssen 等（2024），doi:10.1029/2023JD040179。访问日期 2026-09-25。

各来源的使用与再分发条件分别适用，详见 [ATTRIBUTION.md](ATTRIBUTION.md)。COW 仅列官方入口，不包含在快照中。
