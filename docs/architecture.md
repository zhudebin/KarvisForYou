# 架构详解

> 本文档描述 KarvisForAll V12 的完整系统架构、模块关系和核心处理流程。

---

## 一、系统全景

```
                         ┌─────────────────────────┐
                         │    企业微信 / 用户手机     │
                         └────────┬────────────────┘
                                  │ Webhook POST /wework
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        app.py  —  Flask 主应用                   │
│                                                                   │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │ /wework   │  │ /process     │  │ V8 Scheduler               │ │
│  │ 消息网关   │─▶│ 异步处理端点  │  │ APScheduler                │ │
│  │ 解密/去重  │  │ handle_msg() │  │ daily_init → 意图队列       │ │
│  └──────────┘  └──────┬───────┘  │ scheduler_tick → 规则引擎   │ │
│                       │          │ refresh_cache → 缓存清理     │ │
│                       ▼          └──────────┬─────────────────┘ │
│               ┌──────────────┐              │ POST /system       │
│               │   brain.py    │◀─────────────┘                   │
│               │   AI 大脑     │                                   │
│               └──────┬───────┘                                   │
│                      │                                            │
│         ┌────────────┼────────────┐                              │
│         ▼            ▼            ▼                              │
│  ┌───────────┐ ┌──────────┐ ┌──────────┐                       │
│  │ Flash 层   │ │ Main 层   │ │ Think 层  │   多模型路由          │
│  │ Qwen Flash │ │ DeepSeek  │ │ DS Think  │                      │
│  │ 快速判断    │ │ 主力处理   │ │ 深度推理   │                      │
│  └───────────┘ └──────────┘ └──────────┘                       │
│                      │                                            │
│              ┌───────┴───────┐                                   │
│              ▼               ▼                                   │
│       ┌────────────┐  ┌────────────┐                            │
│       │ Skill 执行  │  │ 回复路由    │                            │
│       │ 24 模块     │  │ 直返/加工   │                            │
│       │ 43 个 Skill │  │ Flash 润色  │                            │
│       └─────┬──────┘  └─────┬──────┘                            │
│             │               │                                    │
│             ▼               ▼                                    │
│       ┌────────────┐  ┌────────────┐                            │
│       │ Storage     │  │ 企微 API    │                            │
│       │ Local/OD   │  │ 发送回复    │                            │
│       └────────────┘  └────────────┘                            │
│                                                                   │
│  ┌──────────────────────────────────────────┐                   │
│  │ web_routes.py  —  Web 管理平台             │                   │
│  │ 10 个用户页面 + 6 个管理 API + 12 个用户 API│                   │
│  └──────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、核心模块

### 2.1 消息网关 (`app.py` — `/wework`)

1. 接收企微 Webhook → `wework_crypto.py` 解密
2. 提取消息类型（text / image / voice / video / link）
3. 消息去重（`_MSG_SEEN` 缓存 + TTL 10 分钟）
4. 媒体文件处理：
   - 语音 → 腾讯云 ASR 转文字
   - 图片/视频/文件 → 下载保存
   - 链接 → BeautifulSoup 抓取正文
5. 异步转发到 `/process`（200ms 内响应企微）

### 2.2 AI 大脑 (`brain.py` — `process()`)

**完整处理流水线**：

```
用户消息
  │
  ├─ 1. 存储预热（创建 Storage 实例）
  ├─ 2. 并发读取 state.json + memory.md
  ├─ 3. 图片处理（管理员 → VL 模型，普通用户 → 直接保存）
  ├─ 4. 打卡超时检查（>30min 自动取消）
  ├─ 5. 记录短期记忆 + 更新节奏画像
  │
  ├─ 6. 组装 System Prompt ─────────────────┐
  │     ├─ SOUL（人格定义 + 用户自定义覆写）    │
  │     ├─ 长期记忆（memory.md）              │
  │     ├─ 最近对话（6 原始 + 压缩摘要）       │
  │     ├─ 状态摘要（打卡/习惯/读书/待办等）    │
  │     ├─ 时间信息（日期/星期/农历/节气）      │
  │     ├─ 条件 RULES（按 payload 类型注入）   │  ← 减少 Token
  │     └─ SKILLS（按用户权限动态生成）         │
  │                                            │
  ├─ 7. 多模型路由 ─────────────────────────────┘
  │     ├─ Flash → 快速判断类任务
  │     ├─ Main  → 用户消息 + 定时任务
  │     └─ Think → 深潜 + 决策追踪
  │
  ├─ 8. 解析 JSON 决策
  ├─ 9. Reflect 防护（自问流程中禁止跳到其他 skill）
  ├─ 10. Quick-Notes 过滤（Flash 异步判断是否有意义）
  │
  ├─ 11. 执行 Steps ────────────────────────────┐
  │      └─ 三级权限拦截                          │
  │         ├─ Visibility（public/preview/private）│
  │         ├─ 用户黑白名单                        │
  │         └─ 管理员特权                          │
  │                                                │
  ├─ 12. 智能回复路由 ──────────────────────────────┘
  │      ├─ 简单 skill → 直接返回 reply
  │      └─ 复杂场景 → Flash 加工后返回
  │
  ├─ 13. 先发回复（降低用户感知延迟）
  │
  └─ 14. 异步后处理
         ├─ Flash 笔记过滤
         ├─ 节奏画像更新
         ├─ state.json + memory.md 保存
         ├─ 决策日志记录
         └─ 告警检测
