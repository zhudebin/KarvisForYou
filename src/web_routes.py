# -*- coding: utf-8 -*-
"""
KarvisForAll Web 路由 — API 接口 + 页面路由
所有 /web/* 和 /api/* 路由在此注册。
"""
import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Blueprint, request, jsonify, send_from_directory, redirect, url_for

from user_context import (
    verify_token, UserContext, get_all_users, update_user_status,
    SYSTEM_DIR, USAGE_LOG_FILE, DATA_DIR,
)
from config import ADMIN_TOKEN, LOG_FILE_KARVISFORALL, LOG_KARVIS_COMPOSE_DIR

_BEIJING_TZ = timezone(timedelta(hours=8))

web_bp = Blueprint("web", __name__)
api_bp = Blueprint("api", __name__)


def _log(msg):
    print(msg, file=sys.stderr, flush=True)


# ============================================================
# 鉴权中间件
# ============================================================

def _get_token_from_request():
    """从请求中提取 token（Header > Cookie > query param）"""
    token = request.headers.get("X-Token", "")
    if not token:
        token = request.cookies.get("karvis_token", "")
    if not token:
        token = request.args.get("token", "")
    return token


def require_auth(f):
    """用户鉴权装饰器：验证 token 并注入 user_id"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token_from_request()
        result = verify_token(token)
        if not result.get("valid"):
            _log(f"[WebAPI] 鉴权失败: token={token[:8] if token else 'empty'}..., "
                 f"expired={result.get('expired', False)}")
            return jsonify({"error": "令牌无效或已过期，请在企微中对 Karvis 说「给我查看链接」重新获取",
                            "expired": result.get("expired", False)}), 401
        kwargs["user_id"] = result["user_id"]
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """管理员鉴权装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "")
        if not token:
            token = request.args.get("admin_token", "")
        if not token:
            token = request.cookies.get("karvis_admin_token", "")
        if not ADMIN_TOKEN or token != ADMIN_TOKEN:
            _log(f"[WebAPI] 管理员鉴权失败")
            return jsonify({"error": "管理员令牌无效"}), 403
        return f(*args, **kwargs)
    return decorated


def _get_ctx(user_id):
    """快速获取用户上下文（不创建目录）"""
    return UserContext(user_id)


# ============================================================
# 用户 API — /api/*
# ============================================================

@api_bp.route("/auth/verify", methods=["POST"])
def api_auth_verify():
    """POST /api/auth/verify — 验证令牌"""
    data = request.get_json(force=True, silent=True) or {}
    token = data.get("token", "") or _get_token_from_request()
    result = verify_token(token)

    if not result.get("valid"):
        _log(f"[WebAPI] /api/auth/verify 失败: token={token[:8] if token else 'empty'}...")
        return jsonify({"valid": False, "expired": result.get("expired", False)})

    user_id = result["user_id"]
    ctx = _get_ctx(user_id)
    nickname = ctx.get_nickname() or user_id

    _log(f"[WebAPI] /api/auth/verify 成功: user={user_id}, nickname={nickname}")
    return jsonify({"valid": True, "user_id": user_id, "nickname": nickname})


