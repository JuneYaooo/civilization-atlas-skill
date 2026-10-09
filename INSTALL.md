# 安装与使用

### 在 Codex 中安装

```sh
git clone https://github.com/JuneYaooo/civilization-atlas-skill.git
cd civilization-atlas-skill
python3 scripts/install_skill.py
```

在支持 Skill 的会话中调用 `$civilization-atlas`。安装程序默认使用 Codex 技能目录；`--dest` 可指定其他技能父目录，已有同名安装时停止覆盖。

### 下载或生成 Skill 安装包

[下载含知识库的 ZIP 安装包](https://github.com/JuneYaooo/civilization-atlas-skill/releases/download/mechanism-validation-2026-10-09/civilization-atlas-validation-20261009.zip) · [查看发布版本](https://github.com/JuneYaooo/civilization-atlas-skill/releases/tag/mechanism-validation-2026-10-09)

也可在本地生成：

```sh
python3 scripts/install_skill.py --zip dist/civilization-atlas.zip
```

ZIP 包含 Skill、知识库和查询工具。WorkBuddy 提供本地技能包导入入口，操作见[官方技能安装说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。

### 直接查看知识库

```sh
python3 knowledge-base/scripts/serve.py
```

打开 `http://127.0.0.1:8765`，按关键词、主体、年代、主题和来源筛选。点击记录可查看原始字段、出处、文件摘要与行号。

```sh
python3 knowledge-base/scripts/query.py coverage
python3 knowledge-base/scripts/query.py search --help
```

Python 3.9+，仅使用标准库。外文数据优先按原文名称检索，中文名称映射仍在补充。


[返回项目介绍](README.md)
