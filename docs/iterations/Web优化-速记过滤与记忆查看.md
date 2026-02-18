---
tags: [karvisforall, iteration, web]
updated: 2026-02-18
version: 2
---

# Web 优化方案 V2：让 Web 端真正服务于"个人数字生活管家"

## 零、核心反思：Web 端存在的意义

> V1 只解决了两个点——速记过滤和记忆查看。V2 需要回答一个更根本的问题：
> **这个 Web 端为什么要存在？**

KarvisForAll 的核心交互在企微——用户通过对话与管家交流。Web 端不是对话的替代品，
它的本质是 **生活的回放与确认**：

| 维度 | 企微端（输入） | Web 端（输出） |
|------|--------------|--------------|
| 角色 | 你和管家的对话 | 管家帮你整理的生活 |
| 核心动作 | 说（记录/指令/闲聊） | 看（回顾/确认/发现） |
| 价值感来源 | "管家理解我" | "我的生活被好好管理了" |

一个好的管家，除了听你说话，还应该定期让你知道：
1. **我对你的了解**（记忆） — 认知透明
2. **你的生活碎片**（速记） — 值得回看的内容，不是聊天日志
3. **你的情绪轨迹**（情绪） — 看见自己
4. **你的任务进展**（待办） — 有条有理
5. **你的深度记录**（日记/笔记） — 结构化沉淀

当前 Web 端的问题：它呈现的不是"管家整理的生活"，而是"原始数据的罗列"。
速记里全是"你好""嗯"，记忆不可见，情绪页面找不到，新用户打开全是零——
用户看不到管家在帮自己管理什么。

---

## 一、问题全景（来自体验审计）

### 1.1 两个底线 Bug

| # | 问题 | 根因 | 用户感受 |
|---|------|------|---------|
| B-1 | 情绪日记详情 404 | `web_routes.py:298` `os.path.basename()` 截断 `emotion/` 前缀，在 `daily_notes_dir` 查找 → 文件不存在 | 点了打不开，产品坏了 |
| B-2 | notes.html Markdown 链接嵌套 | 先替换 `[text](url)` 再匹配裸 URL → 已替换的 href 被二次匹配 → `<a>` 嵌套 | 链接点不了/显示乱 |

### 1.2 四个核心体验问题

| # | 问题 | 影响面 | 与"数字管家"目标的关系 |
|---|------|--------|---------------------|
| E-1 | **速记信噪比极低** | 每个用户每天 | 管家记了一堆废话，不像在管理生活 |
| E-2 | **记忆完全不可见** | 每个用户 | 管家不让你知道他了解你多少 |
| E-3 | **情绪页面无入口** | 有情绪数据的用户 | 管家帮你记了情绪但藏起来不给你看 |
| E-4 | **新用户空状态体验差** | 每个新用户 | 管家让你进门看到的是空荡荡的房间 |

### 1.3 七个体验优化项

| # | 问题 | 描述 |
|---|------|------|
| U-1 | 导航不一致 | mood.html 底部导航与其他页不同 |
| U-2 | 技术栈混用 | notes.html 用原生 JS+XHR，其他页 Alpine+fetch |
| U-3 | 日记页缺"月报" Tab | 后端有 monthly 但前端没筛选 |
| U-4 | 全部只读 | 无法操作，只能看 |
| U-5 | 概览速记预览不可点击 | 看到但跳不过去 |
| U-6 | 详情加载无反馈 | 无 loading 态 |
| U-7 | 无搜索功能 | 没法找内容 |

### 1.4 八个细节问题

B-2、D-1~D-8（背景色不统一、safe-area、Chart.js 内存泄漏、归档按钮偏小、无 favicon、XSS、登录竞态、CDN 版本）。

---

## 二、深度思考：优先级应该怎么排

### 2.1 从"个人数字生活管家"目标出发

不是所有问题都同等重要。用"数字管家"的隐喻来排：

