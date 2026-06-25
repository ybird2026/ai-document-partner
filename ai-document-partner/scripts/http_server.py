#!/usr/bin/env python3
"""Local Markdown/HTML browser for this workspace."""

from __future__ import annotations

import argparse
import html
import http.server
import json
import os
import re
import socket
import socketserver
import urllib.parse
from datetime import datetime
from pathlib import Path


DEFAULT_PORT = 8027
DEFAULT_HOST = "0.0.0.0"
APP_NAME = "AI 文档伴侣"
SKILL_DIR = Path(__file__).resolve().parents[1]
FAVICON_PATH = SKILL_DIR / "assets" / "icon.ico"
ASSET_ROUTES = {
    "/assets/alpine.min.js": (SKILL_DIR / "assets" / "alpine.min.js", "text/javascript; charset=utf-8"),
    "/assets/document-browser.js": (
        SKILL_DIR / "assets" / "document-browser.js",
        "text/javascript; charset=utf-8",
    ),
    "/assets/ALPINE-LICENSE.md": (
        SKILL_DIR / "assets" / "ALPINE-LICENSE.md",
        "text/markdown; charset=utf-8",
    ),
}
PORT_FILE = Path(".skill-build") / "ai-document-partner.port"
SKIP_DIRS = {".git", ".cursor", ".trae", ".vscode", "__pycache__", "node_modules", "回收站"}


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Browse Markdown and HTML files.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--dir", default=os.getcwd())
    return parser.parse_args()


def find_available_port(host: str, start_port: int, attempts: int = 20) -> int:
    bind_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    for port in range(start_port, start_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((bind_host, port)) != 0:
                return port
    raise RuntimeError(f"No available port from {start_port} to {start_port + attempts - 1}")


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    in_code = False
    table_rows: list[list[str]] = []

    for line in lines:
        if line.strip().startswith("```"):
            if table_rows:
                output.append(build_table(table_rows))
                table_rows = []
            if in_code:
                output.append("</code></pre>")
            else:
                lang = html.escape(line.strip()[3:].strip())
                output.append(f'<pre class="code-block"><code class="language-{lang}">')
            in_code = not in_code
            continue

        if in_code:
            output.append(html.escape(line))
            continue

        if "|" in line and line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(set(cell) <= set("-: ") for cell in cells):
                table_rows.append(cells)
            continue

        if table_rows:
            output.append(build_table(table_rows))
            table_rows = []

        stripped = line.strip()
        if not stripped:
            output.append("")
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            output.append(f"<h{level}>{inline_md(heading.group(2))}</h{level}>")
            continue

        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            output.append("<hr>")
            continue

        quote = re.match(r"^>\s?(.*)$", line)
        if quote:
            output.append(f"<blockquote>{inline_md(quote.group(1))}</blockquote>")
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", line)
        if bullet:
            output.append(f"<ul><li>{inline_md(bullet.group(1))}</li></ul>")
            continue

        ordered = re.match(r"^\d+\.\s+(.+)$", line)
        if ordered:
            output.append(f"<ol><li>{inline_md(ordered.group(1))}</li></ol>")
            continue

        output.append(f"<p>{inline_md(line)}</p>")

    if table_rows:
        output.append(build_table(table_rows))

    return "\n".join(output)


def inline_md(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    escaped = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    return escaped


def build_table(rows: list[list[str]]) -> str:
    parts = ['<table class="md-table">']
    for index, row in enumerate(rows):
        tag = "th" if index == 0 else "td"
        cells = "".join(f"<{tag}>{inline_md(cell)}</{tag}>" for cell in row)
        parts.append(f"<tr>{cells}</tr>")
    parts.append("</table>")
    return "\n".join(parts)


def page(title: str, body: str, scripts: str = "") -> bytes:
    favicon_version = int(FAVICON_PATH.stat().st_mtime) if FAVICON_PATH.is_file() else 0
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#2563eb">
<link rel="icon" href="/favicon.ico?v={favicon_version}" type="image/x-icon">
<title>{html.escape(title)}</title>
<style>
:root {{
  --bg: #f7f8fb;
  --panel: #ffffff;
  --text: #16202a;
  --muted: #667085;
  --line: #d9e0ea;
  --accent: #2563eb;
  --soft: #eef4ff;
  --code: #111827;
}}
* {{ box-sizing: border-box; }}
[x-cloak] {{ display: none !important; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
  line-height: 1.68;
}}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.shell {{ max-width: 1120px; margin: 0 auto; padding: 28px 22px 56px; }}
.topbar {{ display: flex; justify-content: space-between; gap: 18px; align-items: end; margin-bottom: 4px; }}
.title {{ margin: 0; font-size: 24px; line-height: 1.25; }}
.meta {{ color: var(--muted); font-size: 13px; margin-top: 6px; }}
.remote-tip {{ margin: 0 0 14px; color: var(--muted); font-size: 13px; font-weight: 400; line-height: 1.6; }}
.remote-tip a {{ color: inherit; text-decoration: underline; text-underline-offset: 2px; }}
.document-toolbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 10px;
}}
.segmented {{
  display: inline-flex;
  align-items: center;
  padding: 2px;
  background: #e9edf4;
  border-radius: 6px;
}}
.segment-button {{
  min-height: 28px;
  padding: 0 12px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #475467;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
}}
.segment-button.active {{
  background: #ffffff;
  color: #174ea6;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.14);
  font-weight: 650;
}}
.today-toggle {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #475467;
  cursor: pointer;
  font-size: 13px;
  user-select: none;
}}
.today-toggle input {{ width: 16px; height: 16px; accent-color: var(--accent); }}
.explorer {{
  overflow: hidden;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}}
