# 历史候选匹配接口

两个命令共用 `scripts/analogue_matcher.py`：事件模式为 `event_matcher.py`，人物决策片段模式为 `historical_figure_matcher.py`。它们只处理给定 JSON，不联网、不自动理解文本、不自带固定人物/危机故事。由宿主 agent 完成检索、读原文和结构编码，再调用排序器。

```sh
python3 scripts/event_matcher.py --request /tmp/research-request.json --candidates /tmp/research-candidates.json
python3 scripts/historical_figure_matcher.py --request /tmp/research-request.json --candidates /tmp/research-candidates.json
```

请求对象必须包含 `as_of`（带时区 ISO 时间）、`features` 和 `conditions`。事件维度：`mechanisms`、`constraints`、`stage`；人物片段维度：`decision_types`、`objectives`、`constraints`、`reversibility`。每项为字符串标签数组；中英文不会自动映射，先统一术语。至少一项非空。`conditions` 为已知条件的字符串映射，未知字段省略，不猜测。

候选文件为对象数组，每项必须有 `id`、`title`、`features`、`required_conditions`、`transfer_limits` 和 `sources`。`transfer_limits` 是非空字符串数组，说明已识别的差异/未知。`required_conditions` 是条件字符串映射，由取证明确的迁移必要条件构成，不把所有差异都当成必要条件。

每个来源必须有 `url`（HTTP/S，无凭据）、`locator`、`basis`（该来源实际支持的编码理由）、`access_scope`（`full_text`、`excerpt` 或 `snippet`）、`available_at`（带时区时间或 null）、`accessed_at`（带时区时间）。本工具检查结构而不认证内容。片段阅读只能支持片段范围内的编码；搜索摘要不能支撑可采用的候选。

排序采用各维度等权的请求标签覆盖均值，不对结果拟合权重。返回 `rank_score`（0—1，仅检索排序）、匹配标签、缺失维度、条件缺口、来源可得时间状态与迁移限制。分数不是相似世界的频率、因果可信度或成功概率。

必要条件冲突、来源在截止后才可得或只有摘要的候选不进入排名，并给出原因；缺少必要条件或原始可得时间未知的候选只可暂列 `provisional`。完全不相交则返回 `no_analogue`，不硬配人物。保留被排除候选和无匹配结果；再检索对照对象，不依据成功结局调整标签。

`as_of` 指证据截止时点，不是故事发生时间。今天阅读古代人物研究属于今天的决策研究；用今天材料模拟过去预测，仍需另行标为历史重建。
