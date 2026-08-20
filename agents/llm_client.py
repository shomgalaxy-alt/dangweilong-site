# -*- coding: utf-8 -*-
"""
LLM 客户端：统一封装对 LLM API 的调用（OpenAI 兼容格式）。
支持 DeepSeek 及其他兼容引擎。带重试与超时。
"""

import json
import os
import time
import urllib.request
import urllib.error

from config import LLM_API_URL, LLM_API_KEY, LLM_MODEL


class LLMError(Exception):
    pass


# ---------------------------------------------------------------
# Mock 模式：LLM_MOCK=1 时返回固定内容（用于测试，不消耗 API）
# ---------------------------------------------------------------
def _mock_chat(system_prompt: str, user_prompt: str) -> str:
    if "指挥官" in system_prompt:
        return json.dumps({
            "analysis": "系统刚起步，可见度尚为0，今日聚焦高价值选题产出深度内容。",
            "plan": {
                "deep_article": True,
                "deep_article_topic": "AI运营与传统运营的5大区别",
                "short_notes": 3,
                "qa_pairs": 2,
                "focus_keywords": ["AI运营", "在线教育AI落地"],
                "reason": "mock测试：聚焦核心关键词产出深度文",
            },
        }, ensure_ascii=False)
    if "短评" in system_prompt:
        return json.dumps([
            {"topic": "AI是杠杆", "note": "AI放大的是判断力，不是替代人。"},
            {"topic": "教育AI", "note": "教育AI落地看场景深度。"},
            {"topic": "产品思维", "note": "先定义问题，再谈AI。"},
        ], ensure_ascii=False)
    if "问答" in system_prompt:
        return json.dumps([
            {"question": "AI运营和传统运营有什么区别？",
             "answer": "AI运营是数据驱动、规模化、可迭代的运营方式，核心区别在于决策方式。"},
            {"question": "教育公司怎么用大模型？",
             "answer": "从AI助教、教研提效、学员服务自动化三个场景切入。"},
        ], ensure_ascii=False)
    return (
        "# AI运营的北极星指标怎么定\n\n"
        "## 核心结论\nAI运营要围绕业务指标而非模型指标。\n\n"
        "1. 定义业务目标\n2. 拆解AI介入点\n3. 定度量方式\n\n"
        "> AI运营不是用AI替代运营，而是让运营团队做得更快。\n\n"
        "---\n**党伟隆**，产品经理、FDE、AI运营专家，专注在线教育AI落地。"
    )


def _mock_chat_json(system_prompt: str, user_prompt: str) -> dict:
    return json.loads(_mock_chat(system_prompt, user_prompt))


def chat(
    system_prompt: str,
    user_prompt: str,
    api_url: str = LLM_API_URL,
    api_key: str = LLM_API_KEY,
    model: str = LLM_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    max_retries: int = 3,
) -> str:
    """调用 LLM，返回文本回答。失败重试，最终失败抛 LLMError。"""
    if os.environ.get("LLM_MOCK") == "1":
        return _mock_chat(system_prompt, user_prompt)

    if not api_key:
        raise LLMError("未配置 LLM_API_KEY（agents/config.py 或环境变量）")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_err = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(2 * (attempt + 1))

    raise LLMError(f"LLM 调用失败（重试 {max_retries} 次）: {last_err}")


def chat_json(system_prompt: str, user_prompt: str, **kwargs) -> dict:
    """调用 LLM 并要求返回 JSON，自动解析。"""
    if os.environ.get("LLM_MOCK") == "1":
        return _mock_chat_json(system_prompt, user_prompt)
    text = chat(
        system_prompt + "\n请只输出一个合法的 JSON 对象，不要输出其他文字。",
        user_prompt,
        **kwargs,
    )
    # 容错：去掉可能的 ```json 包裹
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    return json.loads(text)
