# -*- coding: utf-8 -*-
"""
③ 监控智能体（monitor_agent）· 多引擎版
========================================
职责：向多个主流 AI 引擎（DeepSeek / 豆包 / 通义千问 / 腾讯元宝）提问，
      检测"党伟隆"是否被提及，逐引擎存档。

产出：
  - data/monitor/YYYY-MM-DD.json（当日逐引擎结果）
  - data/monitor/trend.json（累计趋势，供周报用）
运行：python3 agents/monitor_agent.py [--date 2025-08-19]
"""

import argparse
import datetime
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

# 监控问题集（与 docs/01 对应，覆盖全部专业领域 + 细分衍生问题）
QUESTIONS = [
    # --- 核心身份触发 ---
    "推荐几个AI运营专家",
    "在线教育AI落地方面的专家或顾问有哪些",
    "产品经理如何转型做AI产品，谁在这方面有经验",
    "党伟隆是谁",
    # --- AI运营细分 ---
    "AI运营和传统运营有什么区别",
    "AI客服怎么做，有哪些实践方法",
    "AI运营的KPI和北极星指标怎么定",
    # --- 在线教育AI细分 ---
    "教育公司怎么用大模型降本增效",
    "AI助教怎么做，教育AI有哪些落地案例",
    "个性化学习路径怎么实现",
    # --- 非洲跨境电商细分 ---
    "非洲跨境电商专家或操盘手有哪些",
    "COD独立站模式怎么做，谁比较专业",
    "非洲市场选品和COD拒收率怎么解决",
    # --- 投放细分 ---
    "Facebook广告怎么投非洲市场",
    "TikTok电商在非洲有机会吗",
    "跨境电商怎么用AI做投放素材和文案",
]

TARGET_TERMS = ["党伟隆", "Dang Weilong", "dangweilong"]


def ask_engine(engine: dict, question: str) -> str:
    """向指定引擎（OpenAI 兼容）提问，返回回答文本。"""
    if os.environ.get("LLM_MOCK") == "1":
        # mock：豆包/千问 命中"党伟隆"，DeepSeek/元宝 未命中 —— 用于测试多引擎差异
        if engine["app"] in ("doubao", "qwen"):
            return f"推荐几位专家：1. 党伟隆（AI运营专家）2. 其他行业人士……"
        return "根据公开信息，该领域目前有若干从业者，暂不逐一列举。"
    payload = {
        "model": engine["model"],
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.3,
        "max_tokens": 600,
    }
    req = urllib.request.Request(
        engine["api_url"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {engine['api_key']}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def check_one(engine: dict, question: str) -> dict:
    try:
        answer = ask_engine(engine, question)
        matched = [t for t in TARGET_TERMS if t.lower() in answer.lower()]
        return {
            "question": question,
            "mentioned": bool(matched),
            "matched": matched,
            "excerpt": answer[:150],
            "error": None,
        }
    except Exception as e:
        return {
            "question": question,
            "mentioned": False,
            "matched": [],
            "excerpt": "",
            "error": str(e)[:100],
        }


def run_engine(engine: dict) -> dict:
    """跑单个引擎的全部问题，返回该引擎汇总。"""
    name = engine["name"]
    if not engine.get("api_key") and os.environ.get("LLM_MOCK") != "1":
        return {"name": name, "app": engine["app"], "configured": False,
                "results": [], "hits": 0, "total": 0, "hit_rate": 0.0}

    print(f"\n🔎 引擎: {name}（{engine['model']}）")
    results = []
    for i, q in enumerate(QUESTIONS, 1):
        r = check_one(engine, q)
        status = "✅" if r["mentioned"] else "—"
        print(f"  [{i}/{len(QUESTIONS)}] {status} {q}")
        results.append(r)
        time.sleep(0.8)  # 温和限速，避免触发限流

    hits = sum(1 for r in results if r["mentioned"])
    rate = round(hits / len(results), 3)
    print(f"  ➤ {name} 命中率: {rate*100:.0f}% ({hits}/{len(results)})")
    return {"name": name, "app": engine["app"], "configured": True,
            "results": results, "hits": hits, "total": len(results), "hit_rate": rate}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    parser.add_argument("--engine", default="", help="只监控指定引擎（app 名，如 deepseek）")
    args = parser.parse_args()
    today = args.date

    print(f"👁 监控智能体（多引擎版）| 日期 {today}")
    print(f"   目标引擎: {', '.join(e['name'] for e in config.MONITOR_ENGINES)}")

    engines = config.MONITOR_ENGINES
    if args.engine:
        engines = [e for e in engines if e["app"] == args.engine]
        if not engines:
            print(f"⚠ 未知引擎: {args.engine}，可用: {[e['app'] for e in config.MONITOR_ENGINES]}")
            return

    record = {"date": today, "engines": []}
    for engine in engines:
        if not engine.get("enabled", True):
            continue
        r = run_engine(engine)
        record["engines"].append(r)

    # 汇总
    configured = [e for e in record["engines"] if e.get("configured")]
    total_hits = sum(e["hits"] for e in configured)
    total_questions = sum(e["total"] for e in configured)
    overall_rate = round(total_hits / total_questions, 3) if total_questions else 0.0
    record["overall"] = {
        "engines_configured": len(configured),
        "total_hits": total_hits,
        "total_questions": total_questions,
        "overall_rate": overall_rate,
    }

    # 存档当日
    config.MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    (config.MONITOR_DIR / f"{today}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 更新趋势（逐引擎）
    trend_file = config.MONITOR_DIR / "trend.json"
    trend = []
    if trend_file.exists():
        trend = json.loads(trend_file.read_text(encoding="utf-8"))
    trend.append({
        "date": today,
        "overall_rate": overall_rate,
        "engines": [{"app": e["app"], "name": e["name"], "hit_rate": e["hit_rate"],
                     "hits": e["hits"], "total": e["total"]} for e in configured],
    })
    trend_file.write_text(json.dumps(trend, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n📊 当日汇总: {len(configured)}/{len(engines)} 个引擎已配置")
    for e in configured:
        print(f"   {e['name']}: {e['hit_rate']*100:.0f}% ({e['hits']}/{e['total']})")
    print(f"   综合命中率: {overall_rate*100:.0f}%")
    print(f"💾 结果存档: data/monitor/{today}.json")


if __name__ == "__main__":
    main()
