# 技能手册

> 全部 24 个 Skill 模块、43 个 Skill 的完整说明。

---

## 概览

| 分类 | Skill 数 | 模块 |
|------|---------|------|
| 📝 信息收集 | 6 | note_save, classify_archive, voice_journal, book_notes, media_notes |
| ✅ 效率工具 | 7 | todo_manage, daily_report, weekly_review, monthly_review, decision_track |
| 🧠 自我洞察 | 7 | checkin_flow, mood_diary, reflect, deep_dive, habit_coach |
| 🔧 系统管理 | 7 | settings, web_token, internal_ops, dynamic_engine |
| 💰 财务（管理员） | 4 | finance_import, finance_query, finance_report, finance_snapshot |
| — 内置 | 1 | `ignore`（纯闲聊，不执行任何操作） |

---

## 权限说明

| Visibility | 含义 | 普通用户行为 |
|-----------|------|------------|
| `public` | 公开 | 正常使用，可通过 `settings.skills` 开关 |
| `preview` | 预览 | 提示"敬请期待"，不注入 Prompt |
| `private` | 私有 | 完全隐藏，返回"没有这个功能" |

用户可通过黑白名单进一步控制：
- **黑名单模式**（默认）：`list` 中的 skill 被禁用，其余全部可用
- **白名单模式**：仅 `list` 中的 skill 可用
- 支持通配符，如 `finance.*` 匹配所有财务 skill

---

## 📝 信息收集

### `note.save` — 快速笔记

| 属性 | 值 |
|------|---|
| **模块** | `skills/note_save.py` |
| **Visibility** | public |
| **功能** | 将用户消息保存到 `00-Inbox/Quick-Notes.md` |
| **支持类型** | 文字、图片（Markdown 图片链接）、语音（ASR 文字）、视频/文件（附件链接） |
| **格式** | `## HH:MM 内容 ---`，新条目插入头部 |
| **去重** | 相同内容不重复写入 |

**LLM 输出参数**：
```json
{ "skill": "note.save", "text": "要保存的内容" }
```

---

### `classify.archive` — 分类归档

| 属性 | 值 |
|------|---|
| **模块** | `skills/classify_archive.py` |
| **Visibility** | public |
| **功能** | 将消息按类别归档到 `02-Notes/` 对应子目录 |
| **分类** | `work`→工作笔记、`emotion`→情感日记、`fun`→生活趣事、`misc`→碎碎念 |
| **特性** | 支持 `merge=true` 将补充内容合并到上一条同类条目 |

**LLM 输出参数**：
```json
{
  "skill": "classify.archive",
  "category": "work|emotion|fun|misc",
  "title": "条目标题",
  "text": "条目内容",
  "merge": false
}
```

---

### `voice.journal` — 语音日记

| 属性 | 值 |
|------|---|
| **模块** | `skills/voice_journal.py` |
| **Visibility** | public |
| **功能** | 长语音（>200 字 ASR）自动整理为结构化日记 |
| **输出** | 分段去口语化、主题提取、情绪轨迹、关键事件、提到的人 |
| **存储** | `02-Notes/语音日记/语音日记-{日期}-{序号}.md` |

**LLM 输出参数**：
```json
{ "skill": "voice.journal", "text": "ASR 转录文本" }
```

---

### `book.create` — 创建/切换书籍

| 属性 | 值 |
|------|---|
| **模块** | `skills/book_notes.py` |
| **Visibility** | public |
| **功能** | 创建书籍笔记文件，LLM 自动填充作者/分类/简介 |
| **特性** | 更新书单索引，已存在且有感想时自动转到 `book.thought` |
| **存储** | `02-Notes/读书笔记/{书名}.md` |

**LLM 输出参数**：
```json
{
  "skill": "book.create",
  "book_name": "书名",
  "author": "作者",
  "category": "分类",
  "brief": "简介"
}
```

### `book.excerpt` — 书摘

追加到 `✂️ 摘录` 段落。参数：`{ "skill": "book.excerpt", "text": "摘录内容" }`

### `book.thought` — 读书感想

追加到 `💡 我的思考` 段落。参数：`{ "skill": "book.thought", "text": "感想" }`

### `book.summary` — 读书总结

AI 生成总结（核心观点/思考脉络/关联阅读/一句话总结）。参数：`{ "skill": "book.summary" }`

### `book.quotes` — 金句提炼

从笔记中提炼 3-5 条适合分享的金句。参数：`{ "skill": "book.quotes" }`

---

### `media.create` — 创建/切换影视