| 优先级 | 隐喻 | 对应问题 |
|--------|------|---------|
| **最高：管家的基本功** | 管家记的东西不能全是废话 | E-1 速记过滤 |
| **最高：管家的透明度** | 管家要让主人知道"我了解你多少" | E-2 记忆可见 |
| **高：不能摔跤** | 管家带你去某个房间，门打不开 | B-1 情绪 404 |
| **高：房间要找得到** | 有个房间存在但找不到入口 | E-3 情绪入口 |
| **高：第一印象** | 新客人来了看到空房子 | E-4 空状态引导 |
| **中：地板颜色统一** | 技术栈/导航/样式一致性 | U-1, U-2, D-1 |
| **中：日常便利** | 点了能跳转，加载有反馈 | U-3, U-5, U-6 |
| **低：高级功能** | 搜索、写入、PWA | U-4, U-7 |
| **低：边角** | favicon、CDN、safe-area | D-2~D-8 |

### 2.2 成本-收益分析

| 任务 | 代码改动 | 用户感知提升 | 技术风险 |
|------|---------|------------|---------|
| 速记过滤 | +60 行 brain.py + prompts.py | ★★★★★ 每次打开都感受到 | 低（Flash 失败兜底写入） |
| 记忆页面 | +160 行 新文件 | ★★★★★ 核心差异化功能 | 低（只读，新页面不影响旧逻辑） |
| 情绪 404 修复 | +5 行 web_routes | ★★★★ 消灭报错 | 极低 |
| 情绪入口 + 导航统一 | ~30 行 改 2 个 HTML | ★★★★ 功能可达 | 低 |
| 空状态引导 | ~30 行 dashboard.html | ★★★ 新用户转化 | 极低 |
| notes.html 技术栈统一 | ~100 行 重写 | ★★ 开发者感知，用户几乎无感 | 中（全量重写有风险） |
| 月报 Tab | +5 行 daily.html | ★★ 有月报数据的用户 | 极低 |
| 搜索/写入 | +200 行+ | ★★★ 但需大量设计 | 高（写入涉及数据一致性） |

---

## 三、分阶段方案

### 阶段 1（立即执行）：管家的基本功 + 底线修复

> 目标：让用户打开 Web 觉得"管家做事靠谱"

#### 1-A：速记智能过滤（E-1）

**问题精确定位**：`brain.py:515-517`，除 system 和 checkin 外所有消息无条件写入 Quick-Notes。

**解法**：两阶段过滤——规则预过滤（同步，快速跳过明确无用消息）+ Qwen-Flash 后置判断（异步，回复之后执行，不影响响应延迟）。

**为什么用 Flash 而不是纯规则**：正则匹配能处理"你好""给我查看链接"这些明确模式，但面对边缘情况（"嗯今天还行""就那样吧""没什么"）很难准确判断。Flash 对自然语言的理解远超正则，且成本极低（~0.001 元/次），放在回复后异步执行零延迟影响。

#### 阶段一：规则预过滤（同步，回复前）

明确的系统指令类消息直接跳过，无需 LLM 判断：

```python
# ── 规则预过滤：明确不该记录的 skill ──

_SKIP_NOTE_SKILLS = frozenset({
    # 待办系统已处理
    "todo.add", "todo.done", "todo.list",
    # 习惯系统已处理
    "habit.propose", "habit.nudge", "habit.status", "habit.complete",
    # 决策系统已处理
    "decision.record", "decision.review", "decision.list",
    # 读书/影视系统已处理（结构化存储到各自目录）
    "book.create", "book.excerpt", "book.thought", "book.summary", "book.quotes",
    "media.create", "media.thought",
    # 纯系统指令
    "web.token",
    "settings.nickname", "settings.soul", "settings.info",
    # 深度分析（结果单独存储）
    "deep.dive",
})
```

这些 skill 对应的消息已被各自子系统结构化处理，写入 Quick-Notes 纯属冗余。

#### 阶段二：Qwen-Flash 后置判断（异步，回复后）

对于规则没拦住的消息（主要是 `ignore` 和 `classify.archive`），用 Flash 做一道语义判断：

