# -*- coding: utf-8 -*-
"""
② 发布智能体（publisher_agent）
================================
职责：
  A. 网站发布：把当日生成的深度文转成 HTML 页面，更新文章列表、sitemap，
     并尝试 git 提交（若 www/ 是 git 仓库则自动 push）
  B. 平台草稿：把内容转成知乎/公众号/小红书/即刻专属格式草稿

产出：
  - www/ 网站文件
  - data/drafts/YYYY-MM-DD/ 各平台草稿
运行：python3 agents/publisher_agent.py [--date 2025-08-19]
"""

import argparse
import datetime
import html
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config


# ---------------------------------------------------------------
# Markdown 极简渲染（够用即可；避免引入第三方依赖）
# ---------------------------------------------------------------
def md_to_html(md_text: str) -> str:
    lines = md_text.splitlines()
    out = []
    in_list = False
    in_quote = False
    for ln in lines:
        s = ln.strip()
        if not s:
            if in_list:
                out.append("</ul>")
                in_list = False
            if in_quote:
                out.append("</blockquote>")
                in_quote = False
            continue
        if s.startswith("### "):
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<h3>{escape_inline(s[4:])}</h3>")
        elif s.startswith("## "):
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<h2>{escape_inline(s[3:])}</h2>")
        elif s.startswith("# "):
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<h1>{escape_inline(s[2:])}</h1>")
        elif s.startswith("> "):
            if not in_quote:
                out.append("<blockquote>")
                in_quote = True
            out.append(f"<p>{escape_inline(s[2:])}</p>")
        elif re.match(r"^\d+\.\s", s):
            if not in_list:
                out.append("<ol>")
                in_list = True
            cleaned = re.sub(r"^\d+\.\s", "", s)
            out.append(f"<li>{escape_inline(cleaned)}</li>")
        elif s.startswith("- ") or s.startswith("* "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{escape_inline(s[2:])}</li>")
        elif s.startswith("---"):
            if in_list: out.append("</ul>"); in_list = False
            out.append("<hr>")
        else:
            if in_list: out.append("</ul>"); in_list = False
            if in_quote: out.append("</blockquote>"); in_quote = False
            out.append(f"<p>{escape_inline(s)}</p>")
    if in_list:
        out.append("</ul>")
    if in_quote:
        out.append("</blockquote>")
    return "\n".join(out)


def escape_inline(text: str) -> str:
    """行内格式：**粗体** -> <strong>；[text](url) -> 链接。"""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text


# ---------------------------------------------------------------
# A. 网站发布
# ---------------------------------------------------------------
ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - 党伟隆</title>
  <meta name="description" content="{desc}">
  <meta name="author" content="党伟隆">
  <link rel="canonical" href="{canonical}">
  <link rel="stylesheet" href="{css_rel}">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title}",
    "datePublished": "{date}",
    "dateModified": "{date}",
    "author": {{
      "@type": "Person",
      "name": "党伟隆",
      "jobTitle": "产品经理 / AI运营专家",
      "url": "https://dangweilong.com/"
    }},
    "articleSection": "AI运营与教育落地",
    "inLanguage": "zh-CN"
  }}
  </script>
</head>
<body>
  <header class="site-header">
    <div class="container">
      <nav class="nav">
        <a href="{home_rel}" class="brand">党伟隆</a>
        <div class="nav-links">
          <a href="{home_rel}">首页</a>
          <a href="{about_rel}">关于我</a>
          <a href="{articles_rel}">观点与文章</a>
        </div>
      </nav>
    </div>
  </header>
  <main class="article-body">
    <article>
      {content}
      <h2>关于作者</h2>
      <p>{signature}</p>
    </article>
  </main>
  <footer class="site-footer">
    <div class="container">
      <p>© <span id="year"></span> 党伟隆 · 产品经理 / AI运营专家 / 在线教育AI落地专家</p>
    </div>
  </footer>
  <script>document.getElementById('year').textContent = new Date().getFullYear();</script>
