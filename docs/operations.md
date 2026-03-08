# 运维手册

> 日常运维操作、部署方式、备份恢复、监控告警、故障排查。

---

## 一、服务器信息

| 项目 | 值 |
|------|---|
| **IP** | 119.29.237.199 |
| **OS** | Ubuntu 24.04 (腾讯云 Lighthouse) |
| **用户** | ubuntu（sudo 操作项目目录） |
| **SSH** | `ssh -i "mac.pem" -o IdentitiesOnly=yes ubuntu@119.29.237.199` |
| **项目路径** | `/root/KarvisForAll` |
| **端口** | 9000 |
| **服务管理** | systemd (`karvisforall.service`) |
| **Python** | `/root/KarvisForAll/venv/bin/python` |

---

## 二、部署方式

### 方式 1: 一键脚本（推荐新用户）

```bash
curl -fsSL https://raw.githubusercontent.com/.../setup.sh | sudo bash
```

脚本自动完成：安装依赖 → 创建 venv → 拉取代码 → 配置 systemd → 启动服务。

### 方式 2: Docker Compose

```bash
cd deploy/
cp ../.env.example ../.env
# 编辑 .env 填入密钥
docker compose up -d --build
```

### 方式 3: 手动部署

```bash
# 1. 安装依赖
sudo apt update && sudo apt install -y python3.12 python3.12-venv

# 2. 创建虚拟环境
python3 -m venv /root/KarvisForAll/venv
source /root/KarvisForAll/venv/bin/activate
pip install -r src/requirements.txt

# 3. 配置环境变量
cp .env.example src/.env
# 编辑 src/.env

# 4. 启动
cd /root/KarvisForAll
venv/bin/python src/app.py
```

### 方式 4: Git Push 部署

本地一行命令更新服务器：

```bash
git push deploy master
```

**服务器端配置**：

```bash
# 创建 bare repo
sudo git init --bare /root/KarvisForAll.git

# 创建 post-receive 钩子
sudo tee /root/KarvisForAll.git/hooks/post-receive << 'EOF'
#!/bin/bash
GIT_WORK_TREE=/root/KarvisForAll git checkout -f
cd /root/KarvisForAll
source venv/bin/activate
pip install -r src/requirements.txt --quiet
sudo systemctl restart karvisforall
echo "✅ 部署完成"
EOF
sudo chmod +x /root/KarvisForAll.git/hooks/post-receive

# 本地添加 remote
git remote add deploy ubuntu@119.29.237.199:/root/KarvisForAll.git
```

### systemd 服务配置

```ini
# /etc/systemd/system/karvisforall.service
[Unit]
Description=KarvisForAll Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/KarvisForAll
ExecStart=/root/KarvisForAll/venv/bin/python src/app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

---

## 三、日常运维

### 服务管理

```bash
# 启动/停止/重启
sudo systemctl start karvisforall
sudo systemctl stop karvisforall
sudo systemctl restart karvisforall

# 查看状态
sudo systemctl status karvisforall --no-pager

# 查看日志（实时）
sudo journalctl -u karvisforall -f -o cat

# 查看最近 N 行日志
sudo journalctl -u karvisforall --no-pager -n 100 -o cat

# 按时间查看
sudo journalctl -u karvisforall --since "2026-03-01 08:00" --until "2026-03-01 09:00" -o cat
```

### 健康检查

```bash
# 快速检查
curl -s http://127.0.0.1:9000/health | python3 -m json.tool

# 检查要点
# - status: "healthy"
# - disk_free_gb > 1
# - scheduler: true
# - active_users: 预期数量
```

### 手动触发定时任务

```bash
# 触发所有用户的日报
curl -X POST http://127.0.0.1:9000/system \
  -H "Content-Type: application/json" \
  -d '{"action": "daily_report"}'

# 触发指定用户
curl -X POST http://127.0.0.1:9000/system \
  -H "Content-Type: application/json" \
  -d '{"action": "morning_report", "user_id": "CaiWenWen"}'