```python
# ── prompts.py 新增 ──

FLASH_NOTE_FILTER = """判断以下用户消息是否值得记录到"速记"（个人生活碎片时间线）。

速记应该记录：
- 生活感受、心情、见闻（"今天面试挺顺利""刚看完三体太震撼了"）
- 有信息量的事实（"下周二要去北京出差""猫今天吐了"）
- 想法、灵感、反思（"感觉最近太累了需要休息"）

速记不应该记录：
- 打招呼/寒暄（"你好""早""晚安"）
- 纯指令/查询（"帮我查一下""看看待办""给我链接"）
- 无信息量的回复（"好的""嗯""收到""ok""行"）
- 系统交互（URL、token、确认指令）

只回复 YES 或 NO，不要解释。"""


# ── brain.py 新增 ──

def _flash_filter_and_save(payload, state, ctx, primary_skill):
    """回复后异步执行：用 Flash 判断消息是否值得写入 Quick-Notes"""
    text = _extract_user_text(payload)
    if not text or not text.strip():
        return

    try:
        result = call_llm([
            {"role": "system", "content": prompts.FLASH_NOTE_FILTER},
            {"role": "user", "content": text}
        ], model_tier="flash", max_tokens=5, temperature=0)

        should_save = result and result.strip().upper().startswith("YES")

        if should_save:
            _save_to_quick_notes(payload, state, ctx)
            _log(f"[Brain][NoteFilter] Flash 判断写入: {text[:40]}...")
        else:
            _log(f"[Brain][NoteFilter] Flash 判断跳过: {text[:40]}...")
    except Exception as e:
        # Flash 失败时兜底写入（宁可多记不可漏记）
        _log(f"[Brain][NoteFilter] Flash 判断失败，兜底写入: {e}")
        _save_to_quick_notes(payload, state, ctx)
```

#### 整合：改动 brain.py 主流程

**原来**（line 515-517）：所有非 system/非 checkin 消息无条件写入。

**现在**：分两步走。

```python
# ── 第 515-517 行替换为 ──
primary_skill = _get_primary_skill(decision)
if payload.get("type") != "system" \
   and primary_skill not in ("checkin.answer", "checkin.skip", "checkin.cancel", "checkin.start"):
    # 规则预过滤：明确的系统指令类直接跳过
    if primary_skill in _SKIP_NOTE_SKILLS:
        _log(f"[Brain][NoteFilter] 规则跳过: skill={primary_skill}")
    else:
        # 其余消息延迟到回复后，由 Flash 异步判断
        _pending_note_filter = True  # 标记，后面用
```

**回复发送后**（line 577-593 区域，`send_fn` 之后），加入异步 Flash 过滤：

```python
# ── 在 send_fn(reply) 之后、_save_state_and_memory 之前 ──
if _pending_note_filter:
    _executor.submit(_flash_filter_and_save, payload, state, ctx, primary_skill)
```

利用已有的 `_executor`（ThreadPoolExecutor），与 state/memory 保存并发执行。

#### 关键设计决策

- **classify.archive 也过 Flash** — 归档类消息大部分有价值，但也有边缘情况（"嗯那就这样吧"被归档到 misc），让 Flash 统一把关。
- **note.save 不过滤** — 用户主动说"帮我记一下"，一定要记。但 note.save 在 `_execute_steps` 已跳过（line 803-806），Quick-Notes 统一写入走的是 line 515-517 路径，这里自然会被 Flash 判断。
- **mood.generate / voice.journal 不在 `_SKIP_NOTE_SKILLS`** — 情绪/语音日记的原始输入有信息量，让 Flash 判断是否值得保留在速记时间线。
- **Flash 失败兜底写入** — 宁可多记不可漏记。Flash 挂了就回退到原来的全量写入行为。
- **max_tokens=5, temperature=0** — 只需 YES/NO，极快极省。单次成本约 ¥0.001。
- **放在回复后** — 用户体感零延迟。Flash 本身也很快（~200ms），但即使慢也不影响用户。

#### 效果预估

以 CaiWenWen 的实际数据为例：
- "你好" → ignore → Flash 判断 → **NO，跳过** ✓
- "给我查看链接" → web.token → 规则预过滤 → **直接跳过** ✓
- 一段 URL → ignore → Flash 判断 → **NO，跳过** ✓（Flash 能识别纯 URL 无信息量）
- "今天面试挺顺利" → ignore → Flash 判断 → **YES，写入** ✓
- "帮我记个待办：交报告" → todo.add → 规则预过滤 → **直接跳过** ✓
- "刚看完三体太震撼了" → classify.archive → Flash 判断 → **YES，写入** ✓
- "嗯" → ignore → Flash 判断 → **NO，跳过** ✓

