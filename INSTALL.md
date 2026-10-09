# 安装与使用

## 安装仓库版本

```sh
git clone https://github.com/JuneYaooo/civilization-atlas-skill.git
cd civilization-atlas-skill
python3 scripts/install_skill.py
```

在支持 Skill 的会话中调用 `$civilization-atlas`。安装程序默认使用 Codex 技能目录；`--dest` 可指定其他技能父目录，已有同名安装时停止覆盖。

## 为其他工具生成安装包

在所需版本的仓库根目录运行：

```sh
python3 scripts/install_skill.py --zip dist/civilization-atlas.zip
```

ZIP 包含 Skill、知识库和查询工具。WorkBuddy 提供本地技能包导入入口，操作见[官方技能安装说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。

## 查看知识库

```sh
python3 knowledge-base/scripts/serve.py
```

打开 `http://127.0.0.1:8765`，按关键词、主体、年代、主题和来源筛选。点击记录可查看原始字段、出处、文件摘要与行号。

```sh
python3 knowledge-base/scripts/query.py coverage
python3 knowledge-base/scripts/query.py search --help
```

Python 3.9+，仅使用标准库。外文数据优先按原文名称检索，中文名称映射仍在补充。

## 版本与更新

源码安装和本地打包使用当前检出的提交。可用 `git rev-parse --short HEAD` 核对版本；已安装的 Skill 不会随仓库更新自动同步。安装器不覆盖已有目录，更新时应先备份旧安装，再用新版本安装。

[2026-10-09 早期安装包](https://github.com/JuneYaooo/civilization-atlas-skill/releases/tag/mechanism-validation-2026-10-09)对应提交 `d63e2bb`，不包含后来新增的多渠道取证、转折记录及未来活动时间检查。需要这些能力时，从当前仓库安装或打包；发布页的安装包与主分支可能不同步。

安装包包含方法指令、参考协议、目录索引、知识库及研究工具。README 图示、演示报告和截图在仓库中查看，不属于安装内容。知识库快照与工具版本分别维护：更新指令不代表重新采集了数据。

[返回项目介绍](README.md)