```

### 2.3 V8 智能调度引擎 (`app.py`)

**核心机制**：意图队列 + 规则引擎 + 防骚扰

```
每日 05:00 daily_init
  │
  └─ 为每个活跃用户生成当日意图队列：
     ┌──────────────┬──────────────┬──────────────┐
     │ morning_report│ todo_remind  │ companion    │
     │ 晨报(08:30)  │ 待办(10:00)  │ 陪伴(14:00)  │
     └──────────────┴──────────────┴──────────────┘
     ┌──────────────┬──────────────┬──────────────┐
     │ nudge_check  │ reflect_push │evening_checkin│
     │ 习惯(16:00)  │ 自问(20:00)  │ 打卡(21:30)  │
     └──────────────┴──────┬───────┴──────────────┘
                           │
                           ▼
每 N 分钟 scheduler_tick
  │
  └─ 遍历意图队列 → 规则引擎评估：
     ├─ send   → 立即执行（POST /system）
     ├─ wait   → 延后再评估
     ├─ skip   → 跳过（条件不满足）
     └─ merge  → 合并执行（如晚签到+日报）
```

**防骚扰策略**：
- 每日推送上限（默认 5 条）
- 最小间隔（默认 90 分钟）
- 安静时间（22:00 - 07:00）
- 周末偏移（推迟 1 小时）
- 过期意图自动跳过

### 2.4 技能系统 (`skill_loader.py` + `skills/`)

**热加载机制**：
1. 扫描 `skills/` 目录下所有 `.py` 文件
2. 每个文件导出 `SKILL_REGISTRY` 字典
3. 支持两种注册格式：
   - 简单：`{"skill.name": handler_function}`
   - 完整：`{"skill.name": {"handler": fn, "visibility": "public", "description": "..."}}`
4. 全局注册表缓存，首次加载后复用

**三级权限体系**：

| 级别 | 机制 | 说明 |
|------|------|------|
| L1 | Skill visibility | `public` / `preview`（敬请期待）/ `private`（仅管理员） |
| L2 | 用户黑白名单 | `user_config.skills.mode` + `list`，支持通配符 |
| L3 | 管理员特权 | `role: "admin"` 用户可使用 private skill |

### 2.5 存储层 (`storage.py` + `local_io.py` + `onedrive_io.py`)

**策略模式**：

```
storage.py (工厂)
  ├── create_storage("local", ...)    → LocalFileIO
  └── create_storage("onedrive", ...) → OneDriveIO