| 属性 | 值 |
|------|---|
| **模块** | `skills/media_notes.py` |
| **Visibility** | public |
| **功能** | 创建影视笔记（电影/剧集/纪录片/动画），LLM 填充导演/类型/年份/简介 |
| **存储** | `02-Notes/影视笔记/{片名}.md` |

### `media.thought` — 影视感想

追加到 `💭 我的感想` 段落。

---

## ✅ 效率工具

### `todo.add` — 添加待办

| 属性 | 值 |
|------|---|
| **模块** | `skills/todo_manage.py` |
| **Visibility** | public |
| **功能** | 添加待办到 `Todo.md`，支持截止日期和定时提醒 |

**LLM 输出参数**：
```json
{
  "skill": "todo.add",
  "text": "待办内容",
  "due_date": "2026-03-15",
  "remind_at": "2026-03-14 09:00"
}
```

### `todo.done` — 完成待办

支持关键词模糊匹配和序号批量完成（`"2-7"` / `"1,3,5"`）。

```json
{ "skill": "todo.done", "text": "买菜" }
```

### `todo.list` — 查看待办

返回带序号的待办清单 + 最近已完成项。

内含 `check_reminders()` 供定时任务调用，实现到期提醒/预警/过期通知。

---

### `daily.generate` — 日报生成

| 属性 | 值 |
|------|---|
| **模块** | `skills/daily_report.py` |
| **Visibility** | public |
| **功能** | 并发收集当天全部数据，AI 生成日报 |
| **数据源** | Quick-Notes + 4 类归档 + 碎碎念 |
| **输出** | 总结/情绪/标签/亮点/洞察 |
| **存储** | `01-Daily/{日期}.md` |

---

### `weekly.review` — 周回顾

| 属性 | 值 |
|------|---|
| **模块** | `skills/weekly_review.py` |
| **Visibility** | public |
| **功能** | 收集过去 7 天全部数据，AI 生成周回顾 |
| **数据源** | Quick-Notes + 归档 + 日报 + 打卡 + 情绪评分 + 决策日志 |
| **输出** | 情绪曲线/碎片连线/数据统计/洞察/建议 |
| **存储** | `01-Daily/周报-{日期}.md` |

---

### `monthly.review` — 月度回顾

| 属性 | 值 |
|------|---|
| **模块** | `skills/monthly_review.py` |
| **Visibility** | public |
| **功能** | 收集整月数据（含周报摘要、打卡统计），AI 生成月度成长报告 |
| **输出** | 情绪月历/趋势/高光低谷/人际变化/数据看板/洞察/建议 |
| **存储** | `01-Daily/月报-{YYYY-MM}.md` |

---

### `decision.record` — 记录决策

| 属性 | 值 |
|------|---|
| **模块** | `skills/decision_track.py` |
| **Visibility** | public |
| **功能** | 记录重要决策，设定复盘日期（默认 3 天后） |

```json
{
  "skill": "decision.record",
  "topic": "要不要换工作",
  "decision": "决定先面试看看",
  "mood": "纠结但偏乐观",
  "review_after_days": 3
}
```

### `decision.review` — 决策复盘

用户回复决策结果后写入复盘，移到历史（保留最近 20 条）。

### `decision.list` — 查看决策

查看待复盘的决策列表，标注到期/剩余天数。内含 `get_due_decisions()` 供早报注入。

---

## 🧠 自我洞察

### `checkin.start` — 启动打卡

| 属性 | 值 |
|------|---|
| **模块** | `skills/checkin_flow.py` |
| **Visibility** | public |
| **功能** | 启动 4 题晚间打卡流程 |
| **问题** | Q1:今天做了什么 → Q2:状态评分(1-10) → Q3:有什么纠结 → Q4:脑海中常见念头 |
| **存储** | 写入 `01-Daily/{日期}.md`，更新 `state.mood_scores` 和 `checkin_stats` |

相关 skill：`checkin.answer`（回答）、`checkin.skip`（跳过）、`checkin.cancel`（取消）

---

### `mood.generate` — 情绪日记

| 属性 | 值 |
|------|---|
| **模块** | `skills/mood_diary.py` |
| **Visibility** | public |
| **功能** | 从当天全部数据中提取情绪脉络，生成情绪日记 |
| **数据源** | 全天消息 + 打卡数据 + 决策日志 + 深度自问回答 |
| **输出** | 评分/标签/走势/关键时刻/洞察 |
| **存储** | `02-Notes/情感日记/情绪日记-{日期}.md` |
| **评分逻辑** | 打卡评分优先级高于 AI 推断 |

