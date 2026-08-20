# -*- coding: utf-8 -*-
"""
④ 周报智能体（report_agent）
============================
职责：汇总本周运营数据（内容产量 + AI 可见度 + 待办），生成网页周报。

产出：data/reports/周报-YYYY-MM-DD.html（可打开网页查看）
运行：python3 agents/report_agent.py [--week-end 2025-08-24]
"""

import argparse
import datetime
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config


def last_7_days(end_date: datetime.date) -> list:
    return [end_date - datetime.timedelta(days=i) for i in range(6, -1, -1)]


def collect_content_stats(days: list) -> dict:
    """统计本周内容产量。"""
    articles = notes = qa = 0
    files_list = []
    for d in days:
        dstr = d.isoformat()
        cdir = config.CONTENT_DIR / dstr
        if cdir.exists():
            for f in cdir.glob("*.md"):
                files_list.append(f.name)
                if "-article" in f.name:
                    articles += 1
                elif "-note-" in f.name:
                    notes += 1
                elif "-qa-" in f.name:
                    qa += 1
    return {"articles": articles, "notes": notes, "qa": qa, "files": files_list}


def collect_monitor_stats(days: list) -> dict:
    """统计本周 AI 可见度（多引擎版）。"""
    trend_file = config.MONITOR_DIR / "trend.json"
    records = []
    if trend_file.exists():
        trend = json.loads(trend_file.read_text(encoding="utf-8"))
        dates = {d.isoformat() for d in days}
        records = [t for t in trend if t["date"] in dates]

    if not records:
        return {"runs": 0, "best_rate": 0, "latest_rate": 0, "latest_date": None,
                "engine_stats": {}}

    latest = records[-1]
    best = max(r.get("overall_rate", 0) for r in records)

    # 汇总各引擎本周表现（取最新记录）
    engine_stats = {}
    for r in records:
        for e in r.get("engines", []):
            app = e["app"]
            if app not in engine_stats or e["hit_rate"] > engine_stats[app]["hit_rate"]:
                engine_stats[app] = {
                    "name": e["name"], "hit_rate": e["hit_rate"],
                    "hits": e["hits"], "total": e["total"],
                }

    return {
        "runs": len(records),
        "best_rate": best,
        "latest_rate": latest.get("overall_rate", 0),
        "latest_date": latest["date"],
        "engine_stats": engine_stats,
        "series": [{"date": r["date"], "rate": r.get("overall_rate", 0)} for r in records],
    }


def collect_drafts(days: list) -> int:
    """统计本周生成的平台草稿数。"""
    total = 0
    for d in days:
        ddir = config.DRAFTS_DIR / d.isoformat()
        if ddir.exists():
            total += len(list(ddir.glob("*.md")))
    return total


