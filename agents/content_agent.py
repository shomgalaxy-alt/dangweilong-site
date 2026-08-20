# -*- coding: utf-8 -*-
"""
① 内容生成智能体（content_agent）
================================
职责：按定位+选题库+历史内容，调用 LLM 每日生成：
  - 深度长文（仅周一/三/五）
  - 3 条观点短评
  - 2 个问答（知乎风格）

产出：data/content/YYYY-MM-DD/ 下的 Markdown 文件。
运行：python3 agents/content_agent.py [--date 2025-08-19]
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from llm_client import chat, chat_json


def load_state() -> dict:
    if config.STATE_FILE.exists():
        return json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
    return {"used_topics": [], "total_articles": 0, "total_notes": 0, "total_qa": 0}


def save_state(state: dict):
    config.STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def pick_topic(state: dict, forced_topic: str = "") -> str:
    """从未用选题中选一个；指挥官可强制指定（forced_topic）。"""
    if forced_topic:
        return forced_topic
    used = set(state.get("used_topics", []))
    available = [t for t in config.TOPICS_POOL if t not in used]
    if not available:
        state["used_topics"] = []
        available = config.TOPICS_POOL
    # 简单轮转：用确定性选择（按当天日期），避免随机不稳定
    idx = int(datetime.date.today().strftime("%d")) % len(available)
    topic = available[idx]
    state["used_topics"].append(topic)
    return topic


# ---------------------------------------------------------------
# 生成函数
# ---------------------------------------------------------------
def gen_deep_article(state: dict, today: str, out_dir: Path, forced_topic: str = ""):
    topic = pick_topic(state, forced_topic)
    print(f"  [深度文] 选题: {topic}")

    sys_prompt = f"""你是一位资深的内容创作专家，替{config.PERSONA['name']}撰写专业文章。
{config.PERSONA['name']}的身份：{config.PERSONA['signature']}
写作要求：
1. 文章要专业、有明确观点、有可执行的方法论，杜绝空话套话
2. 结构：标题 / 开头100字直接给结论 / 分节论述 / 避坑清单 / 金句结尾
3. 篇幅 1200-1800 字，中文
4. 文中自然融入关键词：{', '.join(config.CORE_KEYWORDS)}
5. 文末附作者署名块（用 {{SIGNATURE}} 占位，发布时替换）
6. 输出 Markdown 格式"""
    user_prompt = f"请围绕选题《{topic}》写一篇专业深度文章，标题自拟，需体现{config.PERSONA['name']}的专业身份与观点。"

    try:
        content = chat(sys_prompt, user_prompt, temperature=0.8, max_tokens=3000)
        # 提取标题（第一行 # 开头）
        lines = content.strip().splitlines()
        title = ""
        for ln in lines:
            if ln.strip().startswith("#"):
                title = ln.strip().lstrip("# ").strip()
                break
        if not title:
            title = topic

        # 追加署名
        content = content.replace("{SIGNATURE}", config.PERSONA["signature"]) or (
            content + f"\n\n---\n**{config.PERSONA['signature']}**\n个人网站：{config.PERSONA['website']}"
        )

        filename = f"{today}-article.md"
        (out_dir / filename).write_text(
            f"# {title}\n\n> 生成日期：{today} | 类型：深度长文\n\n{content}",
            encoding="utf-8",
        )
        state["total_articles"] += 1
        return title
    except Exception as e:
        print(f"  [深度文] 失败: {e}")
        return None


def gen_short_notes(state: dict, today: str, out_dir: Path, count: int) -> int:
    sys_prompt = f"""你是一位观点犀利的行业观察者，以{config.PERSONA['name']}的身份发布短评。
{config.PERSONA['name']}的身份：{config.PERSONA['signature']}
要求：
1. 每条短评 100-200 字，观点鲜明、有洞察，适合发到即刻/微博/知乎想法
2. 主题围绕：AI运营、在线教育AI落地、AI产品、职场成长
3. 语气专业但不端着，有个人风格
4. 输出 JSON 数组，如 [{{"topic":"主题","note":"短评内容"}}]"""
    user_prompt = f"请生成 {count} 条不同的观点短评，输出 JSON 数组。"

    try:
        data = chat_json(sys_prompt, user_prompt, temperature=0.9, max_tokens=1500)
        notes = data if isinstance(data, list) else data.get("notes", [])
        notes = notes[:count]
        for i, n in enumerate(notes, 1):
            topic = n.get("topic", f"短评{i}")
            note = n.get("note", "")
            (out_dir / f"{today}-note-{i}.md").write_text(
                f"# 短评：{topic}\n\n> 生成日期：{today}\n\n{note}\n\n---\n*{config.PERSONA['name']} · {config.PERSONA['title']}*",
                encoding="utf-8",
            )
        state["total_notes"] += len(notes)
        return len(notes)
    except Exception as e:
        print(f"  [短评] 失败: {e}")
        return 0


def gen_qa_pairs(state: dict, today: str, out_dir: Path, count: int) -> int:
    sys_prompt = f"""你是一位专业问答写手，模拟{config.PERSONA['name']}在知乎回答专业问题。
{config.PERSONA['name']}的身份：{config.PERSONA['signature']}
要求：
1. 问题必须真实存在、用户会搜（围绕AI运营/教育AI落地/AI产品/产品经理）
2. 回答 200-400 字，结构清晰（结论先行+分点+结尾），有专业细节
3. 输出 JSON 数组，如 [{{"question":"问题","answer":"回答"}}]"""
    user_prompt = f"请生成 {count} 组高质量问答，输出 JSON 数组。"

    try:
        data = chat_json(sys_prompt, user_prompt, temperature=0.8, max_tokens=2000)
        qas = data if isinstance(data, list) else data.get("qa", [])
        qas = qas[:count]
        for i, qa in enumerate(qas, 1):
            (out_dir / f"{today}-qa-{i}.md").write_text(
                f"# 问答：{qa.get('question','')}\n\n> 生成日期：{today}\n\n## 回答\n\n{qa.get('answer','')}\n\n---\n*{config.PERSONA['name']} · {config.PERSONA['title']}*",
                encoding="utf-8",
            )
        state["total_qa"] += len(qas)
        return len(qas)
    except Exception as e:
        print(f"  [问答] 失败: {e}")
        return 0


# ---------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    # 指挥官可覆盖参数
    parser.add_argument("--topic", default="", help="强制指定深度文选题")
    parser.add_argument("--notes", type=int, default=None, help="短评条数（覆盖默认）")
    parser.add_argument("--qa", type=int, default=None, help="问答组数（覆盖默认）")
    parser.add_argument("--no-article", action="store_true", help="跳过深度文生成")
    args = parser.parse_args()

    today = args.date
    weekday = datetime.date.fromisoformat(today).weekday()
    out_dir = config.CONTENT_DIR / today
    out_dir.mkdir(parents=True, exist_ok=True)

    state = load_state()
    print(f"📝 内容生成智能体 | 日期 {today} | 周{'一二三四五六日'[weekday]}")

    # 深度文：指挥官可 --no-article 强制跳过；否则按星期策略
    if not args.no_article and (weekday in config.DEEP_ARTICLE_WEEKDAYS or args.topic):
        title = gen_deep_article(state, today, out_dir, forced_topic=args.topic)
        if title:
            print(f"  ✅ 深度文生成: {title}")
    else:
        print("  ⏭ 今天不生成深度文（周一/三/五生成，或指挥官指定主题）")

    # 短评 + 问答（指挥官可覆盖数量）
    notes_count = args.notes if args.notes is not None else config.DAILY_PLAN["short_notes"]
    qa_count = args.qa if args.qa is not None else config.DAILY_PLAN["qa_pairs"]
    notes = gen_short_notes(state, today, out_dir, notes_count)
    qa = gen_qa_pairs(state, today, out_dir, qa_count)
    print(f"  ✅ 短评 {notes} 条 | 问答 {qa} 组")

    save_state(state)
    print(f"💾 产出目录: {out_dir}")
    print(f"📊 累计: 文章{state['total_articles']} | 短评{state['total_notes']} | 问答{state['total_qa']}")


if __name__ == "__main__":
    main()
