---
tags: [karvisforall, web, admin, ops]
updated: 2026-02-19
---

# Web 管理后台 — 功能梳理与优化方案

## 一、现状全景

### 页面结构

| 页面 | 路由 | 角色 | 功能 |
|------|------|------|------|
| login.html | `/web/login` | 用户 | Token 登录，支持 URL 参数自动填入 |
| dashboard.html | `/web/dashboard` | 用户 | 仪表盘：速记数、待办、打卡天数、记忆摘要、7天情绪曲线 |
| notes.html | `/web/notes` | 用户 | 速记时间线，按日期分组 + 分页 |
| todos.html | `/web/todos` | 用户 | 待办列表，全部/进行中/已完成三种视图 |
| daily.html | `/web/daily` | 用户 | 日记/周报/月报，Markdown 渲染，按类型 Tab 筛选 |
| archive.html | `/web/archive` | 用户 | 归档笔记（工作/情感/生活/读书/影视/语音）6 个分类 |
| mood.html | `/web/mood` | 用户 | 30 天情绪曲线 + 情绪日记详情 |
| memory.html | `/web/memory` | 用户 | 长期记忆分区折叠展示 |
| **admin.html** | `/web/admin` | 管理员 | 用量统计 + 用户列表管理 |
| **logs.html** | `/web/logs` | 管理员 | 实时日志 + 统计监控面板 |

### API 端点清单

**用户 API（12 个）**：auth/verify, dashboard, notes, todos, daily(list+detail), archive(list+detail), mood, memory, books, media

**管理员 API（6 个）**：
- `GET /api/admin/users` — 用户列表
- `GET /api/admin/usage` — LLM 用量（admin.html 在用）
- `GET /api/admin/stats` — 综合统计（logs.html 在用）
- `GET /api/admin/logs` — 服务日志
- `POST /api/admin/users/<uid>/suspend` — 挂起用户
- `POST /api/admin/users/<uid>/activate` — 激活用户

### 已有能力 ✅

| 维度 | 能力 |
|------|------|
| 查日志 | 双项目切换、关键词/级别过滤、自动刷新、终端风格高亮 |
| 看成本 | Token 趋势图、按模型/用户分布、自动成本估算 |
| 监控延迟 | 平均/P50/P90/P99、延迟瀑布图、>15s 红色告警 |
| 技能分析 | TOP15 技能热力图、按用户 skill 分布 |
| 用户管理 | 列表查看、挂起/激活、每日消息限额（50 条） |
| 健康检查 | `GET /` 返回 alive |

---

## 二、缺失的管理能力

从「查问题 → 定位原因 → 修复 → 防止复发」的运维闭环角度梳理：

### 2.1 问题发现层（主动告警）

**现状**：只有前端被动展示（需要打开页面才看得到），没有主动推送。

**建议**：
- [ ] **企微告警推送**：错误率突增、延迟异常、服务重启时，自动发企微消息给管理员
  - 触发条件：连续 3 次请求 > 20s / 出现 Traceback / 进程重启
  - 实现：在 brain.py 保存阶段加检查 → 调用现有的企微发消息接口
  - 优先级：⭐⭐⭐（最能减少发现问题的延迟）

### 2.2 问题定位层（排障工具）

**现状**：日志只能看原始文本，没有按请求维度关联。

**建议**：
- [ ] **请求追踪视图**：在延迟瀑布图中，点击某条请求可以展开查看完整链路
  - 数据来源：decisions.jsonl 已有 input/thinking/skill/reply/elapsed
  - 展示：输入 → LLM 思考 → 技能选择 → Skill 执行结果 → 回复内容
  - 优先级：⭐⭐⭐
- [ ] **错误日志聚合**：将 `[ERROR]` / `Traceback` 自动提取、去重、计数
  - 类似 Sentry 的错误分组，避免在大量日志中翻找
  - 优先级：⭐⭐

### 2.3 用户运维层

**现状**：管理员能看到用户列表和统计，但无法查看具体用户数据来排查问题。

**建议**：
- [ ] **管理员用户详情页**：`/web/admin/user/<uid>`
  - 查看该用户的最近 N 条决策日志（input + skill + reply + 延迟）
  - 查看该用户的 state.json 关键字段（checkin_pending, mood_scores 等）
  - 查看该用户的 Token 消耗趋势
  - 不展示速记/日记等隐私内容，只展示运营诊断数据
  - 优先级：⭐⭐
- [ ] **用户消息限额调整**：允许管理员单独调整某用户的每日消息上限
  - 当前是全局 50 条，但可能有用户需要更多
  - 优先级：⭐

### 2.4 成本管控层

**现状**：已有 Token 趋势和成本估算，但不够精细。