---

### `reflect.push` — 深度自问

| 属性 | 值 |
|------|---|
| **模块** | `skills/reflect.py` |
| **Visibility** | public |
| **功能** | 推送今日深度自问题目 |
| **题库** | 10 个维度 × 20 题 = 200 道 |
| **维度** | 自我认知/恐惧/内在对话/人际关系/时间/欲望/情绪疗愈/价值观/成长/梦想 |
| **选题策略** | 维度轮转 → 维度内随机 → 90 天去重 → 心情适配（低分时优先疗愈类） |

相关 skill：`reflect.answer`（回答，Flash 生成温柔回应）、`reflect.skip`（跳过，重置连续天数）、`reflect.history`（查看最近 N 天记录）

---

### `deep.dive` — 主题深潜

| 属性 | 值 |
|------|---|
| **模块** | `skills/deep_dive.py` |
| **Visibility** | public |
| **功能** | 跨时间线搜索全历史数据，AI 生成深度分析报告 |
| **数据源** | Quick-Notes + 30 天归档 + memory.md + 决策日志 + 情绪评分 |
| **模型** | 使用 Think 层（深度推理） |
| **输出** | 时间线/趋势/洞察/建议，可选保存到文件 |

---

### `habit.propose` — 微习惯实验

| 属性 | 值 |
|------|---|
| **模块** | `skills/habit_coach.py` |
| **Visibility** | public |
| **功能** | 提议新微习惯实验 |

```json
{
  "skill": "habit.propose",
  "name": "早起喝水",
  "hypothesis": "起床后喝水能提升早晨精神状态",
  "trigger": "起床",
  "micro_action": "喝一杯温水",
  "duration_days": 14
}
```

相关 skill：`habit.nudge`（触发时提议微行动）、`habit.status`（查看进度）、`habit.complete`（结束实验+总结）

---

## 🔧 系统管理

### `settings.*` — 用户设置

| Skill | 功能 | 示例指令 |
|-------|------|---------|
| `settings.nickname` | 设置昵称 | "叫我小明" |
| `settings.ai_name` | 给 AI 起名 | "叫你小K" |
| `settings.soul` | 设置 AI 风格 | "说话幽默一点" |
| `settings.info` | 记录个人信息 | "我在北京，养了一只猫" |
| `settings.skills` | 管理功能开关 | "关掉财务功能" |

---

### `web.token` — 生成 Web 链接

生成带 token 的 Web 数据查看链接，有效期 24 小时。用户说"给我查看链接"触发。

---

### `internal.read` / `internal.search` / `internal.list` — 文件操作（Agent Loop）

| Skill | 功能 | 安全限制 |
|-------|------|---------|
| `internal.read` | 并发读取最多 5 个文件 | 只能访问用户 base_dir |
| `internal.search` | 关键词搜索笔记（最近 14 天） | scope: quick_notes/archives/all |
| `internal.list` | 列出目录文件（最多 30 个） | 只能访问用户 base_dir |

支持 `continue=true` 多轮循环（最多 5 轮），返回 `agent_context` 而非直接回复用户。

---

### `dynamic` — 动态操作引擎

通用原子操作引擎，支持 6 种 op：

| Op | 功能 | 示例 |
|----|------|------|
| `state.set` | 设置 state 字段 | 更新 daily_top3 |
| `state.delete` | 删除 state 字段 | 清除 active_experiment |
| `state.push` | 追加到 state 数组 | 添加 decision_history |
| `file.read` | 读取文件 | 读取 memory.md |
| `file.write` | 覆写文件 | 更新配置文件 |
| `file.append` | 追加到文件 | 追加日志 |

安全机制：字段白名单 + 目录白名单，单次最多 10 个 action。

---

## 💰 财务模块（管理员专属）

> 以下 4 个 Skill 的 visibility 均为 `private`，仅管理员可用。

### `finance.import` — 数据导入

扫描 `03-Finance/inbox/` 目录，解析 iCost xlsx 文件，去重合并到 `finance_data.json`。

### `finance.query` — 收支查询

即时查询收支/余额/明细，支持多种 `time_range`（this_month / last_month / this_week / custom 等）。

### `finance.snapshot` — 资产快照

查询资产状况，支持 5 种模式：summary / compare / by_category / by_channel / trend。

### `finance.monthly` — 财务月报

生成完整月报：自动导入 → 收支总览+环比 → Top 10 → 资产变动 → 趋势 → AI 深度洞察 → 写入 Obsidian + 推送企微摘要。
