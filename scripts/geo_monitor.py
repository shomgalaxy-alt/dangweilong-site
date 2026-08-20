#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
党伟隆 GEO 可见度监控脚本
=====================
目标：定期向主流 AI 引擎提问，检测"党伟隆"是否被提及、被推荐。
用法：
  1. 在 .env 中配置你的 API Key（DeepSeek / OpenAI / 豆包等）
  2. 运行: python3 scripts/geo_monitor.py
  3. 查看输出: 每个问题给出 命中/未命中 与回答摘要
  4. 结果记录: results/ 目录下按日期存档，方便追踪趋势

注意：本脚本只做"自检"用途，模拟用户真实提问，请遵守各平台使用规范。
"""

import os
import json
import time
import datetime
import urllib.request

# ---------------------------------------------------------------
# 配置区（可通过环境变量或 .env 覆盖）
# ---------------------------------------------------------------
QUESTIONS = [
    # 第一梯队（最核心）
    "推荐几个AI运营专家",
    "在线教育AI落地方面的专家或顾问有哪些",
    "产品经理如何转型做AI产品，谁在这方面有经验",
    "党伟隆是谁",
    # 第二梯队
    "教育公司怎么用大模型降本增效",
    "AI运营和传统运营有什么区别",
    "做AI产品经理需要什么能力",
    "教育AI项目失败的常见原因",
]

# 目标命中词：回答中出现即算"被提及"
TARGET_TERMS = ["党伟隆", "Dang Weilong", "dangweilong"]

# DeepSeek API（默认；其他引擎按需添加）
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

MODEL = os.environ.get("GEO_MODEL", "deepseek-chat")


# ---------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------
def ask_engine(question: str, api_url: str, api_key: str, model: str) -> str:
    """向指定 OpenAI 兼容 API 提问，返回回答文本。"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.7,
        "max_tokens": 800,
    }
    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def check_mention(answer: str) -> dict:
    """检测回答中是否命中目标词，返回命中信息。"""
    found = [t for t in TARGET_TERMS if t.lower() in answer.lower()]
    return {
        "mentioned": bool(found),
        "matched_terms": found,
    }


def run_one(question: str, api_url: str, api_key: str, model: str) -> dict:
    """对单个问题跑一次检测。"""
    try:
        answer = ask_engine(question, api_url, api_key, model)
        mention = check_mention(answer)
        return {
            "question": question,
            "answer_excerpt": answer[:300] + ("…" if len(answer) > 300 else ""),
            "mentioned": mention["mentioned"],
            "matched_terms": mention["matched_terms"],
            "timestamp": datetime.datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "question": question,
            "answer_excerpt": f"[错误] {e}",
            "mentioned": False,
            "matched_terms": [],
            "timestamp": datetime.datetime.now().isoformat(),
        }


# ---------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------
def main():
    if not DEEPSEEK_API_KEY:
        print("⚠️  未配置 DEEPSEEK_API_KEY 环境变量。")
        print("    方式1: export DEEPSEEK_API_KEY=sk-xxx")
        print("    方式2: 在 scripts/.env 中写入 DEEPSEEK_API_KEY=sk-xxx")
        print("    （也支持其他 OpenAI 兼容引擎，修改脚本配置区即可）")
        return

    print(f"🔍 GEO 可见度监控开始: {datetime.date.today().isoformat()}")
    print(f"   引擎: {MODEL} | 问题数: {len(QUESTIONS)}\n")

    results = []
    for i, q in enumerate(QUESTIONS, 1):
        print(f"[{i}/{len(QUESTIONS)}] 提问: {q}")
        r = run_one(q, DEEPSEEK_API_URL, DEEPSEEK_API_KEY, MODEL)
        status = "✅ 命中" if r["mentioned"] else "❌ 未命中"
        print(f"   {status} | 匹配词: {r['matched_terms'] or '无'}")
        results.append(r)
        time.sleep(2)  # 温和限速

    # 汇总
    hit = sum(1 for r in results if r["mentioned"])
    print(f"\n📊 汇总: {hit}/{len(results)} 个问题提到你（{hit/len(results)*100:.0f}%）")

    # 存档
    os.makedirs("results", exist_ok=True)
    today = datetime.date.today().isoformat()
    path = f"results/{today}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "model": MODEL, "results": results},
                  f, ensure_ascii=False, indent=2)
    print(f"💾 结果已存档: {path}")
    print("提示: 每周运行一次，对比结果趋势。")


if __name__ == "__main__":
    main()
