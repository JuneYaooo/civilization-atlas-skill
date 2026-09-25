# 二元预测登记与结算

`scripts/forecast_registry.py` 是独立的数值记录工具；`casebook.py` v1 保留原有研究笔记用途。新工具支持固定任务集合上的无条件二元概率、明确弃权、结果快照和 Brier 评分，不生成预测、不认证资料真实性、不证明校准或因果。

## 操作与文件边界

所有输入、冻结输出和评分报告放在 Skill 目录外。程序拒绝从 Skill 内读取研究记录或向其中写入记录，输出已存在时拒绝覆盖。各命令以 `--help` 查看参数。

| 命令 | 输入 | 作用 |
|---|---|---|
| `taskset` | 任务原始 JSON；`--output` | 校验并冻结任务集合 |
| `forecasts` | 预测原始 JSON；`--taskset` 冻结任务；`--output` | 冻结一次预测提交 |
| `outcomes` | 结果原始 JSON；`--taskset` 冻结任务；`--output` | 冻结一个结果版本 |
| `verify` | 冻结文件；非任务记录另需 `--taskset` | 核对摘要、引用与声明的约束 |
| `score` | 冻结任务；`--forecasts` 一个或两个冻结预测；`--outcomes` 冻结结果；`--output` | 单方法描述或同题配对评分 |

任务发生语义采用 `[event_start, event_end)`；时间均需 ISO 格式和时区。当前版本要求预测截止不晚于事件窗口开始，且不接受窗口结束前的提前结算。窗口内滚动预测、条件概率、多类别、连续量和权重暂不支持，应使用其他明确协议，不能藏在自由文本中绕过限制。

## 任务载荷

顶层字段全部必需，未知字段拒绝。`schema_version` 为整数 `1`。

| 字段 | 类型与意义 |
|---|---|
| `id` | 非空任务集合标识 |
| `information_regime` | `real_time`、`historical_reconstruction` 或 `synthetic` |
| `task_family` | 任务族说明；不能仅以主题接近断言任务可比 |
| `unit_definition` | 分析单位定义 |
| `risk_set_definition` | 哪些单位/时期进入分母，以及观察覆盖 |
| `aggregation` | 当前只接受 `equal_task`，每个任务等权 |
| `tasks` | 非空数组，每项字段见下 |

每个任务包含非空文本 `id`、`unit_id`、`target_definition`、`resolution_rule`，以及 `forecast_due`、`event_start`、`event_end`、`resolve_after` 四个时间。须满足 `forecast_due <= event_start < event_end <= resolve_after`。ID 唯一；相同单位、目标文本和时间窗口不得换 ID 重复计权。不同措辞的同义任务仍需人工识别。

## 来源载荷

预测与结果各有 `sources` 数组。每项包含唯一 `id`、非空 `url` 和 `version`、带时区的版本 `available_at`、64 位小写十六进制文件 `sha256`。程序只检查字段，不下载资料或核实摘要对应的文件，调用者须自行归档核对。无外部输入的明确先验方法可以使用空数组；已结算结果必须引用来源。

## 预测载荷

顶层包含 `schema_version`、`id`、`taskset_sha256`、`method_id`、`method_version`、`method_description`、`information_cutoff`、`issued_at`、`sources`、`forecasts`，均必需。

`taskset_sha256` 引用整个冻结任务记录的 `sha256`。`method_description` 说明输入、版本及研究条件；工具不验证资源公平性。`information_cutoff <= issued_at <=` 所有任务的预测截止。

`forecasts` 对每个已注册任务恰好一条。提供概率时字段是 `task_id`、`status: forecast`、`probability`；概率必须是 `[0,1]` 内有限数，布尔值不接受。弃权时字段是 `task_id`、`status: abstain`、非空 `reason`，不得附带概率。省略任务不是弃权。

## 结果载荷

顶层包含 `schema_version`、`id`、`taskset_sha256`、`as_of`、`sources`、`outcomes`，均必需。每个任务恰好一条状态：

- `resolved`：字段为 `task_id`、`status`、整数 `value`（0 或 1）、`known_at`、非空且无重复的 `source_ids`、非空 `locator`。必须有 `resolve_after <= known_at <= as_of`，引用版本不得晚于 `known_at`。
- `unresolved` 或 `invalid`：字段为 `task_id`、`status`、非空 `reason`。不附带结果数值。

来源版本不得晚于快照 `as_of`。结果的初次值和修订值分别冻结；评分报告绑定其中一个版本，不能覆盖旧结果。待结算、无效与实际未发生分开。结算规则是否被正确执行仍需独立复核。

## 冻结与时间检查

冻结记录包含 `record_type: frozen_binary_record`、整数 `schema_version: 1`、`kind`、本机 `frozen_at`、`payload` 和 `sha256`。摘要覆盖除 `sha256` 自身以外的全部字段。

实时模式要求任务注册不晚于预测发布，来源版本不晚于信息截止，任务和预测实际本地冻结均未超过截止。原始过去预测的重建应声明 `historical_reconstruction`；程序不会因手填旧 `issued_at` 而把今天的重建标为实时提交。合成记录也单独标识。

冻结时间不能在本机当前时间之后；预测发布、结果快照时间不得晚于各自冻结。验证保留相同检查。系统时钟、源日期和全部本地文件仍由操作者控制，修改后重算摘要也可伪造，因此这些检查不是签名、第三方时间戳或防篡改账本。

## 如何解释评分

每项二元 Brier 损失为 `(probability - value)^2`，整体采用等任务权重平均，越低越好。报告保留所有任务的状态、逐项损失、已结算/未结算/无效数量、各方法弃权及覆盖。

单方法成绩使用其预测且已结算的任务。两方法还报告共同已结算且双方未弃权的配对成绩、任务 ID 和 `brier_a_minus_b`；负值只表示 A 在这组共同任务的 Brier 更低。两者信息截止须相同。各自覆盖不同的单方法成绩不能直接作为优劣结论。

没有共同结果时得分为 `null`，不能填零。程序不对缺答补 0.5，不生成显著性、可信区间、胜者或罕见事件能力认证。均值偏差不是完整校准检验；重复单位、重叠期限和共同冲击仍须在独立评价中处理。方法质量和弃权代价也不能只由共同样本的分差决定。

评分依据与范围：[Gneiting 与 Raftery 的适当评分规则](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf)。工具采用二元平方损失的负向评分约定；未实现该文其他分布、估计或校准方法。