def render_report(end_date: datetime.date) -> str:
    days = last_7_days(end_date)
    content = collect_content_stats(days)
    monitor = collect_monitor_stats(days)
    drafts = collect_drafts(days)

    week_start = days[0].isoformat()
    week_end = days[-1].isoformat()

    # 可见度状态条
    rate = monitor["latest_rate"]
    if rate >= 0.5:
        level = "🟢 优秀"
    elif rate >= 0.2:
        level = "🟡 有进展"
    elif rate > 0:
        level = "🟠 刚开始"
    else:
        level = "🔴 尚未命中"
    rate_pct = f"{rate*100:.0f}%" if rate else "0%"

    # 内容产量卡片
    files_html = ""
    for f in content["files"]:
        files_html += f"<li>{html.escape(f)}</li>"
    if not files_html:
        files_html = "<li>本周暂无内容产出</li>"

    # 待办
    todos = []
    if drafts > 0:
        todos.append(f"📤 有 {drafts} 份平台草稿待手动发布（data/drafts/ 目录）")
    if monitor["runs"] == 0:
        todos.append("👁 监控未运行，请检查各引擎 API Key 配置")
    if content["articles"] == 0:
        todos.append("✍️ 本周无深度文章，建议补充 1 篇")
    # 分引擎待办：未配置的引擎提醒
    for app in ("deepseek", "doubao", "qwen", "hunyuan"):
        if app not in monitor["engine_stats"]:
            name_map = {"deepseek": "DeepSeek", "doubao": "豆包", "qwen": "通义千问", "hunyuan": "腾讯元宝"}
            todos.append(f"🔧 引擎「{name_map[app]}」未配置 API Key，无法监控")
    todos_html = "".join(f"<li>{html.escape(t)}</li>" for t in todos) or "<li>无待办，本周全部完成 ✅</li>"

    # 分引擎命中率表格
    engine_rows = ""
    for app, st in monitor["engine_stats"].items():
        bar_w = max(int(st["hit_rate"] * 100), 2)

    # 命中率趋势折线图（内联 SVG，无外部依赖）
    series = monitor.get("series", [])
    svg_chart = ""
    if len(series) >= 2:
        W, H = 600, 160
        pad_l, pad_r, pad_t, pad_b = 30, 10, 12, 24
        plot_w, plot_h = W - pad_l - pad_r, H - pad_t - pad_b
        max_rate = max(max(s["rate"] for s in series), 0.1)
        def px(s):
            x = pad_l + (s["rate"] / max_rate) * plot_w
            y = pad_t + plot_h - (s["rate"] / max_rate) * plot_h
            return x, y
        points = " ".join(f"{px(s)[0]:.1f},{px(s)[1]:.1f}" for s in series)
        # 网格线（0%, 50%, 100%）
        grid = ""
        for g in (0.0, 0.5, 1.0):
            gy = pad_t + plot_h - g * plot_h
            grid += f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{W-pad_r}" y2="{gy:.1f}" stroke="#eef2f7" stroke-width="1"/>'
            grid += f'<text x="{pad_l-6}" y="{gy+4:.1f}" font-size="10" fill="#9ca3af" text-anchor="end">{int(g*100)}%</text>'
        # 数据点
        dots = ""
        for s in series:
            x, y = px(s)
            dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#2563eb"/>'
        # 日期标签（首尾 + 中间）
        labels = ""
        step = max(1, len(series) - 1)
        for i in (0, step // 2, step):
            s = series[i]
            x, y = px(s)
            labels += f'<text x="{x:.1f}" y="{H-8}" font-size="9" fill="#9ca3af" text-anchor="middle">{s["date"][5:]}</text>'
        svg_chart = f'''<svg viewBox="0 0 {W} {H}" style="max-width:100%;height:auto;background:#fff;border-radius:12px;">
  {grid}
  <polyline points="{points}" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
  {dots}
  {labels}
</svg>'''
    elif len(series) == 1:
        svg_chart = f'<p class="sub">已记录 {len(series)} 次监控（{series[0]["date"]}，综合命中率 {series[0]["rate"]*100:.0f}%），持续运行后将生成趋势图</p>'
    else:
        svg_chart = '<p class="sub">暂无监控数据，配置 API Key 后自动生成趋势图</p>'
        engine_rows += (
            f"<tr><td>{html.escape(st['name'])}</td>"
            f"<td>{st['hit_rate']*100:.0f}% ({st['hits']}/{st['total']})</td>"
            f"<td><div class='bar'><div class='bar-fill' style='width:{bar_w}%'></div></div></td></tr>"
        )
    if not engine_rows:
        engine_rows = "<tr><td colspan='3'>暂无监控数据</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GEO 运营周报 {week_end} - 党伟隆</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 0; background: #f5f7fa; color: #1f2937; }}
  .wrap {{ max-width: 860px; margin: 0 auto; padding: 24px 16px 60px; }}
  h1 {{ font-size: 1.6rem; }}
  .date {{ color: #6b7280; font-size: 0.9rem; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin: 20px 0; }}
  .card {{ background: #fff; border-radius: 12px; padding: 18px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }}
  .card h3 {{ margin: 0 0 8px; font-size: 0.9rem; color: #6b7280; }}
  .card .num {{ font-size: 1.9rem; font-weight: 700; color: #2563eb; }}
  .card .sub {{ font-size: 0.8rem; color: #9ca3af; }}
  .level {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.9rem; font-weight: 600; background: #f3f4f6; }}
  h2 {{ font-size: 1.15rem; margin-top: 28px; }}
  ul {{ line-height: 1.8; }}
  .todo {{ background: #fff7ed; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 0 8px 8px 0; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.06); }}
  th, td {{ padding: 10px 14px; text-align: left; font-size: 0.9rem; }}
  th {{ background: #f3f4f6; }}
  td {{ border-top: 1px solid #f3f4f6; }}
  .bar {{ background: #e5e7eb; border-radius: 8px; height: 10px; width: 120px; }}
  .bar-fill {{ background: #2563eb; border-radius: 8px; height: 10px; }}
  footer {{ margin-top: 40px; color: #9ca3af; font-size: 0.8rem; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>📊 GEO 运营周报</h1>
  <p class="date">{week_start} ~ {week_end} · 自动生成</p>

  <div class="grid">
    <div class="card"><h3>AI 可见度（最近一次）</h3><div class="num">{rate_pct}</div><div class="sub"><span class="level">{level}</span></div></div>
    <div class="card"><h3>本周深度文章</h3><div class="num">{content['articles']}</div><div class="sub">累计内容源 {len(content['files'])}</div></div>
    <div class="card"><h3>本周短评</h3><div class="num">{content['notes']}</div></div>
    <div class="card"><h3>本周问答</h3><div class="num">{content['qa']}</div></div>
  </div>

  <h2>📈 说明</h2>
  <ul>
    <li>综合可见度 = 各引擎回答监控问题时提到"党伟隆"的平均比例（监控共 {monitor['runs']} 次运行）</li>
    <li>本周最好综合命中率 {monitor['best_rate']*100:.0f}%{('（' + monitor['latest_date'] + '）') if monitor['latest_date'] else ''}</li>
    <li>平台草稿 {drafts} 份已生成（知乎/公众号/小红书）</li>
  </ul>

  <h2>📈 综合命中率趋势</h2>
  {svg_chart}

  <h2>🤖 分引擎 AI 可见度（最近一次）</h2>
  <table>
    <tr><th>引擎</th><th>命中率</th><th>趋势</th></tr>
    {engine_rows}
  </table>

  <h2>📝 本周产出明细</h2>
  <ul>{files_html}</ul>

  <h2>✅ 下周待办</h2>
  <div class="todo"><ul>{todos_html}</ul></div>

  <footer>党伟隆个人GEO自动化系统 · 周报由 report_agent 自动生成</footer>
</div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--week-end", default=datetime.date.today().isoformat())
    args = parser.parse_args()
    end_date = datetime.date.fromisoformat(args.week_end)

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.REPORTS_DIR / f"周报-{end_date.isoformat()}.html"
    out.write_text(render_report(end_date), encoding="utf-8")
    print(f"📄 周报已生成: {out.relative_to(config.BASE_DIR)}")
    print("   在浏览器打开即可查看。")


if __name__ == "__main__":
    main()