```

**统一接口**（Duck Typing）：
- `read_text(path)` / `write_text(path, content)`
- `read_json(path)` / `write_json(path, data)`
- `append_to_section(path, section, content)`
- `append_to_quick_notes(path, content)`
- `upload_binary(path, data)` / `download_binary(path)`
- `list_children(path)`

**OneDrive 特性**：
- 三级缓存：内存（5min TTL）→ `/tmp` 磁盘（10min）→ Graph API
- Token 双重检查锁，提前 120s 刷新
- 全局共享 HTTP Session（连接池 8 连接）
- 小文件直传（≤4MB）/ 大文件分片（每片 3.2MB）
- 全部网络操作 3 次重试 + 超时控制

### 2.6 记忆系统 (`memory.py`)

**三层架构**：

| 层 | 实现 | TTL | 用途 |
|---|---|---|---|
| Prompt 缓存 | `PromptCache` — 内存 → `/tmp` → IO | 可配置 | SOUL / SKILLS / RULES 模板 |
| State 缓存 | 按 user_id 分区 — 内存 → `/tmp` → IO | 请求级 | 用户状态（打卡/习惯/待办等） |
| 对话窗口 | `add_message_to_state()` | 保留 10 条 | 最近对话上下文 |

**对话压缩**：保留最近 6 条原始消息，旧消息压缩为摘要（每条 100 字，总上限 800 字）。

**长期记忆** (`memory.md`)：
- 按 `## section` 结构存储
- 支持 `add`（追加+去重）/ `update`（覆盖）/ `delete`（关键词匹配）
- 写入后自动清除缓存

### 2.7 用户上下文 (`user_context.py`)

**`UserContext` 类** — 贯穿所有函数调用的上下文对象：

```python
ctx = UserContext(user_id)
ctx.user_id          # 用户标识
ctx.nickname         # 昵称
ctx.base_dir         # 用户数据根目录
ctx.IO               # Storage 实例（Local 或 OneDrive）
ctx.is_admin         # 是否管理员
ctx.is_skill_allowed("finance.query")  # 权限检查
```

**用户生命周期**：

```
企微首次发消息
  │
  ├─ 自动注册 → 创建 11 个目录 + 初始化默认文件
  ├─ 通知管理员（企微消息）
  │
  └─ 三步新手引导：
     step 1: 等昵称（LLM 提取） → "叫我XX"
     step 2: 等第一条笔记 → 任意消息
     step 3: 等第一个待办 → "帮我记个待办"
     step 0: 完成 → 生成 Web 查看链接
```

### 2.8 Web 管理平台 (`web_routes.py` + `web_static/`)

**用户页面**（10 个）：

| 页面 | 路由 | 功能 |
|------|------|------|
| 登录 | `/web/login` | Token 验证 |
| 仪表盘 | `/web/dashboard` | 今日概览、情绪曲线 |
| 速记 | `/web/notes` | 时间线卡片、分页 |
| 待办 | `/web/todos` | 进行中/已完成筛选 |
| 日记 | `/web/daily` | 日报/周报/月报/情绪 |
| 归档 | `/web/archive` | 6 类笔记浏览 |
| 情绪 | `/web/mood` | 30 天情绪折线图 |
| 记忆 | `/web/memory` | AI 长期记忆分区卡片 |
| 管理后台 | `/web/admin` | 用户运营中心 |
| 日志监控 | `/web/logs` | 分组日志/统计/错误聚合 |

**技术栈**：Alpine.js + Tailwind CSS + Chart.js，纯静态 HTML（SPA 风格），统一暖色调设计。

---

## 三、多模型分层架构

| 层级 | 模型 | 用途 | 成本 |
|------|------|------|------|
| **Flash** | Qwen Flash | 快速判断、笔记过滤、回复加工 | 免费 |
| **Main** | DeepSeek V3.2 | 用户消息处理、定时任务 | 输入 2¥/M + 输出 8¥/M |
| **Think** | DeepSeek V3.2 (thinking) | 深潜、决策追踪 | 同 Main |
| **VL** | Qwen VL Max | 图片理解（仅管理员） | 输入 3¥/M + 输出 9¥/M |