@api_bp.route("/dashboard", methods=["GET"])
@require_auth
def api_dashboard(user_id=None):
    """GET /api/dashboard — 仪表盘概览数据"""
    ctx = _get_ctx(user_id)

    result = {
        "nickname": ctx.get_nickname() or user_id,
        "date": datetime.now(_BEIJING_TZ).strftime("%Y-%m-%d"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][
            datetime.now(_BEIJING_TZ).weekday()
        ],
    }

    # 速记统计
    try:
        qn = _read_file_safe(ctx.quick_notes_file)
        today_str = datetime.now(_BEIJING_TZ).strftime("%Y-%m-%d")
        today_notes = [s for s in qn.split("\n## ")[1:] if s.strip().startswith(today_str)]
        result["note_count_today"] = len(today_notes)
        # 最近 3 条预览
        recent = qn.split("\n## ")[1:4] if qn else []
        result["recent_notes"] = [s.strip()[:200] for s in recent]
    except Exception as e:
        _log(f"[WebAPI] dashboard 读取速记失败: {e}")
        result["note_count_today"] = 0
        result["recent_notes"] = []

    # 待办统计
    try:
        todo = _read_file_safe(ctx.todo_file)
        pending = len([l for l in todo.split('\n') if l.strip().startswith('- [ ]')])
        done = len([l for l in todo.split('\n') if l.strip().startswith('- [x]')])
        result["todo_pending"] = pending
        result["todo_done"] = done
        result["todo_total"] = pending + done
    except Exception:
        result["todo_pending"] = 0
        result["todo_done"] = 0
        result["todo_total"] = 0

    # 情绪曲线（最近 7 天）
    try:
        state = _read_state_safe(ctx)
        scores = state.get("mood_scores", [])
        result["mood_chart"] = scores[-7:] if scores else []
    except Exception:
        result["mood_chart"] = []

    # 打卡连续天数
    try:
        state = state if "state" in dir() else _read_state_safe(ctx)
        nudge = state.get("nudge_state", {})
        result["streak"] = nudge.get("streak", 0)
    except Exception:
        result["streak"] = 0

    # 最新日记
    try:
        daily_files = _list_files_safe(ctx.daily_notes_dir, "*.md")
        if daily_files:
            latest = sorted(daily_files, reverse=True)[0]
            result["latest_daily"] = {
                "file": latest,
                "date": latest.replace(".md", ""),
            }
        else:
            result["latest_daily"] = None
    except Exception:
        result["latest_daily"] = None

    # 记忆概要（section 数量 + 总条目数）
    try:
        mem_content = _read_file_safe(ctx.memory_file)
        if mem_content:
            mem_sections = [p for p in re.split(r'\n(?=## )', mem_content) if p.strip().startswith("## ")]
            mem_items = len([l for l in mem_content.split('\n') if l.strip().startswith("- ")])
            result["memory_summary"] = {"sections": len(mem_sections), "items": mem_items}
        else:
            result["memory_summary"] = None
    except Exception:
        result["memory_summary"] = None

    return jsonify(result)


@api_bp.route("/notes", methods=["GET"])
@require_auth
def api_notes(user_id=None):
    """GET /api/notes — 获取速记"""
    ctx = _get_ctx(user_id)
    date_filter = request.args.get("date", "")

    qn = _read_file_safe(ctx.quick_notes_file)
    if not qn:
        return jsonify({"notes": [], "has_more": False})

    # 按 ## 分割为条目
    sections = qn.split("\n## ")[1:]  # 跳过文件头部
    notes = []
    for s in sections:
        lines = s.strip().split("\n")
        if not lines:
            continue
        header = lines[0].strip()
        content = "\n".join(lines[1:]).strip()
        # 去掉尾部的分隔线 ---
        if content.endswith("---"):
            content = content[:-3].strip()


        # 日期筛选
        if date_filter and not header.startswith(date_filter):
            continue

        notes.append({
            "time": header,
            "content": content,
        })

    # 最新在前
    notes.reverse()
    # 分页（简单截断）
    limit = int(request.args.get("limit", "50"))
    offset = int(request.args.get("offset", "0"))
    total = len(notes)
    page = notes[offset:offset + limit]

    return jsonify({
        "notes": page,
        "total": total,
        "has_more": (offset + limit) < total,
    })


@api_bp.route("/todos", methods=["GET"])
@require_auth
def api_todos(user_id=None):
    """GET /api/todos — 获取待办"""
    ctx = _get_ctx(user_id)

    todo = _read_file_safe(ctx.todo_file)
    pending = []
    done = []

    for line in todo.split('\n'):
        line = line.strip()
        if line.startswith('- [ ]'):
            pending.append({"content": line[5:].strip(), "done": False})
        elif line.startswith('- [x]'):
            done.append({"content": line[5:].strip(), "done": True})

    return jsonify({"pending": pending, "done": done})