</body>
</html>
"""


def publish_article_to_site(md_path: Path):
    """把一篇 Markdown 文章转成网站 HTML 并写入 www/articles/。返回 URL 路径。"""
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 解析标题（第一个 # 行，跳过元信息）
    title = ""
    body_lines = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("# ") and not title:
            title = s[2:].strip()
        elif s.startswith("> 生成日期") or s.startswith("> 类型"):
            continue
        else:
            body_lines.append(ln)
    if not title:
        title = md_path.stem

    date_str = md_path.stem[:10]
    year, month = date_str[:4], date_str[5:7]
    slug = md_path.stem.replace(f"{date_str}-", "").replace(".md", "")

    rel_dir = f"articles/{year}/{month}"
    dest = config.WWW_DIR / rel_dir / f"{slug}.html"
    dest.parent.mkdir(parents=True, exist_ok=True)

    depth = len(rel_dir.split("/"))
    css_rel = "/".join([".."] * depth) + "/css/style.css"
    home_rel = "/".join([".."] * depth) or "."
    about_rel = f"{home_rel}/about.html"
    articles_rel = f"{home_rel}/articles/"

    content_html = md_to_html("\n".join(body_lines))
    # 去掉生成文件的署名占位，用真实署名
    content_html = content_html.replace("<p>{SIGNATURE}</p>", "")

    page = ARTICLE_TEMPLATE.format(
        title=html.escape(title),
        desc=html.escape(f"{title} - 党伟隆关于AI运营与在线教育AI落地的专业观点。", quote=True),
        canonical=f"https://dangweilong.com/{rel_dir}/{slug}.html",
        css_rel=css_rel,
        date=date_str,
        home_rel=home_rel,
        about_rel=about_rel,
        articles_rel=articles_rel,
        content=content_html,
        signature=config.PERSONA["signature"],
    )
    dest.write_text(page, encoding="utf-8")
    print(f"  ✅ 网站页面: {dest.relative_to(config.BASE_DIR)}")
    return f"/{rel_dir}/{slug}.html"


def update_article_list(url: str, title: str, date_str: str):
    """在 www/articles/index.html 列表顶部插入新文章条目。"""
    list_file = config.WWW_DIR / "articles" / "index.html"
    if not list_file.exists():
        print("  ⚠ 找不到文章列表页，跳过列表更新")
        return
    text = list_file.read_text(encoding="utf-8")
    item = (
        f'<div class="article-item">\n'
        f'            <h3><a href="{url}">{html.escape(title)}</a></h3>\n'
        f'            <p class="article-meta">{date_str} · AI运营与教育落地</p>\n'
        f"          </div>\n"
        f"          <!-- 文章条目：每发布一篇，复制此模板追加到列表，并创建对应 HTML 文件 -->"
    )
    if "<!-- 文章条目" in text:
        text = text.replace("<!-- 文章条目", item, 1)
    else:
        text = text.replace('<div class="article-list">', f'<div class="article-list">\n{item}', 1)
    list_file.write_text(text, encoding="utf-8")
    print("  ✅ 文章列表已更新")


def update_sitemap(url: str, date_str: str):
    """向 www/sitemap.xml 追加新 URL 条目。"""
    sitemap = config.WWW_DIR / "sitemap.xml"
    if not sitemap.exists():
        return
    text = sitemap.read_text(encoding="utf-8")
    entry = (
        f'  <url>\n'
        f'    <loc>https://dangweilong.com{url}</loc>\n'
        f'    <lastmod>{date_str}</lastmod>\n'
        f'    <changefreq>monthly</changefreq>\n'
        f'    <priority>0.7</priority>\n'
        f"  </url>\n"
        f"</urlset>"
    )
    text = text.replace("</urlset>", entry, 1)
    sitemap.write_text(text, encoding="utf-8")
    print("  ✅ sitemap 已更新")


def git_commit_and_push(message: str):
    """若 www/ 是 git 仓库，自动提交并推送。"""
    try:
        r = subprocess.run(
            ["git", "-C", str(config.WWW_DIR), "add", "-A"],
            capture_output=True, text=True, timeout=30,
        )
        r = subprocess.run(
            ["git", "-C", str(config.WWW_DIR), "commit", "-m", message],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            subprocess.run(
                ["git", "-C", str(config.WWW_DIR), "push"],
                capture_output=True, text=True, timeout=60,
            )
            print("  ✅ 已提交并推送网站更新")
        else:
            print("  ℹ 无变更或提交跳过（非错误）")
    except Exception as e:
        print(f"  ⚠ git 操作失败（可手动处理）: {e}")


# ---------------------------------------------------------------
# B. 平台草稿生成
# ---------------------------------------------------------------
def gen_platform_drafts(content_dir: Path, drafts_dir: Path):
    """把当日所有内容转成各平台草稿。"""
    drafts_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(content_dir.glob("*.md"))

    for f in files:
        text = f.read_text(encoding="utf-8")
        kind = "短评" if "-note-" in f.name else ("问答" if "-qa-" in f.name else "文章")
        title = ""
        for ln in text.splitlines():
            if ln.strip().startswith("# "):
                title = ln.strip()[2:].strip()
                break
        title = title or f.name

        # 知乎草稿
        (drafts_dir / f"zhihu-{f.name}").write_text(
            f"【知乎草稿】\n标题：{title}\n\n正文：\n{strip_meta(text)}\n\n发布提示：复制到知乎发布，选择合适话题标签（AI/产品经理/在线教育）。",
            encoding="utf-8",
        )
        # 公众号草稿
        (drafts_dir / f"wechat-{f.name}").write_text(
            f"【公众号草稿】\n标题：{title}\n\n正文（含 Markdown 排版，粘贴到公众号编辑器选“Markdown 模式”或转换）：\n{strip_meta(text)}\n\n发布提示：登录公众号后台→新建图文→粘贴→插入封面图→群发。",
            encoding="utf-8",
        )
        # 小红书草稿（短评和文章都适配）
        xhs_body = "\n".join(
            [f"💡 {title}"] + [ln for ln in strip_meta(text).splitlines() if ln.strip()][:12]
        )
        (drafts_dir / f"xiaohongshu-{f.name}").write_text(
            f"【小红书草稿】\n{xhs_body}\n\n#AI运营 #产品经理 #在线教育 #AI落地\n\n发布提示：标题≤20字，正文加 emoji 分段，配 3 张图。",
            encoding="utf-8",
        )

    print(f"  ✅ 平台草稿生成: {drafts_dir.relative_to(config.BASE_DIR)} 共 {len(files)} 个内容源")


def strip_meta(text: str) -> str:
    """去掉 Markdown 元信息行（# 标题和 > 生成日期行保留正文）。"""
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("> 生成日期") or s.startswith("> 类型"):
            continue
        lines.append(ln)
    return "\n".join(lines)


# ---------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args()

    today = args.date
    content_dir = config.CONTENT_DIR / today
    drafts_dir = config.DRAFTS_DIR / today

    if not content_dir.exists():
        print(f"⚠ 没有找到 {today} 的内容目录，跳过发布")
        return

    print(f"📤 发布智能体 | 日期 {today}")

    # 1. 网站发布（仅文章）
    articles = sorted(content_dir.glob("*-article.md"))
    if articles:
        for art in articles:
            url = publish_article_to_site(art)
            if url:
                title = art.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
                update_article_list(url, title, today)
                update_sitemap(url, today)
        git_commit_and_push(f"auto: 发布 {today} 内容")
    else:
        print("  ⏭ 今日无深度文章，跳过网站发布")

    # 2. 平台草稿
    gen_platform_drafts(content_dir, drafts_dir)


if __name__ == "__main__":
    main()