# 可用 action:
# daily_init, scheduler_tick, refresh_cache,
# morning_report, todo_remind, evening_checkin,
# daily_report, reflect_push, mood_generate,
# weekly_review, monthly_review, nudge_check, companion_check
```

### Web 管理面板

| 页面 | 地址 |
|------|------|
| 管理后台 | http://119.29.237.199:9000/web/admin |
| 日志监控 | http://119.29.237.199:9000/web/logs |
| 仪表盘 | http://119.29.237.199:9000/web/dashboard |

---

## 四、更新部署

### SCP 方式（单文件更新）

```bash
# 上传文件
scp -i "mac.pem" KarvisForAll/src/app.py ubuntu@119.29.237.199:/tmp/

# 服务器端替换
ssh -i "mac.pem" ubuntu@119.29.237.199
sudo cp /tmp/app.py /root/KarvisForAll/src/
sudo systemctl restart karvisforall
```

### 批量更新

```bash
# 上传多个文件到临时目录
ssh -i "mac.pem" ubuntu@119.29.237.199 "sudo mkdir -p /tmp/kfa_update && sudo chmod 777 /tmp/kfa_update"

scp -i "mac.pem" \
  KarvisForAll/src/app.py \
  KarvisForAll/src/brain.py \
  KarvisForAll/src/skill_loader.py \
  ubuntu@119.29.237.199:/tmp/kfa_update/

# 替换并重启
ssh -i "mac.pem" ubuntu@119.29.237.199 \
  "sudo cp /tmp/kfa_update/*.py /root/KarvisForAll/src/ && \
   sudo systemctl restart karvisforall && \
   sudo rm -rf /tmp/kfa_update"
```

### 更新验证

```bash
# 1. 检查服务状态
sudo systemctl status karvisforall --no-pager

# 2. 健康检查
curl -s http://127.0.0.1:9000/health | python3 -m json.tool

# 3. 查看启动日志
sudo journalctl -u karvisforall --no-pager -n 20 -o cat
```

---

## 五、备份与恢复

### 自动备份脚本

```bash
# scripts/backup.sh
# 备份 data/ 目录到 /root/backups/
sudo bash /root/KarvisForAll/scripts/backup.sh
```

### 手动备份

```bash
# 备份用户数据
sudo tar czf /root/backups/kfa_data_$(date +%Y%m%d).tar.gz \
  -C /root/KarvisForAll data/

# 备份配置
sudo cp /root/KarvisForAll/src/.env /root/backups/.env_$(date +%Y%m%d)
```

### 恢复

```bash
# 恢复用户数据
sudo tar xzf /root/backups/kfa_data_20260301.tar.gz \
  -C /root/KarvisForAll

# 重启服务
sudo systemctl restart karvisforall
```

### 清空用户数据（谨慎！）

```bash
# 清空指定用户
sudo rm -rf /root/KarvisForAll/data/users/{user_id}

# 从注册表移除（编辑 JSON）
sudo python3 -c "
import json
f = '/root/KarvisForAll/data/_karvis_system/users.json'
d = json.load(open(f))
del d['{user_id}']
json.dump(d, open(f, 'w'), ensure_ascii=False, indent=2)
"
```

---

## 六、监控与告警

### 内置告警（自动）

| 类型 | 触发条件 | 渠道 |
|------|---------|------|
| 慢请求 | 连续 3 次 > 20s | 企微推送 |
| 异常 | handler 抛出异常 | 企微推送 |
| 月度预算 | 超 80%（¥50/月） | 企微推送 |
| 冷却 | 同类 300s 不重复 | — |

### Web 监控面板

访问 `/web/logs`，三个 Tab：

1. **日志** — 分组视图（按 Request ID）/ 原始视图，支持关键词/用户/级别过滤
2. **统计监控** — Token 成本趋势、延迟 P90/P99、技能热力图
3. **错误聚合** — TOP 20 去重错误 + traceback

### 关键指标

| 指标 | 正常范围 | 告警阈值 |
|------|---------|---------|
| 响应延迟 | 2-5s | P90 > 10s |
| 磁盘空间 | > 5 GB | < 1 GB |
| 日志文件 | < 10 MB | > 100 MB |
| 每日 Token | ~ 200K | 预算 80% |

---

## 七、日志管理

### 日志位置

| 日志 | 来源 | 查看方式 |
|------|------|---------|
| 应用日志 | stderr → journalctl | `journalctl -u karvisforall` |
| 文件日志 | `LOG_FILE_KARVISFORALL` | `tail -f /root/KarvisForAll/logs/app.log` |
| LLM 用量 | `data/_karvis_system/usage_log.jsonl` | 直接读取 |
| 决策日志 | `data/users/{uid}/_Karvis/logs/decisions.jsonl` | 直接读取 |

### 日志格式

```
HH:MM:SS [request_id] [模块] 消息内容
```

示例：
```
08:34:29 [fdba0e77] [/process] 开始处理 type=text, user=CaiWenWen
08:34:29 [fdba0e77] [Brain] 决策: skill=note.save
08:34:58 [fdba0e77] [handle_message] brain 返回: reply=有(53字), already_sent=True
```

### 日志轮转

```bash
# /etc/logrotate.d/karvisforall
/root/KarvisForAll/logs/app.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    postrotate
        systemctl reload karvisforall 2>/dev/null || true
    endscript
}
```

---

## 八、故障排查

### 常见问题

#### 1. 服务启动失败

```bash
# 查看详细错误
sudo journalctl -u karvisforall --no-pager -n 50