**建议**：
- [ ] **成本预算与预警**：设定月度预算线（如 ¥50），超过 80% 时告警
  - 在统计面板顶部加一个预算进度条
  - 优先级：⭐⭐
- [ ] **Prompt 膨胀检测**：当 prompt_tokens 持续 > 12K 时标红
  - 说明 memory 或对话历史过长，需要清理
  - 可以在统计面板加一个 "prompt_tokens 分布直方图"
  - 优先级：⭐⭐
- [ ] **模型降级建议**：统计 flash 够用但走了 main 的情况
  - 如 ignore/note.save 等简单 skill 的调用，如果都走 DeepSeek 是浪费
  - 优先级：⭐

### 2.5 系统稳定性层

**现状**：有健康检查端点，但没有持续监控。

**建议**：
- [ ] **Uptime 监控**：接入 UptimeRobot / 自建 cron 定期 ping `/`
  - 服务挂了能第一时间发现
  - 优先级：⭐⭐⭐（零成本高收益）
- [ ] **OneDrive API 成功率统计**：日志中已有 `[OneDrive] 读取OK` / `写入OK` 和耗时
  - 从日志中正则提取 OneDrive 操作的成功率和 P90 延迟
  - OneDrive 是最大的外部依赖，它慢整个系统就慢
  - 优先级：⭐⭐
- [ ] **进程存活检测**：post-receive 部署后自动检测新进程是否正常响应
  - KarvisForAll 的 hook 中没有 healthcheck（Karvis Docker 版已有）
  - 优先级：⭐⭐

### 2.6 数据运营层

**现状**：有基础的用户列表和消息计数，但缺乏增长和活跃分析。

**建议**：
- [ ] **用户活跃度热力图**：按日展示每个用户的消息数，类似 GitHub 贡献图
  - 快速识别谁在活跃、谁流失了
  - 数据来源：users.json 中的 daily_counts
  - 优先级：⭐
- [ ] **功能使用漏斗**：从 skill 调用频次推断功能渗透率
  - 哪些 skill 从没被用过？需要优化 prompt 引导还是功能本身不好用？
  - 优先级：⭐

---

## 三、admin.html 与 logs.html 职责重叠

当前 admin.html 和 logs.html 都有 Token 用量统计，且 admin.html 的成本计算逻辑（前端简化版 `tokens/1M * 0.5 * 7`）和 logs.html 的统计面板（后端按模型精确计算）存在不一致。

**建议合并方案**：

| 页面 | 定位 | 保留内容 |
|------|------|----------|
| admin.html | **用户运营中心** | 用户列表 + 挂起/激活 + 用户详情（新增） |
| logs.html | **技术监控中心** | 日志 + Token/成本 + 延迟 + 技能 + 告警 |

- admin.html 中移除 LLM 用量统计部分，改为链接到 logs.html 的统计 Tab
- 统一成本计算逻辑到后端 `/api/admin/stats`

---

## 四、优先级排序（实施路线图）

### P0：立刻做（低成本高收益）
1. **Uptime 监控** — 接入免费的 UptimeRobot，5 分钟搞定
2. **企微告警推送** — 复用现有发消息接口，~30 行代码

### P1：近期做（提升排障效率）
3. **请求追踪视图** — 延迟瀑布图点击展开详情
4. **错误日志聚合** — Traceback 自动提取计数
5. **成本预算预警** — 月度预算线 + 80% 告警

### P2：后续做（精细化运营）
6. **管理员用户详情页** — 单用户诊断视图
7. **Prompt 膨胀检测** — prompt_tokens 分布监控
8. **OneDrive API 成功率** — 外部依赖监控

### P3：有空做（锦上添花）
9. admin/logs 职责合并
10. 用户活跃度热力图
11. 功能使用漏斗

---

## 五、技术实现备注

### 企微告警推送的实现思路

```python
# brain.py 中，process() 末尾的保存阶段加入：
if elapsed > 20:
    _send_admin_alert(f"⚠️ 慢请求 {elapsed:.1f}s\nuser={user_id}\nskill={skill}\ninput={text[:50]}")

# 复用 app.py 中已有的 _send_text_message() 函数
# ADMIN_USER_ID 从 config 读取
```

### 请求追踪视图的数据

decisions.jsonl 已有字段：`ts, input_type, input, thinking, skill, reply, has_memory_updates, elapsed_s`

前端只需在延迟瀑布图的每一行加 `@click` 展开，显示 `thinking`（LLM 为什么选了这个 skill）和 `reply`（实际回复了什么），无需后端改动，只需让 `/api/admin/stats` 返回更多字段。

### Prompt 膨胀检测

usage_log.jsonl 已有 `prompt_tokens` 字段，只需在前端统计面板加一个分布图（<4K / 4-8K / 8-12K / >12K），按日展示趋势。