与纯规则方案对比：纯规则的 `_NOISE_PATTERNS` 正则能覆盖 ~70% 噪音，但对"嗯今天还行""就那样吧"这类自然语言无能为力。Flash 覆盖率 ~95%+，且面对新模式不需要更新正则。

#### 成本估算

| 项目 | 数值 |
|------|------|
| 每条消息 Flash 调用 | ~200 input tokens + ~2 output tokens |
| 单次成本 | ~¥0.001（百炼 qwen-flash 价格） |
| 日均消息量（单用户） | ~20-50 条 |
| 日成本（单用户） | ~¥0.02-0.05 |
| 月成本（10 用户） | ~¥6-15 |

完全可以忽略不计。

#### 1-B：修复情绪日记 404（B-1）

**改动**：`web_routes.py` 第 290-307 行的 `/api/daily/<path:filename>` 处理：

```python
@api_bp.route("/daily/<path:filename>", methods=["GET"])
@require_auth
def api_daily_detail(filename, user_id=None):
    ctx = _get_ctx(user_id)

    # 检测情绪日记路径
    if filename.startswith("emotion/"):
        safe_name = os.path.basename(filename)
        if not safe_name.endswith(".md"):
            safe_name += ".md"
        filepath = os.path.join(ctx.emotion_notes_dir, safe_name)
    else:
        safe_name = os.path.basename(filename)
        if not safe_name.endswith(".md"):
            safe_name += ".md"
        filepath = os.path.join(ctx.daily_notes_dir, safe_name)

    content = _read_file_safe(filepath)
    if not content:
        return jsonify({"error": "文件不存在"}), 404
    return jsonify({"content": content, "filename": safe_name})
```

**+5 行实质改动**，消灭一个 100% 复现的 404。

#### 1-C：修复 Markdown 链接嵌套（B-2）

**改动**：`notes.html` 中 Markdown 渲染逻辑，调换裸 URL 和 `[text](url)` 的替换顺序，或在裸 URL 匹配时排除已在 `href="..."` 中的 URL。

推荐方案：先匹配裸 URL，再匹配 `[text](url)`，最终结果中 `[text](url)` 的替换会覆盖裸 URL 的替换。或者更简单——用负向后行断言排除 `href="` 开头的 URL。

---

### 阶段 2（紧接着做）：认知透明 + 可达性

> 目标：让用户感到"管家真的在关注我，而且告诉我他知道什么"

#### 2-A：记忆查看页面（E-2）

**这是整个 Web 端最具差异化的功能。** 没有哪个 AI 助手会让你直接看到"它对你的认知画像"。这正是"数字管家"的核心信任基础。

**后端 API**：

```
GET /api/memory
→ 200:
{
  "sections": [
    { "title": "用户画像", "icon": "👤", "items": ["职业：产品经理", "城市：深圳"] },
    { "title": "重要的人", "icon": "👥", "items": ["小明: 大学室友..."] },
    { "title": "偏好", "icon": "❤️", "items": ["喜欢猫", "不喜欢被叫全名"] },
    { "title": "近期关注", "icon": "📌", "items": ["在准备面试"] },
    { "title": "重要事件", "icon": "⭐", "items": ["2025-12 入职新公司"] }
  ],
  "total_items": 12,
  "last_updated": "2026-02-18T14:30:00"
}
→ 200 (空记忆): { "sections": [], "total_items": 0, "last_updated": null }
```

**解析逻辑**（`web_routes.py` 新增 ~40 行）：

```python
SECTION_ICONS = {
    "用户画像": "👤", "重要的人": "👥", "偏好": "❤️",
    "近期关注": "📌", "重要事件": "⭐",
}

@api_bp.route("/memory", methods=["GET"])
@require_auth
def api_memory(user_id=None):
    ctx = _get_ctx(user_id)
    raw = _read_file_safe(ctx.memory_file)
    if not raw or raw.strip() in ("", "# Memory", "# Memory\n"):
        return jsonify({"sections": [], "total_items": 0, "last_updated": None})

    sections, total = [], 0
    for block in raw.split("\n## ")[1:]:
        lines = block.strip().split("\n")
        title = lines[0].strip()
        items = [l.lstrip("- ").strip() for l in lines[1:] if l.strip().startswith("- ")]
        total += len(items)
        sections.append({
            "title": title,
            "icon": SECTION_ICONS.get(title, "📋"),
            "items": items,
        })

    # 文件修改时间作为 last_updated
    mtime = os.path.getmtime(ctx.memory_file) if os.path.exists(ctx.memory_file) else None
    last_updated = datetime.fromtimestamp(mtime, _BEIJING_TZ).isoformat() if mtime else None

    return jsonify({"sections": sections, "total_items": total, "last_updated": last_updated})
```