@api_bp.route("/daily", methods=["GET"])
@require_auth
def api_daily_list(user_id=None):
    """GET /api/daily — 获取日记/周报/月报列表"""
    ctx = _get_ctx(user_id)

    reports = []
    files = _list_files_safe(ctx.daily_notes_dir, "*.md")
    for f in sorted(files, reverse=True):
        name = f.replace(".md", "")
        rtype = "daily"
        if name.startswith("周报"):
            rtype = "weekly"
        elif name.startswith("月报"):
            rtype = "monthly"
        elif name.startswith("情绪"):
            rtype = "mood"
        reports.append({
            "file": f,
            "date": name,
            "type": rtype,
            "title": name,
        })

    # 也查情绪日记目录
    emotion_files = _list_files_safe(ctx.emotion_notes_dir, "*.md")
    for f in sorted(emotion_files, reverse=True):
        name = f.replace(".md", "")
        reports.append({
            "file": f"emotion/{f}",
            "date": name,
            "type": "mood",
            "title": name,
        })

    return jsonify({"reports": reports})


@api_bp.route("/daily/<path:filename>", methods=["GET"])
@require_auth
def api_daily_detail(filename, user_id=None):
    """GET /api/daily/{filename} — 获取日记详情"""
    ctx = _get_ctx(user_id)

    # 检测 emotion/ 前缀，路由到情绪日记目录
    if filename.startswith("emotion/"):
        safe_name = os.path.basename(filename)
        if not safe_name.endswith(".md"):
            safe_name += ".md"
        filepath = os.path.join(ctx.emotion_notes_dir, safe_name)
    else:
        # 安全检查：防止路径穿越
        safe_name = os.path.basename(filename)
        if not safe_name.endswith(".md"):
            safe_name += ".md"
        filepath = os.path.join(ctx.daily_notes_dir, safe_name)

    content = _read_file_safe(filepath)
    if not content:
        return jsonify({"error": "文件不存在"}), 404

    return jsonify({"content": content, "filename": safe_name})


@api_bp.route("/archive", methods=["GET"])
@require_auth
def api_archive_list(user_id=None):
    """GET /api/archive — 获取归档笔记列表"""
    ctx = _get_ctx(user_id)
    category = request.args.get("category", "")

    categories = {
        "work": ctx.work_notes_dir,
        "emotion": ctx.emotion_notes_dir,
        "fun": ctx.fun_notes_dir,
        "book": ctx.book_notes_dir,
        "media": ctx.media_notes_dir,
        "voice": ctx.voice_journal_dir,
    }

    notes = []
    dirs_to_scan = {category: categories[category]} if category and category in categories else categories

    for cat, dir_path in dirs_to_scan.items():
        files = _list_files_safe(dir_path, "*.md")
        for f in sorted(files, reverse=True):
            # 读取第一行作为标题
            filepath = os.path.join(dir_path, f)
            first_line = _read_first_line(filepath)
            notes.append({
                "file": f,
                "category": cat,
                "title": first_line or f.replace(".md", ""),
                "date": _extract_date_from_filename(f),
            })

    return jsonify({"notes": notes})


@api_bp.route("/archive/<path:filename>", methods=["GET"])
@require_auth
def api_archive_detail(filename, user_id=None):
    """GET /api/archive/{filename} — 获取笔记详情"""
    _log(f"[WebAPI] /api/archive/{filename}: user={user_id}")
    ctx = _get_ctx(user_id)
    category = request.args.get("category", "")

    categories = {
        "work": ctx.work_notes_dir,
        "emotion": ctx.emotion_notes_dir,
        "fun": ctx.fun_notes_dir,
        "book": ctx.book_notes_dir,
        "media": ctx.media_notes_dir,
        "voice": ctx.voice_journal_dir,
    }

    # 安全检查
    filename = os.path.basename(filename)
    if not filename.endswith(".md"):
        filename += ".md"

    # 在指定或所有分类目录中查找
    search_dirs = [categories[category]] if category and category in categories else categories.values()

    for dir_path in search_dirs:
        filepath = os.path.join(dir_path, filename)
        content = _read_file_safe(filepath)
        if content:
            return jsonify({"content": content, "filename": filename})

    return jsonify({"error": "文件不存在"}), 404


