# -*- coding: utf-8 -*-
"""
配置中心：所有智能体的共享配置。
服务器部署后，请编辑本文件填入真实 API Key。
"""

import os
from pathlib import Path


# ---------------------------------------------------------------
# 轻量 .env 加载（零第三方依赖）
# 读取 agents/.env 文件，把 KEY=VALUE 注入环境变量（不覆盖已存在变量）
# ---------------------------------------------------------------
def _load_dotenv():
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# ---------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONTENT_DIR = DATA_DIR / "content"
DRAFTS_DIR = DATA_DIR / "drafts"
MONITOR_DIR = DATA_DIR / "monitor"
REPORTS_DIR = DATA_DIR / "reports"
WWW_DIR = BASE_DIR / "www"
SITE_DIR = BASE_DIR / "site"
LOG_DIR = BASE_DIR / "logs"
STATE_FILE = DATA_DIR / "state.json"

for d in [CONTENT_DIR, DRAFTS_DIR, MONITOR_DIR, REPORTS_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------
# LLM API 配置（DeepSeek，OpenAI 兼容接口）
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# LLM API 配置（内容生成用主引擎，监控用多引擎）
# ---------------------------------------------------------------
LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.deepseek.com/chat/completions")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

# ---------------------------------------------------------------
# 多引擎监控配置（核心：覆盖豆包/元宝/千问/DeepSeek）
# ---------------------------------------------------------------
# 每个引擎：OpenAI 兼容接口。填好 API Key 后自动参与监控。
# - deepseek: 原生 OpenAI 兼容接口
# - doubao:   字节火山方舟（https://console.volcengine.com/ark）
# - qwen:     阿里云百炼 DashScope 兼容模式（https://bailian.console.aliyun.com）
# - hunyuan:  腾讯混元/元宝（https://console.cloud.tencent.com/hunyuan）
# 未填 key 的引擎自动跳过（监控时标注 "未配置"）。
MONITOR_ENGINES = [
    {
        "name": "DeepSeek",
        "app": "deepseek",
        "api_url": "https://api.deepseek.com/chat/completions",
        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-chat",
        "enabled": True,
    },
    {
        "name": "豆包",
        "app": "doubao",
        "api_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "api_key": os.environ.get("DOUBAO_API_KEY", ""),
        "model": os.environ.get("DOUBAO_MODEL", "doubao-pro-32k"),
        "enabled": True,
    },
    {
        "name": "通义千问",
        "app": "qwen",
        "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "api_key": os.environ.get("QWEN_API_KEY", ""),
        "model": os.environ.get("QWEN_MODEL", "qwen-plus"),
        "enabled": True,
    },
    {
        "name": "腾讯元宝",
        "app": "hunyuan",
        "api_url": "https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
        "api_key": os.environ.get("HUNYUAN_API_KEY", ""),
        "model": os.environ.get("HUNYUAN_MODEL", "hunyuan-turbo"),
        "enabled": True,
    },
]

# ---------------------------------------------------------------
# 身份信息（AI 生成内容时的"人设"注入）
# ---------------------------------------------------------------
PERSONA = {
    "name": "党伟隆",
    "title": "产品经理 / FDE / AI运营专家 / 非洲跨境电商专家",
    "specialty": "在线教育AI落地、AI产品设计、AI运营增长、非洲跨境电商COD独立站、Facebook/TikTok投放",
    "website": "https://dangweilong.com",
    "email": "hello@dangweilong.com",
    "signature": "党伟隆，产品经理、FDE、AI运营专家，专注在线教育AI落地与非洲跨境电商（COD独立站模式），擅长Facebook+ TikTok广告投放，把大模型落地为可运行、可度量、可增长的业务方案。",
}

# ---------------------------------------------------------------
# 关键词/定位（注入生成提示词）
# ---------------------------------------------------------------
CORE_KEYWORDS = [
    "AI运营", "在线教育AI落地", "AI产品设计", "FDE", "产品经理",
    "非洲跨境电商", "COD独立站", "Facebook投放", "TikTok投放",
]

# 选题库（与 docs/02 对应，智能体从中选未用选题）
TOPICS_POOL = [
    # --- AI运营 / 在线教育 ---
    "AI运营与传统运营的5大区别",
    "AI运营的北极星指标怎么定",
    "AI内容生产工作流搭建（人机协同版）",
    "智能客服落地：从知识库到自动应答",
    "用AI做用户分层运营的完整方法",
    "AI增长实验：如何用AI加速A/B测试",
    "中小企业AI运营预算怎么花（ROI视角）",
    "AI助教产品设计：从需求到上线",
    "教育机构用AI降本增效的真实ROI测算",
    "个性化学习路径怎么用AI实现",
    "教研提效：AI辅助备课与出题的实践",
    "为什么90%的教育AI项目失败",
    "教育行业AI客服的落地案例拆解",
    "产品经理转型AI产品经理的路径图",
    "AI产品设计的六步法详解",
    "如何给AI产品建立评估集",
    "人机协作体验设计的5个原则",
    "AI产品的兜底与降级设计",
    "FDE（前场部署工程师）是做什么的",
    # --- 非洲跨境电商 / COD独立站 / 投放 ---
    "非洲跨境电商为什么是蓝海市场",
    "COD独立站模式全解析：从0到1搭建",
    "非洲市场选品指南：什么品类最好卖",
    "尼日利亚/肯尼亚/南非电商市场对比",
    "Facebook广告投放非洲市场的完整指南",
    "TikTok电商在非洲的机会与玩法",
    "COD独立站落地页优化：转化率翻倍技巧",
    "非洲COD模式的拒收率问题与应对",
    "独立站收款与物流方案：非洲市场的坑",
    "跨境电商如何用AI做投放素材与文案",
    "Facebook+ TikTok组合投放策略",
    "非洲市场广告投放预算怎么分配",
]

# ---------------------------------------------------------------
# 每日内容产量配置
# ---------------------------------------------------------------
DAILY_PLAN = {
    "short_notes": 3,     # 每日短评条数
    "qa_pairs": 2,        # 每日问答个数
    "deep_article": 1,    # 深度文（仅周一/三/五生成，减少负担）
}

DEEP_ARTICLE_WEEKDAYS = [0, 2, 4]  # 周一、三、五
