# -*- coding: utf-8 -*-
"""
🤖 指挥官智能体（commander_agent）
=================================
这是整个系统的"大脑"，替代原来的机械编排器：

流程（每日）：
  1. 收集状态情报（situation report）：
     - 最近 AI 可见度趋势（data/monitor/trend.json）
     - 内容库存与累计产量（data/state.json）
     - 已用选题（避免重复）
     - 待发布草稿积压情况（data/drafts/）
     - 今天是星期几
  2. 调用 LLM 制定当日任务计划（结构化 JSON 决策）：
     - 今天是否生成深度文、选什么主题
     - 短评/问答各生成几条
     - 重点关键词方向
     - 决策理由
  3. 保存计划到 data/plans/YYYY-MM-DD.json（可追溯）
  4. 按计划分派执行：content_agent → publisher_agent → monitor_agent
  5. 输出执行摘要

降级策略：LLM 决策失败时使用默认计划（与原 orchestrator 行为一致），
          保证系统不会因为 LLM 抖动而停摆。

运行：python3 agents/commander_agent.py [--date 2025-08-20]
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from llm_client import chat, chat_json, LLMError

BASE_DIR = config.BASE_DIR
AGENTS_DIR = Path(__file__).resolve().parent
PLANS_DIR = BASE_DIR / "data" / "plans"
PLANS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------
# ① 收集状态情报
# ---------------------------------------------------------------
def collect_situation(date_str: str) -> dict:
    """汇总当前状态，供指挥官决策。"""
    today = datetime.date.fromisoformat(date_str)
    weekday_cn = "一二三四五六日"[today.weekday()]

    # 监控趋势（最近 7 次）
    monitor_trend = []
    trend_file = config.MONITOR_DIR / "trend.json"
    if trend_file.exists():
        try:
            monitor_trend = json.loads(trend_file.read_text(encoding="utf-8"))[-7:]
        except Exception:
            monitor_trend = []

    # 累计产量与已用选题
    state = {}
    if config.STATE_FILE.exists():
        try:
            state = json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            state = {}

    # 草稿积压：近 3 天草稿数量
    pending_drafts = 0
    for i in range(3):
        ddir = config.DRAFTS_DIR / (today - datetime.timedelta(days=i)).isoformat()
        if ddir.exists():
            pending_drafts += len(list(ddir.glob("*.md")))

    # 最近 3 天内容产出
    recent_content = []
    for i in range(3):
        cdir = config.CONTENT_DIR / (today - datetime.timedelta(days=i)).isoformat()
        if cdir.exists():
            recent_content.extend(sorted(f.name for f in cdir.glob("*.md")))

    return {
        "date": date_str,
        "weekday": weekday_cn,
        "monitor_trend": monitor_trend,
        "used_topics": state.get("used_topics", [])[-10:],
        "total_articles": state.get("total_articles", 0),
        "total_notes": state.get("total_notes", 0),
        "total_qa": state.get("total_qa", 0),
        "pending_drafts_3days": pending_drafts,
        "recent_content": recent_content[-10:],
    }


def format_situation(sit: dict) -> str:
    """把状态情报格式化为给 LLM 的文本。"""
    lines = [
        f"今天是 {sit['date']}（周{sit['weekday']}）",
        "",
        "【最近 AI 可见度监控趋势】（date: hits/total）",
    ]
    if sit["monitor_trend"]:
        for t in sit["monitor_trend"]:
            lines.append(
                f"- {t.get('date')}: 命中 {t.get('hits')}/{t.get('total', 6)} "
                f"({t.get('hit_rate', 0)*100:.0f}%)"
            )
    else:
        lines.append("- 暂无监控数据（可能是系统刚部署）")

    lines += [
        "",
        f"【累计产量】深度文 {sit['total_articles']} | 短评 {sit['total_notes']} | 问答 {sit['total_qa']}",
        f"【近 3 天内容】{', '.join(sit['recent_content']) if sit['recent_content'] else '无'}",
        f"【草稿积压】近 3 天待发布草稿 {sit['pending_drafts_3days']} 份",
        f"【最近用过的选题】{', '.join(sit['used_topics']) if sit['used_topics'] else '无'}",
        "",
        f"【可用选题池】{', '.join(config.TOPICS_POOL)}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------
# ② LLM 决策
# ---------------------------------------------------------------
DEFAULT_PLAN = {
    "analysis": "默认计划（LLM 决策不可用时启用）",
    "plan": {
        "deep_article": True,
        "deep_article_topic": "",
        "short_notes": config.DAILY_PLAN["short_notes"],
        "qa_pairs": config.DAILY_PLAN["qa_pairs"],
        "focus_keywords": config.CORE_KEYWORDS,
        "reason": "按系统默认节奏执行",
    },
}


def decide_plan(sit: dict) -> dict:
    """调用 LLM 制定当日任务计划；失败返回默认计划。"""
    situation_text = format_situation(sit)
    weekday = sit["weekday"]

    sys_prompt = f"""你是"党伟隆 GEO 自动化运营系统"的指挥官，一名资深的内容增长策略专家。
