---
name: "ai-document-partner"
description: "启动 AI 文档伴侣：一个本地 Web 服务，用新版 Workspace Markdown/HTML Browser 浏览项目中的 Markdown 和 HTML 文件，支持目录分组、文件类型徽标、修改时间、文件大小、Markdown 实时渲染、HTML 直显和端口自动递增。适用于用户要求启动 AI-document-partner、启动文档伴侣技能、打开文档伴侣、预览 Markdown、浏览 HTML、启动 md-html-browser、启动 md/html 在线浏览服务，或在局域网/本机分享文档页面。"
---

# AI 文档伴侣

## 功能概述

使用 `scripts/http_server.py` 启动轻量级本地文档浏览服务。服务会扫描指定目录下的 `.md`、`.html`、`.htm` 文件，并提供新版 Workspace 风格列表页。

“AI-document-partner”“AI 文档伴侣”“文档伴侣技能”“文档伴侣”“MD 在线浏览技能”“Markdown 在线浏览技能”“md-html-browser”都指向本技能。用户说“启动文档伴侣技能”或“启动 AI-document-partner”时，直接按本技能流程启动服务。

主要能力：

- 按目录分组展示 Markdown/HTML 文件
- 支持按名称、修改日期、类型、大小排序；默认各文件夹内按修改日期倒序
- 显示文件类型、修改时间、文件大小
- 点击文件时新窗口打开预览
- Markdown 文件实时渲染为 HTML
- HTML 文件直接展示原始页面
- 生成 `AI 文档伴侣｜项目名` 风格的浏览器标题，并使用 `assets/icon.png` 作为 favicon
- 跳过 `.git`、`.cursor`、`.trae`、`.vscode`、`__pycache__`、`node_modules`、`回收站` 等目录
- 默认从 `8027` 启动；如果端口被占用，自动尝试 `8028`、`8029`，最多尝试 20 个端口
- 启动后将实际端口写入 `.skill-build/ai-document-partner.port`

## 默认启动方式

在用户当前项目目录中启动：

```bash
python C:/Users/gzbesto/.codex/skills/ai-document-partner/scripts/http_server.py --dir . --host 0.0.0.0 --port 8027
```

如果用户希望只允许本机访问，使用：

```bash
python C:/Users/gzbesto/.codex/skills/ai-document-partner/scripts/http_server.py --dir . --host 127.0.0.1 --port 8027
```

## 参数说明

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--dir` | 要浏览的文件根目录 | 当前工作目录 |
| `--host` | 监听地址；局域网访问用 `0.0.0.0`，仅本机访问用 `127.0.0.1` | `0.0.0.0` |
| `--port` | 起始端口 | `8027` |

## 使用流程

1. 在用户目标项目目录中运行 `scripts/http_server.py`。
2. 读取命令输出中的访问地址，或读取 `.skill-build/ai-document-partner.port` 获取实际端口。
3. 告诉用户访问 `http://localhost:<端口>` 或 `http://127.0.0.1:<端口>`。
4. 如果用户需要局域网访问，提醒使用本机局域网 IP 加端口。

## 注意事项

- 不要把完整服务代码复制到回答里；优先运行本技能的 `scripts/http_server.py`。
- 如果已有旧实例占用 `8027`、`8028` 或 `8029`，新实例会自动使用后续端口。
- 技能目录已从 `md-html-browser` 更名为 `ai-document-partner`；`AI-document-partner` 作为显示名和触发别名保留，旧名称仅作为触发别名保留。