@api_bp.route("/mood", methods=["GET"])
@require_auth
def api_mood(user_id=None):
    """GET /api/mood — 获取情绪数据"""
    ctx = _get_ctx(user_id)

    state = _read_state_safe(ctx)
    scores = state.get("mood_scores", [])

    # 情绪日记列表
    diaries = []
    emotion_files = _list_files_safe(ctx.emotion_notes_dir, "*.md")
    for f in sorted(emotion_files, reverse=True):
        diaries.append({
            "file": f,
            "date": f.replace(".md", "").replace("情绪日记-", ""),
            "title": f.replace(".md", ""),
        })

    return jsonify({"scores": scores, "diaries": diaries})


@api_bp.route("/memory", methods=["GET"])
@require_auth
def api_memory(user_id=None):
    """GET /api/memory — 获取长期记忆（结构化解析 memory.md）"""
    ctx = _get_ctx(user_id)

    content = _read_file_safe(ctx.memory_file)
    if not content:
        return jsonify({"sections": [], "total_items": 0, "last_updated": ""})

    # 按 ## 标题分段
    _SECTION_ICONS = {
        "用户画像": "👤", "重要的人": "👥", "偏好": "💡",
        "近期关注": "🔍", "重要事件": "📌", "工作": "💼",
        "习惯": "🔄", "健康": "🏥", "财务": "💰",
    }
    sections = []
    total_items = 0
    parts = re.split(r'\n(?=## )', content)
    for part in parts:
        part = part.strip()
        if not part.startswith("## "):
            continue
        lines = part.split("\n")
        title = lines[0].replace("## ", "").strip()
        items = [l.lstrip("- ").strip() for l in lines[1:] if l.strip().startswith("- ")]
        if not items:
            # 非列表段落也保留
            body = "\n".join(lines[1:]).strip()
            if body:
                items = [body]
        icon = _SECTION_ICONS.get(title, "📋")
        total_items += len(items)
        sections.append({"title": title, "icon": icon, "items": items})

    # 获取文件修改时间
    last_updated = ""
    try:
        if os.path.exists(ctx.memory_file):
            mtime = os.path.getmtime(ctx.memory_file)
            last_updated = datetime.fromtimestamp(mtime, _BEIJING_TZ).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass

    return jsonify({"sections": sections, "total_items": total_items, "last_updated": last_updated})


@api_bp.route("/books", methods=["GET"])
@require_auth
def api_books(user_id=None):
    """GET /api/books — 获取读书笔记"""
    ctx = _get_ctx(user_id)

    books = []
    files = _list_files_safe(ctx.book_notes_dir, "*.md")
    for f in sorted(files, reverse=True):
        books.append({
            "file": f,
            "title": f.replace(".md", ""),
        })

    return jsonify({"books": books})


@api_bp.route("/media", methods=["GET"])
@require_auth
def api_media(user_id=None):
    """GET /api/media — 获取影视笔记"""
    ctx = _get_ctx(user_id)

    items = []
    files = _list_files_safe(ctx.media_notes_dir, "*.md")
    for f in sorted(files, reverse=True):
        items.append({
            "file": f,
            "title": f.replace(".md", ""),
        })

    return jsonify({"items": items})


# ============================================================
# 管理员 API — /api/admin/*
# ============================================================

@api_bp.route("/admin/users", methods=["GET"])
@require_admin
def api_admin_users():
    """GET /api/admin/users — 用户列表"""
    _log(f"[WebAPI] /api/admin/users")
    users = get_all_users()
    return jsonify({"users": users})


