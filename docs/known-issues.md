---
tags: [karvisforall, issues]
updated: 2026-03-01
---

# 已知问题与迭代方向

> 功能实现记录见 [CHANGELOG.md](../CHANGELOG.md)

## 已修复

| ID | 问题 | 修复方式 |
|----|------|----------|
| I-001 | 健康检查 GET / 日志刷屏 | 添加 Werkzeug `_HealthCheckFilter` 过滤 `GET /` 和 `GET /health` 的 access log |
| I-002 | V8 容器重启后下午推送"早安"晨报 | `_daily_init()` 新增过期意图跳过：生成意图后检查 `now > latest` 则标记 `skipped` |
| I-003 | 节奏学习 `avg_wake_time` 被下午消息污染 | 入口过滤：wake_time 只接受 05:00~12:00；sleep_time 只接受 20:00~04:00 |

## 待观察

| ID | 优先级 | 问题 | 备注 |
|----|--------|------|------|
| I-004 | P3 | memory.md 缓存延迟：手动编辑后不会立即生效 | 缓存 TTL 到期后自动刷新。可手动 curl `/system?action=refresh_cache` 立即刷新 |
| I-005 | P3 | 同一用户极快连发消息可能导致 state 写入竞争 | 已有 per-user Lock 缓解，但极端并发场景仍有理论风险 |

## 优化迭代方向

### P1 — 功能增强

| ID | 方向 | 说明 | 复杂度 |
|----|------|------|:------:|
| O-001 | SKILLS 按需裁剪 | 按场景裁剪 skill 描述可降 prompt_tokens ~30% | 中 |
| O-002 | V8 Flash LLM 评估 | 规则引擎跑稳后，引入 Flash LLM 判断推送时机 | 中 |
| O-003 | dynamic custom.* 聚合查询 | 让 LLM 能回答"这周喝了多少杯水"之类问题 | 低 |
| O-004 | V8 节奏数据可视化 | 起床/入睡/活跃时段可视化到 Web | 低 |
| O-005 | 批量导入历史数据 | 新用户导入历史笔记到 Quick-Notes | 中 |
| O-010 | 管理员用户详情页 | 单用户视图：消息趋势、活跃时段、技能分布 | 中 |
| O-011 | UptimeRobot 外部监控 | 监控 `/health`，宕机时告警 | 低 |

### P2 — 架构演进

| ID | 方向 | 说明 | 复杂度 |
|----|------|------|:------:|
| O-006 | 本地文件 → SQLite | state.json/users.json 迁移到 SQLite | 中 |
| O-007 | Prompt 工程自动化 | 构建测试框架验证 LLM 输出 | 中 |
| O-008 | 用户规模扩展 | 10+ 人需优化定时任务并发、缓存淘汰、日志分片 | 高 |
| O-009 | GitHub 开源 + CI/CD | Actions 自动测试 + 自动部署 | 中 |
