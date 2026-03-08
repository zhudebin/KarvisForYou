# API 参考

> 所有 HTTP 端点的完整说明，包括请求/响应格式、认证方式和示例。

---

## 认证方式

### 用户认证 (`require_auth`)

Token 传递方式（任选一）：

| 方式 | 示例 |
|------|------|
| Header | `X-Token: {token}` |
| Cookie | `karvis_token={token}` |
| Query | `?token={token}` |

**失败响应**：`401 {"error": "未登录或令牌已过期", "hint": "在企微中对 Karvis 说「给我查看链接」重新获取"}`

### 管理员认证 (`require_admin`)

Token 传递方式（任选一）：

| 方式 | 示例 |
|------|------|
| Header | `X-Admin-Token: {token}` |
| Cookie | `karvis_admin_token={token}` |
| Query | `?admin_token={token}` |

**失败响应**：`403 {"error": "管理员令牌无效"}`

---

## 核心端点

### `GET /` — 探活

```
响应: "Karvis is alive"
```

### `GET /health` — 深度健康检查

**无需认证**

```json
// 200 OK（healthy）或 503（degraded）
{
  "status": "healthy",
  "checks": {
    "deepseek_key": true,
    "qwen_key": true,
    "wework_token": true,
    "disk_free_gb": 29.6,
    "scheduler": true,
    "active_users": 5,
    "log_size_mb": 0.3,
    "msg_cache_size": 2,
    "uptime_s": 3600
  },
  "timestamp": "2026-03-01 08:30:00"
}
```

| 检查项 | 降级条件 |
|--------|---------|
| `disk_free_gb` | < 1 GB |
| `log_size_mb` | > 100 MB |
| `scheduler` | APScheduler 未运行 |

### `GET/POST /wework` — 企微 Webhook

- `GET`：URL 验证（企微配置回调时使用）
- `POST`：接收加密消息 → 解密 → 去重 → 异步转发到 `/process`

### `POST /process` — 内部异步处理

**仅内部调用**，不对外暴露。

```json
// 请求
{
  "type": "text|image|voice|video|link",
  "user": "user_id",
  "content": "消息内容",
  "msg_id": "企微消息ID",
  "media_id": "媒体文件ID"
}
```

### `POST /system` — 系统动作

**仅内部调用**（定时器/手动触发）。

```json
// 请求
{
  "action": "daily_init|scheduler_tick|refresh_cache|morning_report|todo_remind|evening_checkin|daily_report|reflect_push|mood_generate|weekly_review|monthly_review|nudge_check|companion_check",
  "user_id": "可选，指定用户"
}
```

---

## 认证 API

### `POST /api/auth/verify` — 验证令牌

```json
// 请求
{ "token": "uuid-token" }

// 成功响应
{ "valid": true, "user_id": "CaiWenWen", "nickname": "小文" }

// 失败响应
{ "valid": false, "expired": true }
```

---

## 用户 API

> 以下端点均需 **用户认证**（`require_auth`）

### `GET /api/dashboard` — 仪表盘

```json
{
  "nickname": "小文",
  "today_notes": 5,
  "todos": { "pending": 3, "done": 7, "total": 10 },
  "streak_days": 12,
  "mood_scores": [7, 8, 6, 7, 8, 9, 7],
  "recent_notes": [
    { "time": "14:30", "content": "...", "date": "2026-03-01" }
  ],
  "latest_daily": { "filename": "2026-03-01.md", "excerpt": "..." },
  "memory_summary": "工程师，养了一只猫..."
}
```

### `GET /api/notes` — 速记列表

**参数**：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `date` | string | 今天 | 日期筛选 `YYYY-MM-DD` |
| `limit` | int | 20 | 每页条数 |
| `offset` | int | 0 | 偏移量 |

```json
{
  "notes": [
    { "time": "14:30", "content": "今天天气不错", "date": "2026-03-01" }
  ],
  "total": 42,
  "has_more": true
}
```

### `GET /api/todos` — 待办列表

```json
{
  "pending": [
    { "text": "买菜", "due_date": "2026-03-02", "created": "2026-03-01" }
  ],
  "done": [
    { "text": "写周报", "completed": "2026-03-01" }
  ]
}
```

### `GET /api/daily` — 日记列表

```json
{
  "entries": [
    {
      "filename": "2026-03-01.md",
      "type": "daily",
      "date": "2026-03-01",
      "excerpt": "今天是充实的一天..."
    },
    {
      "filename": "周报-2026-03-01.md",
      "type": "weekly",
      "date": "2026-03-01"
    }
  ]
}
```

### `GET /api/daily/<filename>` — 日记详情

```json
{
  "filename": "2026-03-01.md",
  "content": "# 2026-03-01\n\n## 今日总结\n..."
}
```

`filename` 包含 `emotion/` 前缀时路由到 `02-Notes/情感日记/` 目录。

### `GET /api/archive` — 归档笔记列表

**参数**：`?category=work|emotion|fun|book|media|voice`

```json
{
  "notes": [
    { "filename": "工作周会记录.md", "category": "work", "date": "2026-03-01" }
  ]
}
```