# 常见原因:
# - .env 文件缺失 → cp .env.example src/.env
# - Python 依赖未安装 → pip install -r src/requirements.txt
# - 端口被占用 → lsof -i :9000
```

#### 2. 企微消息不响应

```bash
# 检查企微 Token
curl -s http://127.0.0.1:9000/health | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('wework_token:', d['checks']['wework_token'])"

# 检查日志中的错误
sudo journalctl -u karvisforall --no-pager -n 200 -o cat | grep -i error
```

#### 3. OneDrive 用户报错

```bash
# 检查 OneDrive token 是否过期
sudo journalctl -u karvisforall --no-pager -n 100 -o cat | grep -i "onedrive\|token.*refresh\|401"

# OneDrive refresh token 需要手动更新（有效期 90 天）
```

#### 4. LLM API 报错

```bash
# 检查 API Key 配置
sudo grep -E "DEEPSEEK|QWEN" /root/KarvisForAll/src/.env

# 检查网络连通性
curl -s https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer {your_key}" | head -20
```

#### 5. 磁盘空间不足

```bash
# 检查磁盘
df -h /root

# 清理大文件
sudo find /root/KarvisForAll/data -name "*.jsonl" -size +50M
sudo journalctl --vacuum-size=100M

# 清理 usage_log 归档
sudo find /root/KarvisForAll/data/_karvis_system -name "usage_log_*.jsonl.gz" -mtime +30 -delete
```

#### 6. 定时任务不触发

```bash
# 检查 scheduler 状态
curl -s http://127.0.0.1:9000/health | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('scheduler:', d['checks']['scheduler'])"

# 检查 daily_init 是否执行
sudo journalctl -u karvisforall --no-pager --since today -o cat | grep daily_init
```

---

## 九、环境变量速查

### 必填

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `WEWORK_CORP_ID` | 企微企业 ID |
| `WEWORK_AGENT_ID` | 企微应用 ID |
| `WEWORK_CORP_SECRET` | 企微应用密钥 |
| `WEWORK_TOKEN` | 企微回调 Token |
| `WEWORK_ENCODING_AES_KEY` | 企微加密密钥 |
| `ADMIN_TOKEN` | Web 管理后台令牌 |

### 可选

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `QWEN_API_KEY` | — | 通义千问 API（启用 Flash 层） |
| `TENCENT_APPID` | — | 腾讯云 ASR（启用语音识别） |
| `TENCENT_SECRET_ID` | — | 腾讯云密钥 |
| `TENCENT_SECRET_KEY` | — | 腾讯云密钥 |
| `SENIVERSE_KEY` | — | 心知天气（启用天气查询） |
| `SERVER_PORT` | 9000 | 服务端口 |
| `DAILY_MESSAGE_LIMIT` | 50 | 每日消息上限 |
| `DATA_DIR` | `data` | 数据目录 |
| `ALERT_SLOW_THRESHOLD` | 20 | 慢请求阈值（秒） |
| `WEB_TOKEN_EXPIRE_HOURS` | 24 | Web 令牌有效期 |
