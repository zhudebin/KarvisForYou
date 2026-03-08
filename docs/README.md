# KarvisForAll 文档中心

> **版本**: V12 — 统一架构  
> **更新时间**: 2026-03-01  
> **定位**: 运行在企业微信上的多用户 AI 生活助手，数据存储在 Obsidian（本地/OneDrive）

---

## 文档导航

| 文档 | 说明 | 适合谁 |
|------|------|--------|
| [项目 README](../README.md) | 快速上手、部署、环境变量 | 新用户 / 部署者 |
| [架构详解](architecture.md) | 系统架构、模块关系、处理流水线、数据模型 | 开发者 / AI 助手 |
| [技能手册](skills-reference.md) | 全部 43 个 Skill 的功能说明与参数 | 开发者 / 用户 |
| [API 参考](api-reference.md) | 所有 HTTP 端点的请求/响应格式、认证方式 | 前端开发 / 集成 |
| [技能开发指南](skill-development.md) | 如何新增一个 Skill 模块 | 开发者 |
| [运维手册](operations.md) | 部署、日常运维、备份恢复、故障排查 | 运维 / 管理员 |
| [设计决策](设计决策.md) | 20 个架构决策记录 (ADR) | 架构评审 |
| [需求规格](requirements.md) | 完整 PRD — 功能/非功能需求 | 产品 / 开发 |
| [已知问题](known-issues.md) | Bug 跟踪、优化迭代方向 | 开发 / 运维 |
| [版本历史](../CHANGELOG.md) | 版本演进与变更记录 | 所有人 |

---

## 迭代记录

| 文档 | 内容 |
|------|------|
| [Web 优化 — 速记过滤与记忆查看](iterations/Web优化-速记过滤与记忆查看.md) | 用户旅程审计 + 代码级实施方案 |
| [Web 管理后台功能梳理](iterations/Web管理后台-功能梳理与优化方案.md) | 管理能力缺口分析 |

---

## 项目结构

```
KarvisForAll/
├── src/                    # 核心源码
│   ├── app.py              # Flask 主应用 + 消息网关 + V8 调度引擎
│   ├── brain.py            # AI 大脑 — LLM 多模型路由 + 决策解析
│   ├── config.py           # 统一配置（25+ 环境变量）
│   ├── prompts.py          # Prompt 模板管理中心
│   ├── skill_loader.py     # Skill 热加载器
│   ├── storage.py          # 存储抽象工厂（Local / OneDrive）
│   ├── local_io.py         # 本地文件 IO
│   ├── onedrive_io.py      # OneDrive Graph API IO
│   ├── memory.py           # 记忆系统（三级缓存 + 对话压缩）
│   ├── user_context.py     # 多用户上下文隔离
│   ├── web_routes.py       # Web 路由（用户页面 + 管理 API）
│   ├── wework_crypto.py    # 企微消息加解密
│   ├── finance_utils.py    # 财务工具库
│   ├── skills/             # 24 个技能模块（43 个 Skill）
│   ├── web_static/         # 前端页面（10 HTML + Chart.js）
│   └── prompts_example/    # Prompt 模板示例
├── deploy/                 # 部署配置（Docker / SCF / Scheduler）
├── scripts/                # 运维脚本（备份等）
├── tests/                  # 测试用例
├── docs/                   # 项目文档（你在这里）
├── .env.example            # 环境变量模板
├── CHANGELOG.md            # 版本历史
└── README.md               # 项目入口
```