**前端页面** `memory.html`（~120 行，Alpine.js + Tailwind，风格与现有页面统一）：

```
┌─────────────────────────────┐
│       🧠 Karvis 的记忆        │
│    "这是我对你的了解"          │
├─────────────────────────────┤
│                             │
│  👤 用户画像                  │
│  ┌───────────────────────┐  │
│  │ · 职业：产品经理        │  │
│  │ · 城市：深圳           │  │
│  └───────────────────────┘  │
│                             │
│  👥 重要的人                  │
│  ┌───────────────────────┐  │
│  │ · 小明: 大学室友        │  │
│  │ · 妈妈: ...            │  │
│  └───────────────────────┘  │
│                             │
│  ...更多分区...              │
│                             │
│  ┌───────────────────────┐  │
│  │ 💡 有不对的地方？         │  │
│  │ 在企微告诉我就好~        │  │
│  └───────────────────────┘  │
├─────────────────────────────┤
│ 📊概览 📝速记 ✅待办 📖日记 📁笔记 │
└─────────────────────────────┘
```

**空状态**（新用户还没有记忆）：

```
🧠 Karvis 的记忆

  目前还是空白的~

  多和我聊聊，我会慢慢记住：
  · 你是谁、做什么工作
  · 你身边重要的人
  · 你的偏好和习惯
  · 你最近在关注什么

  去企微聊两句？
```

**入口设计（DD-020 不变）**：Dashboard 概览页顶部，昵称区域下方新增记忆入口卡片。

```html
<!-- dashboard.html 顶部新增 -->
<a href="/web/memory" class="block bg-white rounded-xl p-3 shadow-sm border border-warm-100">
  <div class="flex items-center justify-between">
    <div>
      <span class="text-sm font-medium text-warm-800">🧠 Karvis 的记忆</span>
      <p class="text-xs text-warm-400 mt-0.5" x-text="memoryHint"></p>
    </div>
    <span class="text-warm-300">›</span>
  </div>
</a>
```

其中 `memoryHint` 由 Dashboard API 新增 `memory_summary` 字段（"3 个画像 · 2 个偏好"或"还没有记忆，去聊聊~"）。

**为什么不放底部导航**：记忆是"偶尔查看、确认无误就走"的低频操作。占一个底部 Tab 位会挤压高频功能（概览/速记/待办/日记/笔记都是日常使用的）。放在 Dashboard 头部更自然——"我的概览"里自然包含"AI 对我的认知"。

#### 2-B：情绪入口可达 + 导航统一（E-3 + U-1）

**问题**：`mood.html` 存在且功能完整（30 天曲线 + 统计 + 日记列表），但无入口。且 mood.html 的底部导航与其他页面不同。

**方案**：

1. **统一所有页面底部导航**为 5 个：📊概览 📝速记 ✅待办 📖日记 📁笔记
2. **情绪入口**通过 Dashboard 情绪曲线区域点击跳转：

```html
<!-- dashboard.html 情绪曲线区域 -->
<a href="/web/mood" class="block bg-white rounded-xl p-4 shadow-sm">
  <p class="text-xs text-warm-500 mb-2">最近 7 天情绪</p>
  <canvas id="moodChart" height="100"></canvas>
  <p class="text-xs text-warm-400 mt-2 text-right">查看详情 ›</p>
</a>
```

3. **日记页情绪 Tab** 的条目点击同样跳转 mood.html（而非触发 404 的 daily detail）。

**为什么不加底部 Tab**：情绪查看是周级/月级频率。5 个 Tab 已经是移动端底部导航的上限。情绪作为"概览的延伸"更合理。

#### 2-C：新用户空状态引导（E-4）

**Dashboard 空状态改造**：当四个数据都为零/空时，显示引导卡片替代空数据。

