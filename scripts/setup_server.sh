#!/usr/bin/env bash
# ============================================================
# 党伟隆 GEO 自动化系统 - 服务器一键初始化脚本
# 适用：Ubuntu 22.04 LTS（root 或 sudo 用户）
# 用法：bash scripts/setup_server.sh
# ============================================================
set -e

echo "=========================================="
echo " 党伟隆 GEO 自动化系统 · 服务器初始化"
echo "=========================================="

# 1. 系统依赖
echo "[1/6] 安装系统依赖..."
apt-get update -y
apt-get install -y python3 python3-pip git cron curl

# 2. 拉取项目（若未 clone）
PROJECT_DIR="${PROJECT_DIR:-/root/dwl}"
if [ ! -f "$PROJECT_DIR/agents/orchestrator.py" ]; then
  echo "[2/6] 克隆项目到 $PROJECT_DIR ..."
  mkdir -p "$PROJECT_DIR"
  # TODO: 把下面的仓库地址换成你的实际 git 仓库
  # git clone https://github.com/dangweilong/dwl.git "$PROJECT_DIR"
  echo "  ⚠ 请手动把项目文件上传到 $PROJECT_DIR（scp 或 git clone）"
else
  echo "[2/6] 项目已存在，跳过"
fi
cd "$PROJECT_DIR"

# 3. Python 依赖（本项目零第三方依赖，纯标准库）
echo "[3/6] Python 环境检查（标准库即可运行）..."
python3 --version

# 4. 创建目录
echo "[4/6] 创建数据目录..."
mkdir -p data/content data/drafts data/monitor data/reports logs backups

# 5. 配置 API Key
if [ ! -f agents/.env ]; then
  echo "[5/6] 配置 LLM API Key（四引擎：DeepSeek/豆包/千问/元宝）..."
  cp agents/.env.example agents/.env 2>/dev/null || cp scripts/.env.example agents/.env 2>/dev/null || true
  echo "  ⚠ 请编辑 $PROJECT_DIR/agents/.env，至少填入 DeepSeek API Key；"
  echo "    建议同时配置豆包/通义千问/腾讯元宝 Key 实现四引擎全监控"
fi

# 6. 写入 cron 定时任务
echo "[6/6] 配置 cron 定时任务..."
CRON_LINES=(
  "# 党伟隆 GEO 自动化（每日 08:00 生成→发布→监控）"
  "0 8 * * * cd $PROJECT_DIR && python3 agents/orchestrator.py >> logs/cron.log 2>&1"
  "# 每周日 20:00 生成周报"
  "0 20 * * 0 cd $PROJECT_DIR && python3 agents/report_agent.py >> logs/report.log 2>&1"
  "# 每周一 03:00 备份"
  "0 3 * * 1 cd $PROJECT_DIR && tar czf backups/\$(date +\%Y\%m\%d).tar.gz data/ www/ site/ agents/ 2>/dev/null || true"
)
for line in "${CRON_LINES[@]}"; do
  (crontab -l 2>/dev/null | grep -F "$line") || (crontab -l 2>/dev/null; echo "$line") | crontab -
done
echo "  ✅ cron 已配置："
crontab -l | grep -A1 "党伟隆" || true

echo ""
echo "=========================================="
echo " ✅ 初始化完成！接下来："
echo "  1. 编辑 agents/config.py 或 agents/.env 填入 LLM_API_KEY"
echo "  2. 测试运行: python3 agents/orchestrator.py"
echo "  3. 查看周报: python3 agents/report_agent.py"
echo "=========================================="
