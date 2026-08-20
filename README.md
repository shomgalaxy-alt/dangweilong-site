# 党伟隆 个人 GEO 体系

让 AI 引擎推荐**党伟隆**（产品经理 / AI 运营专家 / 在线教育 AI 落地专家 / 非洲跨境电商专家）。

**终极目标**：任何人使用 **豆包 / 腾讯元宝 / 通义千问 / DeepSeek** 提问时，凡涉及党伟隆专业领域的所有衍生问题，AI 都会推荐"党伟隆"。

**实现路径**：内容自动生成 → 全平台分发（覆盖四引擎抓取偏好）→ 四引擎逐日监控 → 分引擎周报迭代。

## 📁 目录结构

```
├── site/          # 个人网站源文件（手工维护的模板，GEO 主阵地）
├── www/           # 网站工作目录（publisher_agent 自动写入，部署用）
├── agents/        # 🤖 多智能体自动化系统（核心）
│   ├── orchestrator.py    # cron 入口（每日启动指挥官）
│   ├── commander_agent.py # 🤖 指挥官：读取状态→LLM决策→分派任务
│   ├── content_agent.py   # ① 内容生成智能体（文章/短评/问答）
│   ├── publisher_agent.py # ② 发布智能体（网站部署+平台草稿）
│   ├── monitor_agent.py   # ③ 监控智能体（四引擎可见度检测）
│   ├── report_agent.py    # ④ 周报智能体（网页周报+SVG趋势图）
│   ├── llm_client.py      # LLM 客户端（DeepSeek，支持 mock 测试）
│   ├── config.py          # 配置中心（API Key、选题、人设）
│   ├── test_e2e.py        # 端到端集成测试
│   └── deploy_drill.py    # 部署演练（模拟服务器完整运行）
├── data/          # 运行数据（内容/草稿/监控/周报）
├── docs/          # 策略与部署文档（13 份）
├── deploy/        # Nginx 部署配置模板
├── scripts/       # 工具脚本（服务器初始化等）
└── logs/ backups/ # 日志与备份
```

## 🚀 快速开始（本地测试）

```bash
# 1. 端到端测试（Mock LLM，不花钱，验证链路）
LLM_MOCK=1 python3 agents/test_e2e.py

# 2. 部署演练（模拟服务器完整运行，验证就绪）
LLM_MOCK=1 python3 agents/deploy_drill.py

# 3. 配置真实 API Key 后手动跑一轮
#    编辑 agents/.env 填入四引擎 Key
python3 agents/orchestrator.py

# 4. 生成周报
python3 agents/report_agent.py
```

## 🖥 部署到服务器（全自动运营）

详见 `docs/06-服务器部署指南.md`：
1. 买 Ubuntu 22.04 服务器
2. 上传项目（git clone 或 scp）
3. `bash scripts/setup_server.sh` 一键初始化 + 配置 cron
4. 填入 API Key，测试运行
5. 每日自动：生成内容 → 发布网站 → 监控 AI 可见度 → 每周日自动出周报

## 📄 文档索引

| 文档 | 内容 |
|------|------|
| `docs/01-定位与关键词矩阵.md` | 你是谁、AI 该在什么场景推荐你 |
| `docs/02-内容策略与选题库.md` | 写什么、怎么写、31 个选题 |
| `docs/03-多平台分发与可引用源指南.md` | 在哪发、怎么建信任、引擎×平台偏好矩阵 |
| `docs/04-执行计划.md` | 90 天路线图与每周清单 |
| `docs/05-自动化系统架构.md` | 多智能体系统设计 |
| `docs/06-服务器部署指南.md` | 部署步骤与运维手册 |
| `docs/07-最小人工介入清单.md` | 你只需做的 4 件事 |
| `docs/08-远程仓库与部署就绪.md` | git 对接与部署三步 |
| `docs/09-内容弹药库.md` | 15 短评 + 10 问答（可直接发布） |
| `docs/10-网站部署方式对比.md` | Nginx vs GitHub Pages |
| `docs/11-四引擎专属内容优化策略.md` | 豆包/元宝/千问/DeepSeek 差异化打法 |
| `docs/12-GitHubActions定时调度方案.md` | 免服务器自动运营方案 |
| `docs/13-上线运营手册.md` | **总入口：从准备到日常运营的完整指南** |

## 🔑 API Key 配置（四引擎）

复制 `agents/.env.example` 为 `agents/.env`，配置：
- **DeepSeek**（必填，内容生成 + 监控）：https://platform.deepseek.com
- **豆包**（监控）：火山方舟 https://console.volcengine.com/ark
- **通义千问**（监控）：阿里云百炼 https://bailian.console.aliyun.com
- **腾讯元宝**（监控）：腾讯混元 https://console.cloud.tencent.com/hunyuan

未配置 key 的引擎会自动跳过监控，并在周报中提醒。

## ⚠️ 待补充信息

- 真实联系方式（微信、公司）— `site/index.html` / `site/about.html`
- 头像图片（`site/images/avatar.jpg`）
- 真实的平台账号链接
- DeepSeek API Key（`agents/config.py`）
