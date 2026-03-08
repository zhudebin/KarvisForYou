# 技能开发指南

> 如何为 KarvisForAll 新增一个 Skill 模块。

---

## 概述

KarvisForAll 使用 **Skill 热加载架构**：在 `src/skills/` 目录下创建 `.py` 文件，导出 `SKILL_REGISTRY` 字典，系统启动时自动发现并注册。

**一个 Skill 的完整生命周期**：

```
1. 创建文件 skills/my_feature.py
2. 实现 handler 函数
3. 导出 SKILL_REGISTRY
4. 在 prompts.py 添加 Prompt 描述
5. 在 prompts.py 的 RULES 中添加触发规则
6. 重启服务（自动加载）
```

---

## 快速上手：5 分钟创建一个 Skill

以创建一个「每日金句」skill 为例：

### Step 1: 创建文件

```python
# src/skills/daily_quote.py

from datetime import datetime, timezone, timedelta

_BEIJING_TZ = timezone(timedelta(hours=8))

def _log(msg):
    ts = datetime.now(_BEIJING_TZ).strftime("%H:%M:%S")
    print(f"{ts} [DailyQuote] {msg}", flush=True)


def handle_quote(params: dict, state: dict, ctx) -> dict:
    """
    生成每日金句。

    参数:
        params: LLM 决策输出的 JSON 参数
        state:  用户 state.json（可读写）
        ctx:    UserContext 实例

    返回:
        dict，可包含:
        - reply: str        — 回复给用户的文字
        - state_patch: dict — 要合并到 state 的字段
        - memory_updates: list — 长期记忆更新操作
        - quick_reply: str  — 快速回复（不经过 Flash 加工）
    """
    topic = params.get("topic", "生活")
    _log(f"生成金句, topic={topic}, user={ctx.user_id}")

    # 这里可以直接返回 reply，也可以读写文件
    return {
        "reply": f"今日金句主题「{topic}」— 具体内容由 LLM 在 Prompt 中生成",
        "state_patch": {
            "last_quote_date": datetime.now(_BEIJING_TZ).strftime("%Y-%m-%d")
        }
    }


# ====== 注册 ======
SKILL_REGISTRY = {
    "quote.generate": {
        "handler": handle_quote,
        "visibility": "public",       # public / preview / private
        "description": "生成每日金句",
    }
}
```

### Step 2: 添加 Prompt 描述

在 `src/prompts.py` 的 `SKILL_PROMPT_LINES` 字典中添加：

```python
SKILL_PROMPT_LINES["quote.generate"] = [
    "- **quote.generate**: 生成每日金句",
    '  输出: {"skill":"quote.generate","topic":"主题关键词"}',
]
```

### Step 3: 添加触发规则

在 `src/prompts.py` 的对应 RULES 段中添加触发条件：

```python
# 在 RULES_CORE 或新建 RULES_QUOTES 中
"""
### 金句
- 用户说"来个金句"/"每日一句"时 → quote.generate
"""
```

### Step 4: 重启服务

```bash
sudo systemctl restart karvisforall
```

系统启动时 `skill_loader.py` 会自动扫描并加载新模块，日志会显示模块数增加。

---

## Handler 函数签名

```python
def handler(params: dict, state: dict, ctx: UserContext) -> dict:
```

### 输入参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `params` | dict | LLM 决策输出的 JSON 参数（如 `text`, `category`, `topic` 等） |
| `state` | dict | 用户 `state.json` 的完整内容，可直接修改 |
| `ctx` | UserContext | 用户上下文，包含 IO、路径、权限等 |

### `ctx` 常用属性和方法

```python
ctx.user_id          # str  — 用户标识
ctx.nickname         # str  — 用户昵称
ctx.base_dir         # str  — 用户数据根目录
ctx.IO               # Storage 实例（LocalFileIO 或 OneDriveIO）
ctx.is_admin         # bool — 是否管理员
ctx.storage_mode     # str  — "local" 或 "onedrive"
ctx.is_skill_allowed("skill.name")  # bool — 检查技能权限
```

### `ctx.IO` 常用方法

