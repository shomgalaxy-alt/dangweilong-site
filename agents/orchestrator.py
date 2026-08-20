# -*- coding: utf-8 -*-
"""
主控编排器（orchestrator）
=========================
每日 cron 入口：启动"指挥官"智能体，由指挥官制定任务计划并分派执行。

架构：
  orchestrator（本文件，cron 入口）
      └──► commander_agent（指挥官：收集情报→LLM决策→分派）
              ├── content_agent   （内容生成）
              ├── publisher_agent （发布）
              └── monitor_agent   （监控）

运行：python3 agents/orchestrator.py
     （配合 cron：0 8 * * * cd /root/dwl && python3 agents/orchestrator.py >> logs/cron.log 2>&1）
"""

import datetime
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
AGENTS_DIR = Path(__file__).resolve().parent


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args()

    today = args.date
    print(f"🚀 GEO 自动化编排开始 | {today}")

    # 启动指挥官（决策 + 调度）
    cmd = [sys.executable, str(AGENTS_DIR / "commander_agent.py"), "--date", today]
    r = subprocess.run(cmd, cwd=BASE_DIR)

    if r.returncode != 0:
        print(f"⚠ 指挥官运行异常（退出码 {r.returncode}）")
        sys.exit(r.returncode)

    print(f"\n🏁 今日编排完成 | {today}")


if __name__ == "__main__":
    main()
