#!/usr/bin/env python3
"""
将 Markdown 文章发布到微信公众号草稿箱

用法:
  python3 publish.py <文章.md> [--digest 摘要]

配置:
  编辑 ../.env 文件:
    WECHAT_APPID=你的AppID
    WECHAT_APPSECRET=你的AppSecret
"""

import sys
import os
import json
import re
import time
import html
import io
import urllib.request
import urllib.error
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent

# 加载 .env
def load_env():
    env_file = PROJECT_DIR / ".env"
    if not env_file.exists():
        print("错误: 未找到 .env 文件，请在项目根目录创建 .env 配置 AppID 和 AppSecret")
        sys.exit(1)
    env = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_access_token(appid, appsecret):
    """获取微信 access_token"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={appsecret}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            if "access_token" in data:
                return data["access_token"]
            else:
                print(f"获取 access_token 失败: {data}")
                sys.exit(1)
    except urllib.error.URLError as e:
        print(f"网络错误: {e}")
        sys.exit(1)


def generate_cover(title):
    """自动生成封面图 (900x500)，黑色背景 + 白色大字标题"""
    width, height = 900, 500
    img = Image.new("RGB", (width, height), "#1a1a1a")
    draw = ImageDraw.Draw(img)

    # 尝试使用系统字体
    font_size = 48
    font = None
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            font = ImageFont.truetype(fp, font_size)
            break
    if font is None:
        font = ImageFont.load_default()

    # 文字换行
    chars_per_line = 16
    lines = []
    for i in range(0, len(title), chars_per_line):
        lines.append(title[i : i + chars_per_line])

    # 居中绘制
    line_height = font_size + 16
    total_height = len(lines) * line_height
    y_start = (height - total_height) // 2

    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        y = y_start + idx * line_height
        draw.text((x, y), line, fill="#ffffff", font=font)

    # 底部小字
    small_font = None
    for fp in font_paths:
        if os.path.exists(fp):
            small_font = ImageFont.truetype(fp, 18)
            break
    if small_font is None:
        small_font = ImageFont.load_default()
    tagline = "每日学习 · 刀哥"
    bbox = draw.textbbox((0, 0), tagline, font=small_font)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, height - 60), tagline, fill="#888888", font=small_font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_cover(access_token, image_data):
    """上传封面图到微信素材库，返回 media_id"""
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=image"

    boundary = "----WebKitFormBoundary" + hex(int(time.time() * 1000))[2:]
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="cover.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8")
    body += image_data
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if "media_id" in result:
                print(f"封面图上传成功: {result['media_id']}")
                return result["media_id"]
            else:
                print(f"封面上传失败: {result}")
                return None
    except urllib.error.URLError as e:
        print(f"封面图上传网络错误: {e}")
        return None


def md_to_wechat_html(md_text):
    """将 Markdown 转为公众号兼容 HTML（内联样式），支持表格和代码块"""
    lines = md_text.split("\n")
    out = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 代码块 — 收集内容直到闭合的 ```
        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # 跳过闭合的 ```
            if code_lines:
                code_html = "\n".join(html_escape(l) for l in code_lines)
                out.append(
                    f'<pre style="background:#f5f5f5;padding:12px;border-radius:4px;font-size:13px;line-height:1.7;color:#333;overflow-x:auto;white-space:pre-wrap;word-break:break-all;">{code_html}</pre>'
                )
            continue

        # 空行
        if not stripped:
            i += 1
            continue

        # 分隔线
        if stripped == "---":
            out.append(
                '<p style="text-align:center;margin:24px 0;color:#ccc;">· · ·</p>'
            )
            i += 1
            continue

        # 表格检测：当前行有 | 且至少有 2 个 |
        if stripped.count("|") >= 2:
            table_rows = []
            while i < len(lines) and lines[i].strip().count("|") >= 2:
                table_rows.append(lines[i].strip())
                i += 1
            out.append(_render_table(table_rows))
            continue

        # H1
        if line.startswith("# "):
            text = html_escape(line[2:])
            out.append(
                f'<h1 style="font-size:20px;font-weight:bold;color:#333;margin:24px 0 12px;line-height:1.4;">{text}</h1>'
            )
            i += 1
            continue

        # H2
        if line.startswith("## "):
            text = html_escape(line[3:])
            out.append(
                f'<h2 style="font-size:18px;font-weight:bold;color:#333;margin:20px 0 10px;line-height:1.4;">{text}</h2>'
            )
            i += 1
            continue

        # H3 — 特殊处理"AI 的总结"
        if line.startswith("### "):
            text = html_escape(line[4:])
            if "AI" in text and ("总结" in text or "视角" in text):
                out.append(
                    f'<p style="text-align:center;margin:32px 0 16px;"><span style="display:inline-block;padding:6px 20px;border-radius:20px;background:#1a6fc4;color:#fff;font-size:14px;font-weight:bold;letter-spacing:2px;">{text}</span></p>'
                )
            else:
                out.append(
                    f'<h3 style="font-size:16px;font-weight:bold;color:#333;margin:16px 0 8px;line-height:1.4;">{text}</h3>'
                )
            i += 1
            continue

        # 列表
        if re.match(r"^- ", line):
            text = render_inline(line[2:])
            out.append(
                f'<p style="font-size:15px;color:#3f3f3f;line-height:1.75;margin:4px 0 4px 16px;">· {text}</p>'
            )
            i += 1
            continue

        # 普通段落
        text = render_inline(line)
        out.append(
            f'<p style="font-size:15px;color:#3f3f3f;line-height:1.75;margin:0 0 12px;">{text}</p>'
        )
        i += 1
        out.append(
            f'<p style="font-size:15px;color:#3f3f3f;line-height:1.75;margin:0 0 12px;">{text}</p>'
        )
        i += 1

    body = "\n".join(out)
    return f'<section style="padding:0 10px;">{body}</section>'


def _render_table(rows):
    """将 Markdown 表格行转为 HTML 表格"""
    if len(rows) < 2:
        # 不是有效表格，退化成段落
        return f'<p style="font-size:15px;color:#3f3f3f;line-height:1.75;margin:0 0 12px;">{html_escape(" | ".join(rows))}</p>'

    # 解析每一行的单元格
    def parse_cells(row):
        cells = row.strip().strip("|").split("|")
        return [c.strip() for c in cells]

    # 表头
    header_cells = parse_cells(rows[0])

    # 检测分隔行（如 |---|---|）
    sep_cells = parse_cells(rows[1])
    is_sep = all(re.match(r"^:?-{3,}:?$", c) for c in sep_cells)

    if is_sep:
        data_start = 2
    else:
        data_start = 1

    # 对齐方式
    aligns = []
    if is_sep:
        for c in sep_cells:
            if c.startswith(":") and c.endswith(":"):
                aligns.append("center")
            elif c.endswith(":"):
                aligns.append("right")
            else:
                aligns.append("left")
    else:
        aligns = ["left"] * len(header_cells)

    # 数据行
    data_rows = [parse_cells(r) for r in rows[data_start:]]

    # 所有列
    all_rows = [header_cells] + data_rows
    num_cols = max(len(r) for r in all_rows)

    # 构建 HTML
    html_parts = [
        '<table style="width:100%;border-collapse:collapse;margin:12px 0;font-size:14px;">'
    ]

    # 表头
    html_parts.append('<thead>')
    html_parts.append('<tr style="background:#f5f5f5;">')
    for j in range(num_cols):
        cell = header_cells[j] if j < len(header_cells) else ""
        html_parts.append(
            f'<th style="padding:8px 10px;border:1px solid #e0e0e0;text-align:left;font-weight:bold;color:#333;">{html_escape(cell)}</th>'
        )
    html_parts.append('</tr>')
    html_parts.append('</thead>')

    # 表体
    html_parts.append('<tbody>')
    for row_idx, row in enumerate(data_rows):
        bg = "#fff" if row_idx % 2 == 0 else "#fafafa"
        html_parts.append(f'<tr style="background:{bg};">')
        for j in range(num_cols):
            cell = row[j] if j < len(row) else ""
            align = aligns[j] if j < len(aligns) else "left"
            cell_html = render_inline(cell)
            html_parts.append(
                f'<td style="padding:8px 10px;border:1px solid #e0e0e0;text-align:{align};color:#3f3f3f;">{cell_html}</td>'
            )
        html_parts.append('</tr>')
    html_parts.append('</tbody>')
    html_parts.append('</table>')

    return "\n".join(html_parts)


def html_escape(text):
    text = html.escape(text)
    return text


def render_inline(text):
    """处理行内加粗"""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text


def extract_title_and_digest(md_text):
    """从文章中提取标题和摘要"""
    lines = md_text.split("\n")
    title = ""
    digest = ""

    # 取第一个 # 标题
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # 摘要：取第一个非空、非标题段落的前 120 字，跳过引用和元信息
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            continue
        if stripped.startswith(">") or stripped.startswith("来源") or stripped.startswith("日期"):
            continue
        clean = re.sub(r"\*\*", "", stripped)
        digest = clean[:120]
        if len(clean) > 120:
            digest += "…"
        break

    return title, digest


def create_draft(access_token, title, content, thumb_media_id, digest=""):
    """创建公众号草稿"""
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"

    body = {
        "articles": [
            {
                "title": title,
                "author": "刀哥",
                "content": content,
                "digest": digest,
                "thumb_media_id": thumb_media_id,
                "content_source_url": "",
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
        ]
    }

    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json; charset=utf-8"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if "media_id" in result:
                media_id = result.get("media_id", "")
                print(f"草稿创建成功！media_id: {media_id}")
                print(f"标题: {title}")
                return media_id
            else:
                print(f"创建草稿失败: {result}")
                if result.get("errcode") == 45110:
                    print("→ 原因: 标题过长（上限 64 字）")
                return None
    except urllib.error.URLError as e:
        print(f"网络错误: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 publish.py <文章.md> [--digest 摘要]")
        print("示例: python3 publish.py 2026-05-14-坚持.md")
        sys.exit(1)

    md_path = SCRIPT_DIR / sys.argv[1]
    if not md_path.exists():
        print(f"文件不存在: {md_path}")
        sys.exit(1)

    # 读取 Markdown
    with open(md_path) as f:
        md_text = f.read()

    # 提取标题和摘要
    title, auto_digest = extract_title_and_digest(md_text)

    # 可选自定义摘要
    digest = auto_digest
    for i, arg in enumerate(sys.argv):
        if arg == "--digest" and i + 1 < len(sys.argv):
            digest = sys.argv[i + 1]
            break

    if not title:
        print("错误: 文章中未找到标题（# 开头）")
        sys.exit(1)

    print(f"标题: {title}")
    print(f"摘要: {digest[:60]}…" if len(digest) > 60 else f"摘要: {digest}")

    # 转换 HTML
    print("转换中…")
    content = md_to_wechat_html(md_text)

    # 获取 token
    print("连接微信…")
    env = load_env()
    access_token = get_access_token(env["WECHAT_APPID"], env["WECHAT_APPSECRET"])

    # 生成并上传封面
    print("生成封面…")
    cover_data = generate_cover(title)
    thumb_media_id = upload_cover(access_token, cover_data)
    if not thumb_media_id:
        print("错误: 封面图上传失败，无法创建草稿")
        sys.exit(1)

    # 创建草稿
    print("推送到草稿箱…")
    create_draft(access_token, title, content, thumb_media_id, digest)

    print("完成！打开公众号后台 → 图文消息 → 草稿箱 查看")


if __name__ == "__main__":
    main()