### `GET /api/archive/<filename>` — 归档笔记详情

**参数**：`?category=work`

```json
{
  "filename": "工作周会记录.md",
  "content": "# 工作周会记录\n..."
}
```

### `GET /api/mood` — 情绪数据

```json
{
  "scores": [
    { "date": "2026-02-28", "score": 7 },
    { "date": "2026-03-01", "score": 8 }
  ],
  "diaries": [
    {
      "filename": "情绪日记-2026-03-01.md",
      "date": "2026-03-01",
      "excerpt": "今天整体心情不错..."
    }
  ]
}
```

### `GET /api/memory` — 长期记忆

```json
{
  "sections": [
    {
      "title": "用户画像",
      "icon": "👤",
      "items": ["工程师", "住在北京"],
      "last_updated": "2026-03-01"
    },
    {
      "title": "偏好",
      "icon": "❤️",
      "items": ["喜欢喝咖啡", "爱看科幻电影"]
    }
  ]
}
```

### `GET /api/books` — 读书笔记列表

### `GET /api/media` — 影视笔记列表

---

## 管理员 API

> 以下端点均需 **管理员认证**（`require_admin`）

### `GET /api/admin/users` — 用户列表

```json
{
  "users": [
    {
      "user_id": "CaiWenWen",
      "nickname": "小文",
      "created_at": "2026-02-28T10:00:00+08:00",
      "last_active": "2026-03-01T08:34:00+08:00",
      "message_count_today": 12,
      "total_messages": 156,
      "status": "active"
    }
  ],
  "total": 5
}
```

### `POST /api/admin/users/<uid>/suspend` — 挂起用户

```json
// 响应
{ "ok": true, "message": "用户已挂起" }
```

### `POST /api/admin/users/<uid>/activate` — 激活用户

```json
// 响应
{ "ok": true, "message": "用户已激活" }
```

### `GET /api/admin/users/<uid>/skills` — 查看技能配置

```json
{
  "mode": "blacklist",
  "list": ["finance.*"],
  "all_skills": [
    { "name": "note.save", "visibility": "public", "available": true },
    { "name": "finance.query", "visibility": "private", "available": false }
  ]
}
```

### `POST /api/admin/users/<uid>/skills` — 更新技能配置

```json
// 请求
{
  "mode": "blacklist",
  "list": ["finance.*", "deep.dive"]
}

// 响应
{ "ok": true }
```

### `GET /api/admin/usage` — LLM 用量统计

```json
{
  "total_tokens": 1234567,
  "by_user": { "CaiWenWen": 500000, "KongKongd": 734567 },
  "by_model": { "deepseek-v3.2": 1000000, "qwen-flash": 234567 },
  "by_date": { "2026-03-01": 150000, "2026-02-28": 200000 }
}
```

### `GET /api/admin/stats` — 综合统计面板

**参数**：`?days=14`（统计天数）

```json
{
  "token": {
    "daily_trend": [...],
    "model_distribution": {...},
    "user_usage": {...},
    "today_summary": { "prompt_tokens": 50000, "completion_tokens": 20000 },
    "cost_estimate": { "today": 0.56, "month": 12.3, "budget": 50 },
    "prompt_inflation": [...]
  },
  "latency": {
    "avg": 3.2,
    "p50": 2.8,
    "p90": 5.1,
    "p99": 12.3,
    "max": 29.2,
    "slow_count": 3,
    "waterfall": [...]
  },
  "skills": {
    "top15": [...],
    "by_user": {...}
  },
  "errors": {
    "top20": [
      {
        "signature": "KeyError: 'xxx'",
        "count": 3,
        "last_seen": "2026-03-01 08:00:00",
        "sample_traceback": "..."
      }
    ]
  }
}
```

### `GET /api/admin/logs` — 查看日志

**参数**：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `lines` | int | 200 | 返回行数 |
| `keyword` | string | — | 关键词过滤 |
| `level` | string | — | 日志级别（ERROR/WARNING） |
| `user` | string | — | 用户 ID 过滤 |

```json
{
  "lines": [
    "08:34:29 [fdba0e77] [/process] 开始处理 type=text, user=CaiWenWen",
    "08:34:58 [fdba0e77] [handle_message] brain 返回: reply=有(53字)"
  ],
  "project": "karvisforall",
  "total": 200
}
```

---

## Web 页面路由

| 路由 | 页面 | 认证 |
|------|------|------|
| `GET /web/` | → 重定向到 `/web/login` | 无 |
| `GET /web/login` | 登录页 | 无 |
| `GET /web/dashboard` | 仪表盘 | 用户 Token |
| `GET /web/notes` | 速记 | 用户 Token |
| `GET /web/todos` | 待办 | 用户 Token |
| `GET /web/daily` | 日记 | 用户 Token |
| `GET /web/archive` | 归档笔记 | 用户 Token |
| `GET /web/mood` | 情绪 | 用户 Token |
| `GET /web/memory` | 记忆 | 用户 Token |
| `GET /web/admin` | 管理后台 | Admin Token |
| `GET /web/logs` | 日志监控 | Admin Token |
| `GET /web/static/<path>` | 静态资源 | 无 |
