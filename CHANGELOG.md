# 版本历史

> KarvisForAll 项目的版本演进记录。

---

## V12 — 统一架构 (2026-03)

**当前版本** — Karvis 单用户版与 KarvisForAll 多用户版合并为统一代码库。

### 日志系统重构
- 所有模块 `_log()` 统一输出 `HH:MM:SS [request_id] message` 时间戳格式
- SkillLoader 从 24 行逐模块日志精简为 1 行摘要
- 移除 `get_all_active_users()`、`increment_message_count()`、解密成功等冗余日志
- Scheduler 只在有实际变更时打印日志
- Flask/werkzeug 设为 ERROR 级别，过滤外部扫描探测噪音
- Web 日志查看器增加分组视图（按 Request ID 聚合）、一键复制、Toast 提示

### OneDrive IO 修复
- 修复 `_upload_small()` 缺少重试机制的问题
- 修复错误部署单用户版 `onedrive_io.py` 导致的 `ImportError` 生产故障

---

## V11 — Web 管理平台 (2026-02)

### 管理后台
- 新增 `admin.html` — 用户运营中心（用户列表、挂起/激活、技能配置）
- 新增 `logs.html` — 日志 & 监控三合一面板（日志/统计/错误聚合）
- 统计面板：Token 成本趋势、延迟瀑布图（P50/P90/P99）、技能热力图
- 错误聚合：自动从日志中提取 ERROR/Traceback 并去重 TOP 20

### Web 用户页面
- 新增 `memory.html` — 长期记忆分区卡片视图
- 新增 `mood.html` — 30 天情绪折线图 + 情绪日记列表
- Dashboard 增加情绪曲线（Chart.js）

### 成本控制
- LLM 用量追踪（usage_log.jsonl）+ 自动轮转（>10MB 归档压缩）
- 月度预算监控（每 50 次调用检查，超 80% 推企微告警）
- Prompt Token 膨胀检测

---

## V10 — 企微告警 & 健康检查 (2026-02)

### 告警系统
- 慢请求告警（连续 N 次 > 20s → 企微推送管理员）
- 异常告警（handler 异常 → 企微推送）
- 告警冷却机制（同类 300s 不重复）

### 健康检查
- `GET /health` 深度检查（API Key / 企微 Token / 磁盘 / Scheduler / 日志大小）
- 降级状态检测（任一检查项异常 → 503）

### 部署优化
- systemd 服务配置（开机自启 + 自动重启）
- logrotate 日志轮转

---

## V9 — Web 查看平台 (2026-02)

### 用户页面
- `login.html` — Token 登录（URL 参数自动填入）
- `dashboard.html` — 仪表盘概览
- `notes.html` — 速记时间线
- `todos.html` — 待办管理
- `daily.html` — 日记（日报/周报/月报）
- `archive.html` — 归档笔记（6 个分类）

### Token 系统
- `web.token` skill — 用户说"给我查看链接"生成 24h 令牌
- 三级 Token 提取（Header > Cookie > Query Param）
- 过期自动清理

---

## V8 — 智能调度引擎 (2026-02)

### 意图队列
- 每日 05:00 生成当日 7 个意图（晨报/待办提醒/陪伴/习惯/自问/打卡/日报）
- 基于用户作息节奏动态调整时间窗口
- 意图合并（晚签到+日报可合并为一次推送）

### 规则引擎
- scheduler_tick 定期评估 pending 意图
- 四种决策：send / wait / skip / merge
- 防骚扰：每日上限 + 最小间隔 + 安静时间 + 周末偏移

### 节奏学习
- 记录每小时活跃计数
- 推算起床/入睡时间
- 周末偏移量

---

## V7 — 高级技能 (2026-01)

### 新增 Skill
- `deep.dive` — 主题深潜（跨时间线全历史分析，Think 模型）
- `reflect.*` — 深度自问（200 题库 × 10 维度，90 天去重，心情适配）
- `decision.*` — 决策追踪与复盘（记录/复盘/列表）
- `habit.*` — 微习惯实验（提议/触发/状态/完成）
- `internal.*` — 文件操作 Agent Loop（读/搜/列，最多 5 轮）
- `dynamic` — 动态操作引擎（6 种原子 op）

### 多模型路由
- Flash 层（Qwen Flash）— 快速判断、笔记过滤
- Main 层（DeepSeek V3.2）— 主力处理
- Think 层（DeepSeek Thinking）— 深度推理
- VL 层（Qwen VL Max）— 图片理解（管理员）
- 自动降级：Flash 失败 → Main

---

## V6 — 多用户基座 (2026-01)

### 核心架构
- `UserContext` 全链路贯穿 — 每个函数签名 `(params, state, ctx)`
- 多用户数据隔离 — 每用户独立目录结构（11 个子目录）
- Skill 热加载 — `skills/` 目录自动发现 `SKILL_REGISTRY`
- Storage 策略模式 — Local / OneDrive 无感切换

### 用户管理
- 自动注册 + 三步新手引导（昵称 → 第一条笔记 → 第一个待办）
- 新用户通知管理员
- 每日消息限额（默认 50 条）
- 不活跃检测（7 天阈值）
- 挂起/激活机制

### 三级权限体系
- Skill visibility（public / preview / private）
- 用户级黑白名单（支持通配符 `finance.*`）
- 管理员特权（`role: "admin"`）

---

## V5 — 基础技能 (2025-12)

### Skill 模块
- `note.save` — 快速笔记
- `classify.archive` — 分类归档（工作/情感/生活/碎碎念）
- `todo.add` / `todo.done` / `todo.list` — 待办管理
- `checkin.*` — 晚间 4 题打卡
- `book.*` — 读书笔记全流程
- `media.*` — 影视笔记
- `voice.journal` — 语音日记
- `daily.generate` — 日报生成
- `weekly.review` — 周回顾
- `monthly.review` — 月度回顾
- `mood.generate` — 情绪日记
- `settings.*` — 用户设置（昵称/AI 名/风格/个人信息）
- `finance.*` — 财务四件套（导入/查询/快照/月报）

### 记忆系统
- 长期记忆（memory.md — 分段结构）
- 对话压缩（保留 6 条 + 摘要）
- 三级缓存（内存 → /tmp → IO）

---

## V1-V4 — 单用户原型 (2025)

> 早期版本在 `Karvis/` 仓库中开发，后迁移到 `KarvisForAll/` 统一代码库。

- V1: 基础对话 + Obsidian 笔记写入
- V2: 企微集成 + 媒体处理（图片/语音/视频）
- V3: 定时任务（日报/打卡/晨报）
- V4: OneDrive 同步 + 腾讯云 SCF 部署