```html
<template x-if="isEmpty">
  <div class="bg-white rounded-xl p-6 shadow-sm text-center">
    <p class="text-3xl mb-3">👋</p>
    <h2 class="text-lg font-bold text-warm-800 mb-2">欢迎来到你的数字空间</h2>
    <p class="text-sm text-warm-500 mb-4">在企微里和 Karvis 说点什么，这里就会热闹起来~</p>
    <div class="text-left bg-warm-50 rounded-lg p-4 space-y-2 text-sm text-warm-700">
      <p>💬 说说今天的事 → 自动记录速记</p>
      <p>📝 "帮我记个待办" → 创建待办事项</p>
      <p>📖 "刚看完三体" → 影视笔记</p>
      <p>😊 每天的打卡 → 追踪你的情绪</p>
    </div>
  </div>
</template>
```

**判断空状态逻辑**：

```javascript
get isEmpty() {
  return !this.data.note_count_today
    && !this.data.todo_total
    && !this.data.streak
    && !this.data.latest_daily
    && (!this.data.mood_chart || !this.data.mood_chart.length)
    && (!this.data.recent_notes || !this.data.recent_notes.length);
}
```

---

### 阶段 3（体验打磨）：一致性与便利性

> 目标：消灭"不统一"的割裂感，增加日常便利

#### 3-A：notes.html 技术栈统一（U-2 + D-1）

将 notes.html 从原生 JS + XHR + 手写 CSS 改为 Alpine.js + fetch + Tailwind，与其他页面保持一致。统一背景色为 `#fdf8f6`。保留入场动画效果（用 Tailwind transition 实现）。

**优先级中等的原因**：用户视觉感知差异不大（背景色 `#f5f3f0` vs `#fdf8f6` 肉眼几乎分不出），但代码维护成本降低。

#### 3-B：日记页补"月报" Tab（U-3）

`daily.html` 筛选 Tab 增加"月报"：

```html
<!-- 现有：全部 / 日报 / 周报 / 情绪 -->
<!-- 新增：全部 / 日报 / 周报 / 月报 / 情绪 -->
```

+5 行改动。

#### 3-C：概览页速记预览可点击（U-5）

最近速记区域改为 `<a href="/web/notes">`，点击跳转速记页。

#### 3-D：详情加载反馈（U-6）

日记/笔记详情点击后显示 loading spinner：

```html
<div x-show="detailLoading" class="flex justify-center py-8">
  <div class="animate-spin rounded-full h-6 w-6 border-2 border-warm-300 border-t-warm-600"></div>
</div>
```

---

### 阶段 4（远期方向）：从"看"到"做"

| 方向 | 说明 | 与"数字管家"的关系 | 复杂度 |
|------|------|-------------------|--------|
| 全局搜索 | 跨速记/笔记/日记搜索 | 管家帮你找到过去的记忆 | 中（需后端索引） |
| 待办操作 | Web 端完成/新增待办 | 管家不只是展示清单，还能协作 | 中（写入一致性） |
| 速记补充 | Web 端快速新增速记 | 不依赖企微也能记录 | 低 |
| PWA | 添加到主屏幕 | 像原生 App 一样触达 | 低 |
| iPhone 适配 | safe-area-inset-bottom | 底部导航不被刘海遮挡 | 极低 |
| XSS 清理 | marked.js + DOMPurify | 安全底线 | 低 |

---

## 四、实施路线与改动清单

### 阶段 1 — 立即

| 序 | 任务 | 文件 | 改动量 | 解决问题 |
|----|------|------|--------|---------|
| 1 | 速记过滤 | `brain.py`, `prompts.py` | +60 行 | E-1 |
| 2 | 情绪 404 修复 | `web_routes.py` | +5 行 | B-1 |
| 3 | 链接嵌套修复 | `notes.html` | +3 行 | B-2 |

### 阶段 2 — 紧接着

| 序 | 任务 | 文件 | 改动量 | 解决问题 |
|----|------|------|--------|---------|
| 4 | 记忆 API | `web_routes.py` | +40 行 | E-2 |
| 5 | 记忆页面 | `memory.html`(新建) | ~120 行 | E-2 |
| 6 | Dashboard 记忆入口 | `dashboard.html` | +15 行 | E-2 |
| 7 | Dashboard API 增加 memory_summary | `web_routes.py` | +10 行 | E-2 |
| 8 | 统一导航 + 情绪入口 | `dashboard.html`, `mood.html` | ~30 行 | E-3, U-1 |
| 9 | 空状态引导 | `dashboard.html` | +30 行 | E-4 |