@api_bp.route("/admin/usage", methods=["GET"])
@require_admin
def api_admin_usage():
    """GET /api/admin/usage — LLM 用量统计"""
    _log(f"[WebAPI] /api/admin/usage")

    # 读取 usage_log.jsonl
    entries = []
    try:
        if os.path.exists(USAGE_LOG_FILE):
            with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        _log(f"[WebAPI] 读取用量日志失败: {e}")

    # 按用户汇总
    user_stats = {}
    total_tokens = 0
    for entry in entries:
        uid = entry.get("user_id", "unknown")
        tokens = entry.get("total_tokens", 0)
        total_tokens += tokens

        if uid not in user_stats:
            user_stats[uid] = {"total_tokens": 0, "call_count": 0, "models": {}}
        user_stats[uid]["total_tokens"] += tokens
        user_stats[uid]["call_count"] += 1

        model = entry.get("model", "unknown")
        if model not in user_stats[uid]["models"]:
            user_stats[uid]["models"][model] = {"tokens": 0, "count": 0}
        user_stats[uid]["models"][model]["tokens"] += tokens
        user_stats[uid]["models"][model]["count"] += 1

    # 最近 7 天按日分组
    daily = {}
    for entry in entries:
        ts = entry.get("ts", "")[:10]  # YYYY-MM-DD
        if ts not in daily:
            daily[ts] = {"tokens": 0, "calls": 0}
        daily[ts]["tokens"] += entry.get("total_tokens", 0)
        daily[ts]["calls"] += 1

    return jsonify({
        "total_tokens": total_tokens,
        "total_calls": len(entries),
        "user_stats": user_stats,
        "daily": daily,
    })


@api_bp.route("/admin/users/<uid>/suspend", methods=["POST"])
@require_admin
def api_admin_suspend(uid):
    """POST /api/admin/users/{id}/suspend — 挂起用户"""
    _log(f"[WebAPI] /api/admin/suspend: {uid}")
    update_user_status(uid, "suspended")
    return jsonify({"ok": True, "user_id": uid, "status": "suspended"})


@api_bp.route("/admin/users/<uid>/activate", methods=["POST"])
@require_admin
def api_admin_activate(uid):
    """POST /api/admin/users/{id}/activate — 激活用户"""
    _log(f"[WebAPI] /api/admin/activate: {uid}")
    update_user_status(uid, "active")
    return jsonify({"ok": True, "user_id": uid, "status": "active"})


