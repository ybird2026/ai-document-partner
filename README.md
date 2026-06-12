# AI 文档伴侣

AI 文档伴侣是一个 Codex 技能，用来在本地启动 Workspace 风格的 Markdown/HTML 在线浏览服务。它适合用于预览项目文档、浏览 HTML 报告、在本机或局域网中分享文档页面。

## 能做什么

- 扫描指定目录下的 `.md`、`.html`、`.htm` 文件。
- 按目录分组展示文件列表。
- 显示文件类型、修改时间和文件大小。
- 点击文件时新窗口打开预览。
- Markdown 文件实时渲染为 HTML。
- HTML 文件直接展示原始页面。
- 默认从 `8027` 启动；如果端口被占用，自动尝试 `8028`、`8029` 等后续端口。
- 启动后将实际端口写入 `.skill-build/ai-document-partner.port`。

## 目录结构

```text
ai-document-partner/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── scripts/
    └── http_server.py
```

## 使用方式

在任意项目目录中运行：

```bash
python ai-document-partner/scripts/http_server.py --dir . --host 0.0.0.0 --port 8027
```

如果只希望本机访问，使用：

```bash
python ai-document-partner/scripts/http_server.py --dir . --host 127.0.0.1 --port 8027
```

启动后访问：

```text
http://localhost:<实际端口>
```

实际端口可从命令行输出查看，也可以读取：

```text
.skill-build/ai-document-partner.port
```

## 参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--dir` | 要浏览的文件根目录 | 当前工作目录 |
| `--host` | 监听地址；局域网访问用 `0.0.0.0`，仅本机访问用 `127.0.0.1` | `0.0.0.0` |
| `--port` | 起始端口 | `8027` |

## 技能触发词

以下说法都可以指向这个技能：

- 启动 AI-document-partner
- 启动 AI 文档伴侣
- 启动文档伴侣技能
- 打开文档伴侣
- 启动 Markdown/HTML 在线浏览服务
- 启动 md-html-browser

## 开源协议

MIT