```python
# 文件读写
content = ctx.IO.read_text(ctx.base_dir, "00-Inbox/Quick-Notes.md")
ctx.IO.write_text(ctx.base_dir, "path/to/file.md", content)

# JSON 读写
data = ctx.IO.read_json(ctx.base_dir, "path/to/data.json")
ctx.IO.write_json(ctx.base_dir, "path/to/data.json", data)

# Obsidian 笔记操作
ctx.IO.append_to_quick_notes(ctx.base_dir, "新笔记内容")
ctx.IO.append_to_section(ctx.base_dir, "path/to/file.md", "## 段落标题", "追加内容")

# 目录操作
files = ctx.IO.list_children(ctx.base_dir, "02-Notes/工作笔记")

# 二进制文件
ctx.IO.upload_binary(ctx.base_dir, "attachments/photo.jpg", binary_data)
data = ctx.IO.download_binary(ctx.base_dir, "attachments/photo.jpg")
```

### 返回值

Handler 返回一个 dict，所有字段均为可选：

| 字段 | 类型 | 说明 |
|------|------|------|
| `reply` | str | 回复给用户的文字（经 Flash 加工后发送） |
| `quick_reply` | str | 直接回复（不经 Flash 加工） |
| `state_patch` | dict | 合并到 state.json 的字段 |
| `memory_updates` | list | 长期记忆操作，格式见下方 |
| `agent_context` | str | Agent Loop 模式下的中间结果（不直接回复用户） |

### `memory_updates` 格式

```python
[
    {"action": "add", "section": "偏好", "content": "喜欢喝咖啡"},
    {"action": "update", "section": "工作", "content": "新的工作信息（覆盖整段）"},
    {"action": "delete", "section": "偏好", "keyword": "喝茶"},
]
```

---

## 注册方式

### 简单注册（仅 handler）

```python
SKILL_REGISTRY = {
    "skill.name": handler_function,
}
```

默认 `visibility = "public"`。

### 完整注册（带元数据）

```python
SKILL_REGISTRY = {
    "skill.name": {
        "handler": handler_function,
        "visibility": "public",        # public / preview / private
        "description": "功能描述",
    }
}
```

### 一个文件多个 Skill

```python
SKILL_REGISTRY = {
    "book.create": {"handler": handle_create, "visibility": "public"},
    "book.excerpt": {"handler": handle_excerpt, "visibility": "public"},
    "book.thought": {"handler": handle_thought, "visibility": "public"},
    "book.summary": {"handler": handle_summary, "visibility": "public"},
}
```

---

## Visibility 控制

三种可见级别：`public`（所有人可用）、`preview`（提示"敬请期待"）、`private`（仅管理员）。
完整说明和用户黑白名单机制见 [技能手册 · 权限说明](skills-reference.md#权限说明)。

---

## 多步骤（Multi-Step）Skill

LLM 可以在一次决策中输出多个步骤：

```json
{
  "steps": [
    {"skill": "note.save", "text": "保存内容"},
    {"skill": "classify.archive", "category": "work", "title": "工作记录", "text": "内容"}
  ],
  "reply": "已保存并归档"
}
```

brain.py 会按顺序执行每个 step 的 handler，合并所有 `state_patch` 和 `memory_updates`。

---

## Agent Loop（continue 机制）

如果 handler 返回 `agent_context`，brain.py 会将其注入下一轮 LLM 调用，最多循环 5 轮：

```python
def handle_read(params, state, ctx):
    file_path = params.get("path")
    content = ctx.IO.read_text(ctx.base_dir, file_path)
    return {
        "agent_context": f"文件内容:\n{content}"
    }
```

LLM 在下一轮可以基于文件内容做进一步决策（读更多文件、生成回复等）。

---

## 最佳实践

1. **命名规范**：`模块.动作`，如 `book.create`、`todo.add`、`finance.query`
2. **日志规范**：使用统一的 `_log()` 函数，包含时间戳和模块标识
3. **错误处理**：handler 内部 try/catch，返回 `reply` 告知用户错误，而非抛异常
4. **并发读取**：需要读多个文件时使用 `ThreadPoolExecutor`
5. **State 最小化**：只在 state 中存必要的运行时数据，持久化内容写文件
6. **隐私保护**：决策日志（`decisions.jsonl`）不记录用户原文，只记录技术字段
7. **安全边界**：所有文件操作必须在 `ctx.base_dir` 范围内

---

## 调试技巧

```bash
# 查看 skill 加载情况
sudo journalctl -u karvisforall --no-pager -n 10 -o cat | grep SkillLoader

# 查看某个 skill 的执行日志
sudo journalctl -u karvisforall --no-pager -n 100 -o cat | grep "DailyQuote"

# 通过 Web API 查看所有已注册 skill
curl -s "http://127.0.0.1:9000/api/admin/users/{uid}/skills?admin_token={token}" | python3 -m json.tool
```