@api_bp.route("/admin/stats", methods=["GET"])
@require_admin
def api_admin_stats():
    """GET /api/admin/stats — 延迟 + Token + 技能统计"""
    import glob
    from collections import defaultdict

    days = int(request.args.get("days", "14"))
    now = datetime.now(_BEIJING_TZ)
    cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")

    # --- 1. 读取 usage_log.jsonl (Token 用量) ---
    usage_entries = []
    try:
        if os.path.exists(USAGE_LOG_FILE):
            with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                        if e.get("ts", "")[:10] >= cutoff:
                            usage_entries.append(e)
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass

    # Token 按日汇总
    token_daily = defaultdict(lambda: {"prompt": 0, "completion": 0, "total": 0, "calls": 0})
    token_by_model = defaultdict(lambda: {"prompt": 0, "completion": 0, "total": 0, "calls": 0})
    token_by_user = defaultdict(lambda: {"prompt": 0, "completion": 0, "total": 0, "calls": 0})
    today_str = now.strftime("%Y-%m-%d")

    for e in usage_entries:
        day = e.get("ts", "")[:10]
        pt = e.get("prompt_tokens", 0)
        ct = e.get("completion_tokens", 0)
        tt = e.get("total_tokens", 0)
        model = e.get("model", "unknown")
        uid = e.get("user_id", "unknown")

        token_daily[day]["prompt"] += pt
        token_daily[day]["completion"] += ct
        token_daily[day]["total"] += tt
        token_daily[day]["calls"] += 1

        token_by_model[model]["prompt"] += pt
        token_by_model[model]["completion"] += ct
        token_by_model[model]["total"] += tt
        token_by_model[model]["calls"] += 1

        token_by_user[uid]["prompt"] += pt
        token_by_user[uid]["completion"] += ct
        token_by_user[uid]["total"] += tt
        token_by_user[uid]["calls"] += 1

    # 今日汇总
    today_stats = token_daily.get(today_str, {"prompt": 0, "completion": 0, "total": 0, "calls": 0})

    # 成本估算 (DeepSeek: 输入¥2/M 输出¥8/M, Qwen Flash: 免费, Qwen VL: 输入¥3/M 输出¥9/M)
    total_cost = 0.0
    for model, stats in token_by_model.items():
        m = model.lower()
        if "deepseek" in m:
            total_cost += stats["prompt"] / 1e6 * 2 + stats["completion"] / 1e6 * 8
        elif "vl" in m or "vl-max" in m:
            total_cost += stats["prompt"] / 1e6 * 3 + stats["completion"] / 1e6 * 9
        # qwen-flash 免费

    today_cost = 0.0
    for e in usage_entries:
        if e.get("ts", "")[:10] == today_str:
            m = e.get("model", "").lower()
            pt = e.get("prompt_tokens", 0)
            ct = e.get("completion_tokens", 0)
            if "deepseek" in m:
                today_cost += pt / 1e6 * 2 + ct / 1e6 * 8
            elif "vl" in m:
                today_cost += pt / 1e6 * 3 + ct / 1e6 * 9

    # --- 2. 读取各用户 decisions.jsonl (延迟 + 技能) ---
    decisions = []
    users_dir = os.path.join(DATA_DIR, "users")
    try:
        decision_files = glob.glob(os.path.join(users_dir, "*", "_Karvis", "logs", "decisions.jsonl"))
        for df in decision_files:
            uid = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(df))))
            with open(df, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                        if e.get("ts", "")[:10] >= cutoff:
                            e["user_id"] = uid
                            decisions.append(e)
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass

    # 按时间倒排，取最近 100 条用于延迟瀑布图
    decisions.sort(key=lambda x: x.get("ts", ""), reverse=True)
    recent_decisions = decisions[:100]

    # 延迟分布统计
    latencies = [d.get("elapsed_s", 0) for d in decisions if d.get("elapsed_s")]
    latency_stats = {}
    if latencies:
        latencies_sorted = sorted(latencies)
        latency_stats = {
            "avg": round(sum(latencies) / len(latencies), 1),
            "p50": round(latencies_sorted[len(latencies_sorted) // 2], 1),
            "p90": round(latencies_sorted[int(len(latencies_sorted) * 0.9)], 1),
            "p99": round(latencies_sorted[int(len(latencies_sorted) * 0.99)], 1),
            "max": round(max(latencies), 1),
            "count": len(latencies),
            "slow_15s": len([l for l in latencies if l > 15]),
            "slow_8s": len([l for l in latencies if l > 8]),
        }

    # 技能频次统计
    skill_counts = defaultdict(int)
    skill_by_user = defaultdict(lambda: defaultdict(int))
    for d in decisions:
        sk = d.get("skill", "unknown")
        uid = d.get("user_id", "unknown")
        skill_counts[sk] += 1
        skill_by_user[uid][sk] += 1

    skill_top = sorted(skill_counts.items(), key=lambda x: -x[1])[:15]

    return jsonify({
        "token": {
            "daily": dict(token_daily),
            "by_model": dict(token_by_model),
            "by_user": dict(token_by_user),
            "today": today_stats,
            "total_cost": round(total_cost, 2),
            "today_cost": round(today_cost, 4),
        },
        "latency": {
            "recent": [{
                "ts": d.get("ts", ""),
                "user_id": d.get("user_id", ""),
                "skill": d.get("skill", ""),
                "elapsed_s": d.get("elapsed_s", 0),
                "input": d.get("input", "")[:40],
            } for d in recent_decisions],
            "stats": latency_stats,
        },
        "skills": {
            "top": skill_top,
            "by_user": {uid: dict(sk) for uid, sk in skill_by_user.items()},
        },
        "period_days": days,
    })


@api_bp.route("/admin/logs", methods=["GET"])
@require_admin
def api_admin_logs():
    """GET /api/admin/logs — 查看服务日志"""
    import subprocess
    from collections import deque

    project = request.args.get("project", "karvisforall")
    lines = min(int(request.args.get("lines", "200")), 2000)
    keyword = request.args.get("keyword", "").strip()
    level = request.args.get("level", "").upper()

    log_lines = []

    if project == "karvis":
        # Karvis 个人版: 通过 docker compose logs 获取
        try:
            result = subprocess.run(
                ["docker", "compose", "-f",
                 os.path.join(LOG_KARVIS_COMPOSE_DIR, "docker-compose.yml"),
                 "logs", "--tail", str(lines), "--no-color"],
                capture_output=True, text=True, timeout=10,
            )
            raw = result.stdout or result.stderr or ""
            for line in raw.splitlines():
                # 去掉 Docker 容器名前缀 (e.g. "karvis-personal-1  | ")
                idx = line.find("| ")
                clean = line[idx + 2:] if idx != -1 else line
                log_lines.append(clean)
        except Exception as e:
            log_lines = [f"[ERROR] 读取 Karvis 日志失败: {e}"]
    else:
        # KarvisForAll: 直接读取文件尾部
        try:
            if os.path.exists(LOG_FILE_KARVISFORALL):
                with open(LOG_FILE_KARVISFORALL, "r", encoding="utf-8", errors="replace") as f:
                    log_lines = list(deque(f, maxlen=lines))
                log_lines = [l.rstrip("\n") for l in log_lines]
            else:
                log_lines = [f"[ERROR] 日志文件不存在: {LOG_FILE_KARVISFORALL}"]
        except Exception as e:
            log_lines = [f"[ERROR] 读取日志失败: {e}"]

    # 关键词过滤
    if keyword:
        kw_lower = keyword.lower()
        log_lines = [l for l in log_lines if kw_lower in l.lower()]

    # 级别过滤
    if level and level != "ALL":
        log_lines = [l for l in log_lines if level in l.upper()]

    return jsonify({"lines": log_lines, "total": len(log_lines), "project": project})


# ============================================================
# Web 页面路由 — /web/*（提供静态 HTML）
# ============================================================

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "web_static")


@web_bp.route("/")
def web_index():
    """Web 首页 → 重定向到登录页"""
    return redirect(url_for("web.web_login"))


@web_bp.route("/login")
def web_login():
    return _serve_page("login.html")


@web_bp.route("/dashboard")
def web_dashboard():
    return _serve_page("dashboard.html")


@web_bp.route("/notes")
def web_notes():
    return _serve_page("notes.html")


@web_bp.route("/todos")
def web_todos():
    return _serve_page("todos.html")


@web_bp.route("/daily")
def web_daily():
    return _serve_page("daily.html")


@web_bp.route("/archive")
def web_archive():
    return _serve_page("archive.html")


@web_bp.route("/mood")
def web_mood():
    return _serve_page("mood.html")


@web_bp.route("/memory")
def web_memory():
    return _serve_page("memory.html")


@web_bp.route("/admin")
def web_admin():
    return _serve_page("admin.html")


@web_bp.route("/logs")
def web_logs():
    return _serve_page("logs.html")


def _serve_page(filename):
    """提供静态 HTML 页面"""
    if not os.path.exists(os.path.join(_STATIC_DIR, filename)):
        return f"页面 {filename} 不存在", 404
    return send_from_directory(_STATIC_DIR, filename)


# ============================================================
# 工具函数
# ============================================================

def _read_file_safe(filepath):
    """安全读取文件，失败返回空字符串"""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        _log(f"[WebAPI] 读取文件失败 {filepath}: {e}")
    return ""


def _read_state_safe(ctx):
    """安全读取用户 state"""
    try:
        content = _read_file_safe(ctx.state_file)
        if content:
            return json.loads(content)
    except Exception as e:
        _log(f"[WebAPI] 读取 state 失败: {e}")
    return {}


def _list_files_safe(dir_path, pattern="*"):
    """安全列出目录下的文件"""
    try:
        if os.path.exists(dir_path):
            import glob
            files = glob.glob(os.path.join(dir_path, pattern))
            return [os.path.basename(f) for f in files if os.path.isfile(f)]
    except Exception as e:
        _log(f"[WebAPI] 列出文件失败 {dir_path}: {e}")
    return []


def _read_first_line(filepath):
    """读取文件第一行（去除 # 标记），用于获取标题"""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                line = f.readline().strip()
                if line.startswith("#"):
                    line = line.lstrip("#").strip()
                return line
    except Exception:
        pass
    return ""


def _extract_date_from_filename(filename):
    """从文件名中提取日期"""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    return match.group(1) if match else ""