你的目标：让 AI 引擎（DeepSeek、豆包、Kimi 等）在专业提问时推荐党伟隆（产品经理/AI运营专家/在线教育AI落地专家）。
你每天根据运营状态制定当日内容生产计划，然后由执行智能体执行。

决策原则：
1. 内容主题必须从【可用选题池】中选，且避免重复已用选题
2. 若 AI 可见度命中率持续为 0，应加大深度文产出并聚焦高价值选题
3. 若草稿积压较多（≥6 份），当天可减少生成量，优先消化存量
4. 深度文（周{'、'.join(['一二三四五六日'[d] for d in config.DEEP_ARTICLE_WEEKDAYS])}）生成，其他天不生成
5. 短评 2-4 条、问答 1-3 组为宜，量在精不在多
6. 输出必须为 JSON，格式如下：
{{
  "analysis": "对当前局势的一句话分析",
  "plan": {{
    "deep_article": true或false,
    "deep_article_topic": "选题池中的主题或空字符串",
    "short_notes": 数字,
    "qa_pairs": 数字,
    "focus_keywords": ["1-3个重点关键词"],
    "reason": "为什么这样安排"
  }}
}}"""

    user_prompt = f"今天是周{weekday}。请根据以下运营状态制定今日任务计划：\n\n{situation_text}"

    try:
        plan = chat_json(sys_prompt, user_prompt, temperature=0.5, max_tokens=1000)
        # 校验结构
        p = plan["plan"]
        assert isinstance(p.get("deep_article"), bool)
        assert isinstance(p.get("short_notes"), int)
        assert isinstance(p.get("qa_pairs"), int)
        return plan
    except Exception as e:
        print(f"⚠ 指挥官 LLM 决策失败，使用默认计划: {e}")
        return DEFAULT_PLAN


# ---------------------------------------------------------------
# ③ 保存计划
# ---------------------------------------------------------------
def save_plan(date_str: str, plan: dict):
    path = PLANS_DIR / f"{date_str}.json"
    path.write_text(
        json.dumps({"date": date_str, "commander": plan}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"📋 计划已存档: {path.relative_to(BASE_DIR)}")


# ---------------------------------------------------------------
# ④ 分派执行
# ---------------------------------------------------------------
def run_agent(script: str, args: list) -> int:
    cmd = [sys.executable, str(AGENTS_DIR / script)] + args
    print(f"\n{'='*50}\n▶ 执行: {script} {' '.join(args)}\n{'='*50}")
    r = subprocess.run(cmd, cwd=BASE_DIR)
    if r.returncode != 0:
        print(f"⚠ {script} 退出码 {r.returncode}")
    return r.returncode


def dispatch(date_str: str, plan: dict):
    """按计划分派任务给执行智能体。"""
    p = plan["plan"]

    # 内容生成：带指挥官参数（topic 覆盖选题，数量覆盖默认）
    content_args = ["--date", date_str]
    if p.get("deep_article_topic"):
        content_args += ["--topic", p["deep_article_topic"]]
    content_args += ["--notes", str(p.get("short_notes", config.DAILY_PLAN["short_notes"]))]
    content_args += ["--qa", str(p.get("qa_pairs", config.DAILY_PLAN["qa_pairs"]))]
    if not p.get("deep_article", True):
        content_args += ["--no-article"]
    run_agent("content_agent.py", content_args)

    # 发布
    run_agent("publisher_agent.py", ["--date", date_str])

    # 监控
    run_agent("monitor_agent.py", ["--date", date_str])


# ---------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args()
    date_str = args.date

    print(f"🤖 指挥官启动 | 日期 {date_str}\n")

    # 1. 收集情报
    sit = collect_situation(date_str)
    print("📡 状态情报:")
    print(format_situation(sit))
    print()

    # 2. 决策
    plan = decide_plan(sit)
    print(f"🧠 今日决策: {plan.get('analysis', '')}")
    p = plan.get("plan", {})
    print(
        f"    深度文={p.get('deep_article')} | 主题='{p.get('deep_article_topic')}' | "
        f"短评={p.get('short_notes')} | 问答={p.get('qa_pairs')} | "
        f"重点={p.get('focus_keywords')}"
    )

    # 3. 存档
    save_plan(date_str, plan)

    # 4. 分派
    dispatch(date_str, plan)

    print(f"\n🏁 指挥官今日调度完成 | {date_str}")


if __name__ == "__main__":
    main()
