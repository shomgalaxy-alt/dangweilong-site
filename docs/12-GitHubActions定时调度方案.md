# GitHub Actions 定时调度方案（免服务器备选）

> 如果暂时不买服务器，可以用 GitHub Actions 免费实现"每日自动运营"。
> 优点：免费、无需服务器、云端运行；缺点：受 GitHub 免费额度限制、无法访问私有内容。
> 更新日期：2025-08-24

---

## 一、方案原理

把整个系统放进 GitHub 仓库，用 GitHub Actions 的 `schedule` 定时触发工作流，在云端跑 `orchestrator.py`，结果（生成的内容、网站页面）自动提交回仓库。

```
GitHub Actions (cron 每日 08:00 UTC+8)
    └── 运行 orchestrator.py
            ├── content_agent（生成内容）
            ├── publisher_agent（更新 www/ + git commit）
            └── monitor_agent（四引擎监控）
    └── git push 回仓库 → GitHub Pages 自动发布网站
```

## 二、文件配置

在仓库创建 `.github/workflows/daily.yml`：

```yaml
name: GEO Daily Operations

on:
  schedule:
    # 每天 00:30 UTC = 08:30 北京时间
    - cron: '30 0 * * *'
  workflow_dispatch:  # 支持手动触发

jobs:
  operate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      # 配置 API Key（在 GitHub 仓库 Settings → Secrets 里添加）
      - name: Configure env
        run: |
          echo "LLM_API_KEY=${{ secrets.LLM_API_KEY }}" >> agents/.env
          echo "DEEPSEEK_API_KEY=${{ secrets.DEEPSEEK_API_KEY }}" >> agents/.env
          echo "DOUBAO_API_KEY=${{ secrets.DOUBAO_API_KEY }}" >> agents/.env
          echo "QWEN_API_KEY=${{ secrets.QWEN_API_KEY }}" >> agents/.env
          echo "HUNYUAN_API_KEY=${{ secrets.HUNYUAN_API_KEY }}" >> agents/.env

      - name: Run orchestrator
        run: python3 agents/orchestrator.py

      # 把生成的内容提交回仓库
      - name: Commit results
        run: |
          git config user.name "GEO Bot"
          git config user.email "geo-bot@users.noreply.github.com"
          git add -A
          git diff --cached --quiet || git commit -m "auto: daily GEO operations $(date +%F)"
          git push
```

## 三、启用步骤

1. 推送仓库到 GitHub
2. 在仓库 Settings → Secrets and variables → Actions 添加上述 5 个 API Key
3. 网站托管：用 `dangweilong.github.io` 仓库名，GitHub Pages 自动发布 `www/`
4. 首次手动触发一次（Actions → GEO Daily Operations → Run workflow）验证

## 四、与服务器方案的对比

| 维度 | GitHub Actions | 个人服务器 |
|------|---------------|-----------|
| 费用 | 免费（有额度） | 需购买 |
| 定时精度 | 分钟级（足够） | 秒级 |
| 运行时长限制 | 免费版单任务限时（足够本系统） | 无限制 |
| 私有数据 | 公开仓库有泄露风险，需私有仓库 | 完全私有 |
| 适合 | 起步阶段/验证 | 正式长期运营 |

## 五、注意事项

- 免费额度：公开仓库无限，私有仓库每月 2000 分钟（本系统每日运行约 5-10 分钟，绰绰有余）
- API Key 必须放 GitHub Secrets，**绝不能写进代码或 .env 提交**
- 本系统零第三方依赖（纯 Python 标准库），Actions 环境开箱即用
- 周报文件也会自动提交回仓库，用户可在仓库 Actions 的 Artifacts 或提交记录里查看