**自动降级**：Flash 失败 → 降级到 DeepSeek Main。

---

## 四、数据架构

### 4.1 每用户目录结构

```
data/users/{user_id}/
├── 00-Inbox/
│   ├── Quick-Notes.md          # 快速笔记（最新在最前）
│   ├── Todo.md                 # 待办事项（Markdown checkbox）
│   ├── .ai-life-state.json    # 用户状态（打卡/习惯/对话/节奏等）
│   ├── 碎碎念.md               # 随想
│   └── attachments/            # 媒体附件
├── 01-Daily/                   # 日记（日报/周报/月报）
├── 02-Notes/
│   ├── 工作笔记/
│   ├── 情感日记/
│   ├── 生活趣事/
│   ├── 读书笔记/
│   ├── 影视笔记/
│   └── 语音日记/
├── 03-Finance/                 # 财务（仅管理员）
└── _Karvis/
    ├── user_config.json        # 用户配置
    ├── memory/memory.md        # AI 长期记忆
    └── logs/decisions.jsonl    # 决策日志（不含用户原文）
```

### 4.2 系统级数据

```
data/_karvis_system/
├── users.json                  # 用户注册表
├── tokens.json                 # Web 访问令牌
└── usage_log.jsonl             # LLM 用量日志
```

### 4.3 关键数据模型

**`state.json`**（用户状态，频繁读写）：

```json
{
  "messages": [],              // 最近对话（FIFO 10条）
  "compressed_summary": "",    // 旧对话压缩摘要
  "checkin": {},               // 打卡状态
  "checkin_stats": {},         // 打卡统计
  "mood_scores": [],           // 情绪评分序列
  "active_book": {},           // 当前在读书籍
  "active_media": {},          // 当前在看影视
  "active_experiment": {},     // 当前习惯实验
  "pending_decisions": [],     // 待复盘决策
  "daily_top3": [],            // 每日 Top 3
  "scheduler": {
    "intent_queue": [],        // 今日意图队列
    "user_rhythm": {}          // 用户作息节奏
  }
}
```

**`user_config.json`**（用户配置，低频读写）：

```json
{
  "nickname": "小明",
  "ai_name": "Karvis",
  "soul_override": "",
  "role": "user",
  "storage_mode": "local",
  "onedrive": {},
  "skills": { "mode": "blacklist", "list": [] },
  "info": {},
  "onboarding_step": 0,
  "preferences": {
    "morning_report": true,
    "evening_checkin": true,
    "companion_enabled": true
  }
}
```

---

## 五、认证体系

双层认证：**用户令牌**（UUID v4，24h 过期）+ **管理员密钥**（静态环境变量）。
详细的认证方式、Token 传递优先级和错误响应格式见 [API 参考](api-reference.md)。

---

## 六、告警体系

| 类型 | 触发条件 | 渠道 |
|------|---------|------|
| 慢请求 | 连续 N 次超过 20s（可配） | 企微推送管理员 |
| 处理异常 | handler 抛出异常 | 企微推送管理员 |
| 月度预算 | 超 80%（默认 ¥50/月） | 企微推送管理员 |
| 冷却机制 | 同类告警 300s 内不重复 | — |

---

## 七、日志系统

- **统一时间戳**：所有模块 `_log()` 输出 `HH:MM:SS [request_id] message`
- **Request ID**：8 位 hex，贯穿单次请求全链路
- **Web 日志查看器**：分组视图（按 RID 聚合）/ 原始视图 / 错误聚合
- **过滤**：关键词 / 用户 ID / 日志级别（ERROR/WARNING）
- **外部噪音过滤**：SSH 扫描、安全探测、错误请求码自动屏蔽
- **werkzeug**：设为 ERROR 级别，抑制 startup banner