.columns,
.file-row {{
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 150px 130px 82px;
  align-items: center;
  min-width: 760px;
}}
.columns {{
  height: 34px;
  color: #475467;
  background: #f8fafc;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  font-weight: 650;
}}
.columns > span,
.file-row > span {{ padding: 0 12px; }}
.columns > span + span,
.file-row > span + span {{ border-left: 1px solid var(--line); }}
.sort-button {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-width: 0;
  height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-weight: inherit;
  text-decoration: none;
}}
.sort-button:hover {{ color: var(--accent); }}
.sort-button.active {{ color: #174ea6; }}
.sort-mark {{ color: var(--accent); font-size: 12px; margin-left: 6px; }}
.folder {{ border-bottom: 1px solid #edf1f6; }}
.folder:last-child {{ border-bottom: 0; }}
.folder summary {{
  display: flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 10px;
  color: #174ea6;
  cursor: pointer;
  user-select: none;
  font-weight: 650;
  list-style: none;
}}
.folder summary::-webkit-details-marker {{ display: none; }}
.folder summary::before {{
  content: ">";
  color: #667085;
  font-size: 12px;
  transform: rotate(90deg);
}}
.folder:not([open]) summary::before {{ transform: rotate(0deg); }}
.folder-name {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.folder-count {{ color: var(--muted); font-size: 12px; font-weight: 500; }}
.file-row {{
  min-height: 26px;
  color: var(--text);
  font-size: 13px;
  border-top: 1px solid #f2f4f7;
}}
.file-row:hover {{ background: #e8f2ff; text-decoration: none; }}
.file-name {{
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}}
.file-name-content {{ min-width: 0; padding: 5px 0; }}
.doc-icon {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 18px;
  border-radius: 4px;
  color: #ffffff;
  flex: 0 0 auto;
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
}}
.doc-icon.md {{ background: #2563eb; }}
.doc-icon.html {{ background: #0f766e; }}
.file-title {{
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #111827;
}}
.file-path {{
  display: block;
  overflow: hidden;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.file-row.compact .file-name-content {{ padding: 2px 0; }}
.date,
.type,
.size {{ color: #475467; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.size {{ text-align: right; }}
.empty-state {{ padding: 38px 20px; color: var(--muted); text-align: center; }}
.no-js {{ margin: 0 0 12px; color: #b42318; font-size: 13px; }}
.content {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 26px 30px;
}}
.content h1, .content h2 {{ border-bottom: 1px solid var(--line); padding-bottom: 8px; }}
.content h1 {{ font-size: 28px; }}
.content h2 {{ font-size: 22px; margin-top: 30px; }}
.content h3 {{ font-size: 18px; margin-top: 24px; }}
.content img {{ max-width: 100%; border-radius: 6px; }}
.content code {{ background: #eef2f7; padding: 2px 5px; border-radius: 4px; font-family: Consolas, monospace; }}
.content pre.code-block {{ background: var(--code); color: #e5e7eb; padding: 16px; border-radius: 8px; overflow-x: auto; }}
.content pre.code-block code {{ background: transparent; padding: 0; }}
.content blockquote {{ border-left: 4px solid var(--accent); background: var(--soft); margin: 16px 0; padding: 10px 16px; color: #344054; }}
.content table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
.content th, .content td {{ border: 1px solid var(--line); padding: 8px 10px; text-align: left; }}
.content th {{ background: #f1f5f9; }}
.back {{ display: inline-flex; margin-bottom: 16px; font-weight: 650; }}
@media (max-width: 700px) {{
  .topbar {{ display: block; }}
  .document-toolbar {{ align-items: flex-start; flex-direction: column; }}
  .content {{ padding: 18px 16px; }}
  .explorer {{ overflow-x: auto; }}
}}
</style>
</head>
<body>{body}{scripts}</body>
</html>"""
    return document.encode("utf-8")


def list_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not name.startswith(".")]
        current_path = Path(current)
        for name in names:
            if name.startswith("."):
                continue
            path = current_path / name
            if path.suffix.lower() in {".md", ".html", ".htm"}:
                files.append(path)
    return sorted(files, key=lambda p: str(p.relative_to(root)).lower())


def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size / 1024 / 1024:.1f} MB"


def file_type_label(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "MD 文件"
    if suffix in {".html", ".htm"}:
        return "HTML 文件"
    return f"{suffix.lstrip('.').upper()} 文件"


def folder_label(path: str) -> str:
    return "项目根目录" if not path else path


def project_label(root: Path) -> str:
    return root.name or str(root)


def document_payload(root: Path, path: Path) -> dict[str, str | int]:
    rel = path.relative_to(root).as_posix()
    rel_parent = path.parent.relative_to(root).as_posix()
    folder_key = "" if rel_parent == "." else rel_parent
    suffix = path.suffix.lower().lstrip(".")
    kind = "md" if suffix == "md" else "html"
    stat = path.stat()
    return {
        "name": path.name,
        "rel": rel,
        "folderKey": folder_key,
        "folderLabel": folder_label(folder_key),
        "modifiedMs": int(stat.st_mtime * 1000),
        "modifiedText": datetime.fromtimestamp(stat.st_mtime).strftime("%Y/%m/%d %H:%M"),
        "typeLabel": file_type_label(path),
        "sizeBytes": stat.st_size,
        "sizeText": format_size(stat.st_size),
        "kind": kind,
        "href": "/view?path=" + urllib.parse.quote(rel),
    }


def safe_json(data: object) -> str:
    return (
        json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


class BrowserHandler(http.server.SimpleHTTPRequestHandler):
    root: Path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.root), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in {"", "/"}:
            self.send_index()
            return
        if parsed.path == "/favicon.ico":
            self.send_favicon()
            return
        if parsed.path in ASSET_ROUTES:
            self.send_asset(parsed.path)
            return
        if parsed.path == "/view":
            params = urllib.parse.parse_qs(parsed.query)
            rel = params.get("path", [""])[0]
            self.send_file_view(rel)
            return
        super().do_GET()

    def send_favicon(self) -> None:
        if not FAVICON_PATH.is_file():
            self.send_error(404, "Favicon not found")
            return
        data = FAVICON_PATH.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/x-icon")
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_asset(self, route: str) -> None:
        path, content_type = ASSET_ROUTES[route]
        if not path.is_file():
            self.send_error(404, "Asset not found")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_index(self) -> None:
        documents = [document_payload(self.root, path) for path in list_files(self.root)]
        documents_json = safe_json(documents)
        project_name = project_label(self.root)
        body = (
            '<main class="shell" x-data="documentBrowser">'
            '<div class="topbar"><div>'
            f'<h1 class="title">{html.escape(APP_NAME)}</h1>'
            f'<div class="meta"><span x-text="visibleCount">{len(documents)}</span> 个文档 · '
            f'{html.escape(str(self.root))}</div>'
            '</div></div>'
            '<p class="remote-tip">如需远程访问（比如通勤路上通过手机访问），可借助'
            '<a href="http://url.oray.com/i/47635" target="_blank" rel="noopener noreferrer">蒲公英</a>、'
            '<a href="http://url.oray.com/i/47634" target="_blank" rel="noopener noreferrer">花生壳</a>等内网穿透工具实现。</p>'
            '<div class="document-toolbar" x-cloak>'
            '<div class="segmented" aria-label="文档视图">'
            '<button class="segment-button" :class="{ active: view === \'all\' }" '
            '@click="setView(\'all\')" type="button">全部文档</button>'
            '<button class="segment-button" :class="{ active: view === \'folders\' }" '
            '@click="setView(\'folders\')" type="button">按文件夹</button>'
            '</div>'
            '<label class="today-toggle">'
            '<input type="checkbox" :checked="filter === \'today\'" @change="toggleToday()">'
            '<span>今天修改</span>'
            '</label>'
            '</div>'
            '<noscript><p class="no-js">需要启用 JavaScript 才能使用排序、筛选和视图切换。</p></noscript>'
            '<section class="explorer" x-cloak>'
            '<div class="columns">'
            '<span><button class="sort-button" :class="{ active: sort === \'name\' }" '
            '@click="sortBy(\'name\')" type="button"><span>名称</span>'
            '<span class="sort-mark" x-text="sortMarker(\'name\')"></span></button></span>'
            '<span><button class="sort-button" :class="{ active: sort === \'modified\' }" '
            '@click="sortBy(\'modified\')" type="button"><span>修改日期</span>'
            '<span class="sort-mark" x-text="sortMarker(\'modified\')"></span></button></span>'
            '<span><button class="sort-button" :class="{ active: sort === \'type\' }" '
            '@click="sortBy(\'type\')" type="button"><span>类型</span>'
            '<span class="sort-mark" x-text="sortMarker(\'type\')"></span></button></span>'
            '<span><button class="sort-button" :class="{ active: sort === \'size\' }" '
            '@click="sortBy(\'size\')" type="button"><span>大小</span>'
            '<span class="sort-mark" x-text="sortMarker(\'size\')"></span></button></span>'
            '</div>'
            '<div x-show="view === \'all\'">'
            '<template x-for="document in visibleDocuments" :key="document.rel">'
            '<a class="file-row" :href="document.href" :title="document.rel" '
            'target="_blank" rel="noopener noreferrer">'
            '<span class="file-name"><span class="doc-icon" :class="document.kind" '
            'x-text="document.kind.toUpperCase()"></span>'
            '<span class="file-name-content"><span class="file-title" x-text="document.name"></span>'
            '<span class="file-path" x-text="document.folderLabel"></span></span></span>'
            '<span class="date" x-text="document.modifiedText"></span>'
            '<span class="type" x-text="document.typeLabel"></span>'
            '<span class="size" x-text="document.sizeText"></span>'
            '</a>'
            '</template>'
            '</div>'
            '<div x-show="view === \'folders\'">'
            '<template x-for="group in groups" :key="group.key">'
            '<details class="folder" open>'
            '<summary><span class="folder-name" x-text="group.label"></span>'
            '<span class="folder-count" x-text="`(${group.documents.length})`"></span></summary>'
            '<template x-for="document in group.documents" :key="document.rel">'
            '<a class="file-row compact" :href="document.href" :title="document.rel" '
            'target="_blank" rel="noopener noreferrer">'
            '<span class="file-name"><span class="doc-icon" :class="document.kind" '
            'x-text="document.kind.toUpperCase()"></span>'
            '<span class="file-name-content"><span class="file-title" x-text="document.name"></span>'
            '</span></span>'
            '<span class="date" x-text="document.modifiedText"></span>'
            '<span class="type" x-text="document.typeLabel"></span>'
            '<span class="size" x-text="document.sizeText"></span>'
            '</a>'
            '</template>'
            '</details>'
            '</template>'
            '</div>'
            '<div class="empty-state" x-show="visibleCount === 0">'
            '<span x-text="filter === \'today\' ? \'今天没有修改过的文档\' : '
            '\'当前目录没有 Markdown 或 HTML 文档\'"></span>'
            '</div>'
            '</section>'
            f'<script type="application/json" id="document-data">{documents_json}</script>'
            '</main>'
        )
        browser_js_path = ASSET_ROUTES["/assets/document-browser.js"][0]
        alpine_js_path = ASSET_ROUTES["/assets/alpine.min.js"][0]
        browser_js_version = int(browser_js_path.stat().st_mtime)
        alpine_js_version = int(alpine_js_path.stat().st_mtime)
        scripts = (
            f'<script defer src="/assets/document-browser.js?v={browser_js_version}"></script>'
            f'<script defer src="/assets/alpine.min.js?v={alpine_js_version}"></script>'
        )
        self.send_bytes(page(f"{APP_NAME}｜{project_name}", body, scripts=scripts))

    def send_file_view(self, rel: str) -> None:
        target = (self.root / rel).resolve()
        if self.root not in target.parents and target != self.root:
            self.send_error(403, "Forbidden")
            return
        if not target.is_file():
            self.send_error(404, "File not found")
            return

        suffix = target.suffix.lower()
        if suffix in {".html", ".htm"}:
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if suffix != ".md":
            self.send_error(415, "Unsupported file")
            return

        text = target.read_text(encoding="utf-8", errors="replace")
        body = (
            '<main class="shell">'
            '<a class="back" href="/">返回文档列表</a>'
            '<article class="content">'
            f'<h1>{html.escape(target.name)}</h1>'
            f'{markdown_to_html(text)}'
            '</article></main>'
        )
        self.send_bytes(page(f"{target.name}｜{APP_NAME}", body))

    def send_bytes(self, data: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        print(f"[AI-document-partner] {self.address_string()} {format % args}", flush=True)


def main() -> None:
    args = parse_args()
    root = Path(args.dir).resolve()
    port = find_available_port(args.host, args.port)
    BrowserHandler.root = root
    PORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PORT_FILE.write_text(str(port), encoding="utf-8")
    with ThreadingTCPServer((args.host, port), BrowserHandler) as server:
        print(f"Serving {root} at http://localhost:{port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()


