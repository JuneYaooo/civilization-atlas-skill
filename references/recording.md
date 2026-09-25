# 研究记录协议

`scripts/casebook.py`提供`validate`、`freeze`、`verify`和`review`子命令。通过`--help`查看参数。输入、快照和复盘文件均应放在Skill仓库外的研究目录。

## 对象

顶层使用`schema_version`、`id`、`question`、`target_definition`、`geography`、`time_scope`、`as_of`、`information_regime`，以及`sources`、`evidence`、`claims`、`mechanisms`、`predictions`集合。当前`schema_version`为1。

来源记录标题、URL、版本、访问范围及可得时间；证据记录来源ID、定位和观察；命题区分观察、作者解释、项目假设与价值目标，并关联支持、挑战或背景证据及理由。机制记录过程、适用条件、区分观察和命题引用。预测记录目标、期限、明确条件、状态、结算规则和命题引用。

信息模式可为`real_time`、`historical_reconstruction`或`synthetic`。实时模式要求来源版本的`available_at`不晚于`as_of`，时间带时区。今天下载的修订内容不能用旧发布日期冒充当时可得版本。

## 冻结与复盘

冻结写入完整输入、SHA256和本地时间，拒绝覆盖已有输出。验证检查内容摘要及结构；摘要不是签名，本地时间也不是可信第三方事前登记。

复盘输入为数组，每条记录包含`prediction_id`、`observed_outcome`、`condition_assessment`、`model_diagnosis`、`evidence_locators`和`verdict`。判定可为`supported`、`contradicted`、`unresolved`、`not_yet_due`或`unscorable`。程序另写复盘，保留原预测及未评估ID。

校验不证明内容真实，也不自动去重共同上游、估计因果或裁判结果。v1不支持数值概率登记。没有证据时保留未知，不为通过校验而制造资料。

固定期限的二元概率另用[数值登记协议](binary-registry.md)。两个工具的记录类型和职责不同，不将旧研究笔记直接视为已冻结的数值预测。
