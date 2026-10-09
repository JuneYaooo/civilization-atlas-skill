#!/usr/bin/env python3
"""Produce a search plan for the host agent. This program does not search the web."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def plan(question, mode, topics, as_of):
    if not isinstance(question, str) or not question.strip():
        raise ValueError('question must not be empty')
    date = datetime.fromisoformat(as_of.replace('Z', '+00:00'))
    if date.tzinfo is None:
        raise ValueError('as_of needs timezone')
    if mode not in ('event', 'personal'):
        raise ValueError('unknown mode')
    catalog = json.loads((ROOT / 'references/source-routes.json').read_text())['sources']
    selected = [s for s in catalog if set(s['topics']) & set(topics)]
    q = question.strip()
    facts = [q + ' 原始公告 数据定义 发布时间 更正']
    facts += [q + ' site:' + urlsplit(s['url']).hostname for s in selected]
    return {
        'mode': mode, 'as_of': as_of, 'execution_status': 'plan_only_not_searched',
        'pre_search_reflection': {
            'status': 'host_reasoning_required',
            'questions': ['What outcome and scope are being judged?', 'Which factors, interactions and opposing pathways could change it?', 'Which current states and rates are unknown or decision-sensitive?', 'Which historical comparisons test each mechanism?', 'What omitted condition could reverse the conclusion?'],
            'record': 'Save a concise factor map with inclusion/exclusion reasons in the external research workspace before selecting analogues; revise with evidence.'
        },
        'source_routes': selected,
        'stages': [
            {'stage': 'facts', 'queries': facts, 'deliverable': 'Dated evidence with original upstream, locator and access scope'},
            {'stage': 'mechanisms', 'queries': [q + ' 机制 研究 反证 替代解释', q + ' 条件变化 网络结构 扩散速度 响应延迟 实际覆盖 容量', q + ' 观测变化 阶段转换 竞争机制'], 'deliverable': 'Evidence per causal link, not consensus counts'},
            {'stage': 'historical_comparison', 'queries': [q + (' 历史 决策 书信 传记 约束' if mode == 'personal' else ' 历史 对照 相同冲击 不同结果'), q + ' 失败案例 幸存者偏差 不适用条件'], 'deliverable': 'Candidate episodes plus disanalogies or no analogue'},
            {'stage': 'update_check', 'queries': [q + ' 最新 更正 修订'], 'deliverable': 'Recheck decision-sensitive facts before answering; no background monitoring'},
        ],
        'execution': 'Use available host search/browse tools; open original pages. Queries and date filters do not enforce historical availability.',
        'privacy': 'Supply public event keywords or abstract decision structure, not identifying private details.',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--question', required=True)
    p.add_argument('--mode', choices=('event', 'personal'), required=True)
    p.add_argument('--topic', action='append', choices=('health', 'economy', 'history', 'personal', 'technology', 'climate'), default=[])
    p.add_argument('--as-of', required=True)
    a = p.parse_args()
    try:
        result = plan(a.question, a.mode, a.topic, a.as_of)
    except ValueError as exc:
        p.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
