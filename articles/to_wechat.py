#!/usr/bin/env python3
"""
Markdown → 微信公众号 HTML 转换器
用法: python3 to_wechat.py <文章.md>
输出: 复制 HTML 到微信公众号编辑器的"源代码"模式即可
"""

import sys
import re
import html


def render_paragraph(text):
    """渲染段落，处理加粗和行内样式"""
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return text


def md_to_wechat(md_text):
    """将 Markdown 文本转为微信公众号兼容 HTML"""
    lines = md_text.split('\n')
    out = []
    in_code_block = False
    code_lines = []

    for line in lines:
        # 代码块
        if line.strip().startswith('```'):
            if in_code_block:
                code_html = '<pre style="background:#f5f5f5;padding:12px;border-radius:4px;font-size:13px;overflow-x:auto;line-height:1.6;color:#333;">' + '\n'.join(code_lines) + '</pre>'
                out.append(code_html)
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # 空行
        if not line.strip():
            out.append('<br/>')
            continue

        # 分隔线
        if line.strip() == '---':
            out.append('<hr style="border:none;border-top:1px solid #e5e5e5;margin:24px 0;"/>')
            continue

        # 标题
        if line.startswith('# '):
            out.append(f'<h1 style="font-size:20px;font-weight:bold;color:#333;margin:24px 0 12px;line-height:1.4;">{render_paragraph(line[2:])}</h1>')
            continue
        if line.startswith('## '):
            out.append(f'<h2 style="font-size:18px;font-weight:bold;color:#333;margin:20px 0 10px;line-height:1.4;">{render_paragraph(line[3:])}</h2>')
            continue
        if line.startswith('### '):
            out.append(f'<h3 style="font-size:16px;font-weight:bold;color:#333;margin:16px 0 8px;line-height:1.4;">{render_paragraph(line[4:])}</h3>')
            continue

        # 列表项
        if re.match(r'^- ', line):
            out.append(f'<p style="font-size:15px;color:#3f3f3f;line-height:1.75;margin:4px 0 4px 16px;">· {render_paragraph(line[2:])}</p>')
            continue

        # 引用
        if line.startswith('> '):
            out.append(f'<blockquote style="border-left:3px solid #ddd;padding:8px 12px;margin:12px 0;color:#666;font-size:14px;background:#f9f9f9;">{render_paragraph(line[2:])}</blockquote>')
            continue

        # 普通段落
        out.append(f'<p style="font-size:15px;color:#3f3f3f;line-height:1.75;margin:0 0 12px;">{render_paragraph(line)}</p>')

    # 处理未闭合的代码块
    if in_code_block and code_lines:
        code_html = '<pre style="background:#f5f5f5;padding:12px;border-radius:4px;font-size:13px;overflow-x:auto;line-height:1.6;color:#333;">' + '\n'.join(code_lines) + '</pre>'
        out.append(code_html)

    body = '\n'.join(out)

    html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="max-width:677px;margin:0 auto;padding:16px 10px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;">
{body}
</body>
</html>"""

    return html_template


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 to_wechat.py <文章.md>")
        print("输出: HTML 文本，复制到公众号编辑器源代码模式")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, 'r') as f:
        md = f.read()

    result = md_to_wechat(md)
    output_path = path.replace('.md', '_wechat.html')
    with open(output_path, 'w') as f:
        f.write(result)

    print(f"已生成: {output_path}")
    print("打开后复制全部 HTML，粘贴到微信公众号编辑器 → 源代码模式")
