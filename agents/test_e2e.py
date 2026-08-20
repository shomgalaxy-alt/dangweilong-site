#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端集成测试（使用 Mock LLM，不消耗真实 API）
==============================================
验证"生成→发布→监控→周报"完整链路可运行。

用法：LLM_MOCK=1 python3 agents/test_e2e.py
"""

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

TEST_DATE = "2025-08-20"  # 周三，会生成深度文


def run(cmd: list) -> int:
    print(f"\n▶ {' '.join(cmd)}")
    env = dict(os.environ)
    env["LLM_MOCK"] = "1"
    r = subprocess.run(cmd, cwd=config.BASE_DIR, env=env)
    return r.returncode


def main():
    print("=" * 60)
    print("端到端测试：内容生成 → 发布 → 监控 → 周报（LLM_MOCK=1）")
    print("=" * 60)

    # 清理测试日期数据
    for d in [config.CONTENT_DIR / TEST_DATE, config.DRAFTS_DIR / TEST_DATE]:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    for f in [config.MONITOR_DIR / f"{TEST_DATE}.json",
              config.REPORTS_DIR / f"周报-{TEST_DATE}.html"]:
        f.unlink(missing_ok=True)
    (config.CONTENT_DIR / TEST_DATE).mkdir(parents=True, exist_ok=True)

    # 1. 内容生成
    rc = run([sys.executable, "agents/content_agent.py", "--date", TEST_DATE])
    assert rc == 0, "内容生成失败"
    files = sorted((config.CONTENT_DIR / TEST_DATE).glob("*.md"))
    print(f"✅ 产出 {len(files)} 个文件: {[f.name for f in files]}")
    assert files, "内容未生成"

    # 2. 发布
    rc = run([sys.executable, "agents/publisher_agent.py", "--date", TEST_DATE])
    assert rc == 0, "发布失败"
    pages = list((config.WWW_DIR / "articles" / "2025" / "08").glob("*.html"))
    assert pages, "网站页面未生成"
    print(f"✅ 网站页面: {[p.name for p in pages]}")
    drafts = list((config.DRAFTS_DIR / TEST_DATE).glob("*.md"))
    assert drafts, "平台草稿未生成"
    print(f"✅ 平台草稿 {len(drafts)} 份")

    # 3. 监控
    rc = run([sys.executable, "agents/monitor_agent.py", "--date", TEST_DATE])
    assert rc == 0, "监控失败"
    monitor_file = config.MONITOR_DIR / f"{TEST_DATE}.json"
    assert monitor_file.exists(), "监控结果未存档"
    record = json.loads(monitor_file.read_text(encoding="utf-8"))
    overall = record.get("overall", {})
    rate = overall.get("overall_rate", 0)
    print(f"✅ 监控记录: 综合命中率 {rate*100:.0f}% | "
          f"引擎数 {overall.get('engines_configured', 0)}")

    # 4. 周报
    rc = run([sys.executable, "agents/report_agent.py", "--week-end", TEST_DATE])
    assert rc == 0, "周报失败"
    report = config.REPORTS_DIR / f"周报-{TEST_DATE}.html"
    assert report.exists(), "周报未生成"
    print(f"✅ 周报生成: {report.name}")

    print("\n" + "=" * 60)
    print("🎉 端到端测试全部通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
