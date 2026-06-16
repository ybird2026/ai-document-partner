#!/usr/bin/env python3
"""Local Markdown/HTML browser for this workspace."""

from __future__ import annotations

import argparse
import html
import http.server
import os
import re
import socket
import socketserver
import urllib.parse
from collections import defaultdict
from datetime import datetime
from pathlib import Path


DEFAULT_PORT = 8027
DEFAULT_HOST = "0.0.0.0"
APP_NAME = "AI 文档伴侣"
SKILL_DIR = Path(__file__).resolve().parents[1]
FAVICON_PATH = SKILL_DIR / "assets" / "icon.png"
PORT_FILE = Path(".skill-build") / "ai-document-partner.port"
SKIP_DIRS = {".git", ".cursor", ".trae", ".vscode", "__pycache__", "node_modules", "回收站"}
SORT_LABELS = {"name": "名称", "modified": "修改日期", "type": "类型", "size": "大小"}
SORT_DEFAULT_DIRECTIONS = {"name": "asc", "modified": "desc", "type": "asc", "size": "desc"}
DEFAULT_SORT = "modified"
DEFAULT_SORT_DIR = "desc"
VALID_SORT_DIRS = {"asc", "desc"}


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


def page(title: str, body: str) -> bytes:
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#2563eb">
<link rel="icon" href="/favicon.png" type="image/png">
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
.topbar {{ display: flex; justify-content: space-between; gap: 18px; align-items: end; margin-bottom: 22px; }}
.title {{ margin: 0; font-size: 24px; line-height: 1.25; }}
.meta {{ color: var(--muted); font-size: 13px; margin-top: 6px; }}
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
.sort-link {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-width: 0;
  color: inherit;
  text-decoration: none;
}}
.sort-link:hover {{ color: var(--accent); text-decoration: none; }}
.sort-link.active {{ color: #174ea6; }}
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #111827;
}}
.date,
.type,
.size {{ color: #475467; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.size {{ text-align: right; }}
.empty-state {{ padding: 38px 20px; color: var(--muted); text-align: center; }}
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
  .content {{ padding: 18px 16px; }}
  .explorer {{ overflow-x: auto; }}
}}
</style>
</head>
<body>{body}</body>
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


def normalize_sort_params(params: dict[str, list[str]]) -> tuple[str, str]:
    sort_key = params.get("sort", [DEFAULT_SORT])[0]
    if sort_key not in SORT_LABELS:
        return DEFAULT_SORT, DEFAULT_SORT_DIR

    if "dir" not in params:
        return sort_key, SORT_DEFAULT_DIRECTIONS[sort_key]

    sort_dir = params.get("dir", [""])[0]
    if sort_dir not in VALID_SORT_DIRS:
        return DEFAULT_SORT, DEFAULT_SORT_DIR
    return sort_key, sort_dir


def sort_files(paths: list[Path], sort_key: str, sort_dir: str) -> list[Path]:
    by_name = sorted(paths, key=lambda path: path.name.lower())
    reverse = sort_dir == "desc"
    if sort_key == "name":
        return sorted(by_name, key=lambda path: path.name.lower(), reverse=reverse)
    if sort_key == "modified":
        return sorted(by_name, key=lambda path: path.stat().st_mtime, reverse=reverse)
    if sort_key == "type":
        return sorted(by_name, key=lambda path: file_type_label(path), reverse=reverse)
    if sort_key == "size":
        return sorted(by_name, key=lambda path: path.stat().st_size, reverse=reverse)
    return sort_files(by_name, DEFAULT_SORT, DEFAULT_SORT_DIR)


def sort_header(label: str, key: str, current_sort: str, current_dir: str) -> str:
    is_active = key == current_sort
    next_dir = "asc" if is_active and current_dir == "desc" else "desc" if is_active else SORT_DEFAULT_DIRECTIONS[key]
    marker = " ↓" if is_active and current_dir == "desc" else " ↑" if is_active else ""
    active_class = " active" if is_active else ""
    href = f"/?sort={urllib.parse.quote(key)}&dir={urllib.parse.quote(next_dir)}"
    return (
        f'<a class="sort-link{active_class}" href="{href}">'
        f'<span>{html.escape(label)}</span><span class="sort-mark">{html.escape(marker)}</span>'
        '</a>'
    )


def build_columns(current_sort: str, current_dir: str) -> str:
    headers = "".join(
        f"<span>{sort_header(label, key, current_sort, current_dir)}</span>"
        for key, label in SORT_LABELS.items()
    )
    return f'<div class="columns">{headers}</div>'


class BrowserHandler(http.server.SimpleHTTPRequestHandler):
    root: Path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.root), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in {"", "/"}:
            params = urllib.parse.parse_qs(parsed.query)
            self.send_index(params)
            return
        if parsed.path == "/favicon.png":
            self.send_favicon()
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
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_index(self, params: dict[str, list[str]]) -> None:
        current_sort, current_dir = normalize_sort_params(params)
        files = list_files(self.root)
        groups: dict[str, list[Path]] = defaultdict(list)
        for path in files:
            rel_parent = path.parent.relative_to(self.root).as_posix()
            groups["" if rel_parent == "." else rel_parent].append(path)

        sections = []
        for folder in sorted(groups.keys(), key=lambda value: (value != "", value.lower())):
            rows = []
            for path in sort_files(groups[folder], current_sort, current_dir):
                rel = path.relative_to(self.root).as_posix()
                suffix = path.suffix.lower().lstrip(".")
                kind = "md" if suffix == "md" else "html"
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y/%m/%d %H:%M")
                size = format_size(stat.st_size)
                doc_type = file_type_label(path)
                href = "/view?path=" + urllib.parse.quote(rel)
                rows.append(
                    f'<a class="file-row" href="{href}" title="{html.escape(rel)}" target="_blank" rel="noopener noreferrer">'
                    f'<span class="file-name"><span class="doc-icon {kind}">{kind.upper()}</span>'
                    f'<span class="file-title">{html.escape(path.name)}</span></span>'
                    f'<span class="date">{html.escape(modified)}</span>'
                    f'<span class="type">{html.escape(doc_type)}</span>'
                    f'<span class="size">{html.escape(size)}</span>'
                    '</a>'
                )
            folder_text = folder_label(folder)
            sections.append(
                '<details class="folder" open>'
                f'<summary><span class="folder-name">{html.escape(folder_text)}</span>'
                f'<span class="folder-count">({len(rows)})</span></summary>'
                f'{"".join(rows)}'
                '</details>'
            )

        if sections:
            explorer = (
                '<section class="explorer">'
                f'{build_columns(current_sort, current_dir)}'
                f'{"".join(sections)}'
                '</section>'
            )
        else:
            explorer = '<section class="explorer"><div class="empty-state">当前目录没有 Markdown 或 HTML 文档</div></section>'

        project_name = project_label(self.root)
        body = (
            '<main class="shell">'
            '<div class="topbar"><div>'
            f'<h1 class="title">{html.escape(APP_NAME)}</h1>'
            f'<div class="meta">{len(files)} 个文档 · {html.escape(str(self.root))}</div>'
            '</div></div>'
            f'{explorer}'
            '</main>'
        )
        self.send_bytes(page(f"{APP_NAME}｜{project_name}", body))

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


