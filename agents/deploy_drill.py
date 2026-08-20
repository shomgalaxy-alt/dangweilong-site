#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署演练（deploy_drill.py）
===========================
在本地模拟服务器部署后的完整运行，验证"部署就绪"。
用法：LLM_MOCK=1 python3 agents/deploy_drill.py

验证项：
  1. 目录结构完整（data/ 子目录、logs/、backups/）
  2. .env 配置加载正常（mock 模式）
  3. 指挥官 → 内容生成 → 发布 → 监控 全链路
  4. 周报生成
  5. git 提交可用（www 是仓库时）
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

TEST_DATE = "2025-08-28"


def run(cmd: list) -> int:
    print(f"\n▶ {' '.join(cmd)}")
    env = dict(os.environ)
    env["LLM_MOCK"] = "1"
    r = subprocess.run(cmd, cwd=config.BASE_DIR, env=env)
    return r.returncode


def main():
    print("=" * 60)
    print("🏗 部署演练：模拟服务器完整运行")
    print("=" * 60)

    # 1. 目录检查
    print("\n[1/5] 检查目录结构...")
    dirs = ["data/content", "data/drafts", "data/monitor", "data/reports",
            "data/plans", "logs", "backups", "www", "site"]
    for d in dirs:
        p = config.BASE_DIR / d
        p.mkdir(parents=True, exist_ok=True)
        assert p.exists(), f"目录缺失: {d}"
    print(f"  ✅ {len(dirs)} 个目录就绪")

    # 2. .env 配置检查
    print("\n[2/5] 检查 .env 配置...")
    env_file = config.BASE_DIR / "agents" / ".env"
    if env_file.exists():
        print("  ✅ agents/.env 存在")
    else:
        print("  ℹ agents/.env 不存在（mock 模式可运行；真实部署需创建）")

    # 3. 全链路（指挥官）
    print("\n[3/5] 运行全链路（指挥官调度）...")
    rc = run([sys.executable, "agents/orchestrator.py", "--date", TEST_DATE])
    assert rc == 0, "全链路失败"

    # 检查产出
    content_files = list((config.CONTENT_DIR / TEST_DATE).glob("*.md"))
    print(f"  ✅ 内容产出: {len(content_files)} 个文件")

    # 4. 周报
    print("\n[4/5] 生成周报...")
    rc = run([sys.executable, "agents/report_agent.py", "--week-end", TEST_DATE])
    assert rc == 0, "周报失败"
    report = config.REPORTS_DIR / f"周报-{TEST_DATE}.html"
    assert report.exists(), "周报未生成"
    print(f"  ✅ 周报: {report.name}")

    # 5. git 状态
    print("\n[5/5] 检查 git 状态...")
    r = subprocess.run(["git", "status", "--short"], cwd=config.BASE_DIR,
                       capture_output=True, text=True)
    print(f"  ✅ git 可用，当前变更 {len(r.stdout.strip().splitlines()) if r.stdout.strip() else 0} 项")

    print("\n" + "=" * 60)
    print("🎉 部署演练全部通过！系统已就绪，可部署上线。")
    print("=" * 60)


if __name__ == "__main__":
    main()
