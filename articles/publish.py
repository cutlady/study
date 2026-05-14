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
import urllib.request
import urllib.error
from pathlib import Path

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


def md_to_wechat_html(md_text):
    """将 Markdown 转为公众号兼容 HTML（内联样式）"""
    lines = md_text.split("\n")
    out = []

    for line in lines:
        stripped = line.strip()

        # 代码块
        if stripped.startswith("```"):
            continue

        # 空行 → 段落间隔
        if not stripped:
            continue

        # 分隔线
        if stripped == "---":
            out.append(
                '<p style="text-align:center;margin:24px 0;color:#ccc;">· · ·</p>'
            )
            continue

        # H1
        if line.startswith("# "):
            text = html_escape(line[2:])
            out.append(
                f'<h1 style="font-size:20px;font-weight:bold;color:#333;margin:24px 0 12px;line-height:1.4;">{text}</h1>'
            )
            continue

        # H2
        if line.startswith("## "):
            text = html_escape(line[3:])
            out.append(
                f'<h2 style="font-size:18px;font-weight:bold;color:#333;margin:20px 0 10px;line-height:1.4;">{text}</h2>'
            )
            continue

        # H3
        if line.startswith("### "):
            text = html_escape(line[4:])
            out.append(
                f'<h3 style="font-size:16px;font-weight:bold;color:#333;margin:16px 0 8px;line-height:1.4;">{text}</h3>'
            )
            continue

        # 列表
        if re.match(r"^- ", line):
            text = render_inline(line[2:])
            out.append(
                f'<p style="font-size:15px;color:#3f3f3f;line-height:1.75;margin:4px 0 4px 16px;">· {text}</p>'
            )
            continue

        # 普通段落
        text = render_inline(line)
        out.append(
            f'<p style="font-size:15px;color:#3f3f3f;line-height:1.75;margin:0 0 12px;">{text}</p>'
        )

    # 包裹 section（公众号要求）
    body = "\n".join(out)
    return f'<section style="padding:0 10px;">{body}</section>'


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

    # 摘要：取第一个非空、非标题段落的前 120 字
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            continue
        # 去掉加粗标记
        clean = re.sub(r"\*\*", "", stripped)
        digest = clean[:120]
        if len(clean) > 120:
            digest += "…"
        break

    return title, digest


def create_draft(access_token, title, content, digest=""):
    """创建公众号草稿"""
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"

    body = {
        "articles": [
            {
                "title": title,
                "content": content,
                "digest": digest,
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
            if result.get("errcode") == 0:
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

    # 创建草稿
    print("推送到草稿箱…")
    create_draft(access_token, title, content, digest)

    print("完成！打开公众号后台 → 图文消息 → 草稿箱 查看")


if __name__ == "__main__":
    main()