### 阶段 3 — 体验打磨

| 序 | 任务 | 文件 | 改动量 | 解决问题 |
|----|------|------|--------|---------|
| 10 | notes.html 技术栈统一 | `notes.html` | ~100 行重写 | U-2, D-1 |
| 11 | 月报 Tab | `daily.html` | +5 行 | U-3 |
| 12 | 速记预览可点击 | `dashboard.html` | +3 行 | U-5 |
| 13 | 详情 loading | `daily.html`, `archive.html` | +10 行 | U-6 |

---

## 五、设计决策

### DD-019: 速记两阶段过滤（V2 更新）

**背景**：Quick-Notes 原始设计是"统一收件箱，不丢消息"（DD-009）。体验审计发现信噪比问题是**新老用户共同最大痛点**（审计评分拉低的首要原因）。

**决策**：在写入 Quick-Notes 前增加两阶段过滤——规则预过滤（同步，Skill 维度跳过）+ Qwen-Flash 后置判断（异步，回复后执行，语义级过滤）。

**关键约束**：
- 规则预过滤零延迟，明确的系统指令类直接跳过
- Flash 判断放在 `send_fn(reply)` 之后，利用已有 `_executor` 异步执行，用户体感零延迟
- Flash 失败兜底写入（宁可多记不可漏记）
- max_tokens=5, temperature=0，单次 ~¥0.001
- classify.archive 也过 Flash（大部分有价值但有边缘情况）
- mood.generate / voice.journal 不在预过滤跳过列表（有信息量的原始输入）

**回退策略**：关闭 Flash 过滤只需注释一行提交代码（`_executor.submit` 那行），回退到全量写入。或把 `_SKIP_NOTE_SKILLS` 对应的也改回全量写入。

### DD-020: 记忆入口放 Dashboard 而非底部 Tab（不变）

**理由同 V1**：记忆是低频操作（偶尔看看），不值得占一级导航位。Dashboard 头部是自然入口——"我的概览"包含"AI 对我的认知"。

### DD-021: 情绪入口通过 Dashboard 曲线跳转（新增）

**背景**：mood.html 功能完整但无入口（审计 E-3）。

**决策**：不新增底部 Tab。Dashboard 情绪曲线区域改为可点击跳转 `/web/mood`。日记页情绪类条目也链接到 mood 详情。

**理由**：情绪查看是周/月级频率。5 Tab 是移动端导航上限。情绪是"概览的延伸"，从概览入口更符合用户心智。

### DD-022: 空状态策略——引导而非隐藏（新增）

**背景**：当前 `x-show` 在无数据时隐藏整个区域，导致新用户看到空白页面（审计 E-4，首次体验 3/10）。

**决策**：新用户空状态时显示引导卡片，告诉用户"去企微做什么 → 这里会出现什么"，建立 企微输入→Web 展示 的心智模型。

**理由**：空状态是产品的"第零次使用"。用户不知道该做什么 = 流失。引导卡片的成本极低（纯前端），但对首次体验的提升是从 3/10 到 6/10 的跃升。

---

## 六、总结：V2 与 V1 的差异

| 维度 | V1 | V2 |
|------|----|----|
| 视角 | 从两个具体问题出发 | 从"Web 端存在的意义"出发 |
| 覆盖范围 | 速记过滤 + 记忆查看 | 17 个问题的全景梳理 + 分阶段方案 |
| 优先级依据 | 改动大小 | 与"数字管家"目标的贴合度 × 用户感知提升 |
| 情绪入口 | 未涉及 | 纳入阶段 2（E-3 + U-1） |
| 空状态 | 未涉及 | 纳入阶段 2（E-4） |
| Bug 修复 | 未涉及 | 纳入阶段 1（B-1 + B-2） |
| 技术方案 | 概要 | 精确到行号 + 代码示例 + 回退策略 + 成本估算 |
| 远期规划 | 无 | 搜索/写入/PWA 方向 |
| 设计决策 | DD-019, DD-020 | DD-019(更新), DD-020, DD-021(新), DD-022(新) |
