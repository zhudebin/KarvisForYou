# 企业微信应用配置指南

> 这是 Karvis 连接企业微信的详细步骤。大约需要 10 分钟。

---

## 1. 注册企业微信

1. 打开 [work.weixin.qq.com](https://work.weixin.qq.com/)
2. 点击「立即注册」
3. 用你的微信扫码，选择「企业/组织」类型
4. 填写企业名称（随便写，比如「我的工作室」）

> 不需要真的是公司，个人就能注册。

---

## 2. 创建自建应用

1. 登录 [企微管理后台](https://work.weixin.qq.com/wework_admin/frame)
2. 左侧菜单 → **应用管理** → 自建 → **创建应用**
3. 填写：
   - 应用名称：`Karvis`（或你喜欢的名字）
   - 应用 logo：随便传一个
   - 可见范围：选「全公司」

---

## 3. 记下必要信息

创建好后，你需要记下 **5 样东西**，分三个地方找：

### 3.1 企业 ID（Corp ID）

- 企微管理后台 → 左下角 **我的企业** → 企业信息页
- 最下方「企业 ID」，格式类似 `ww1234567890abcdef`

### 3.2 AgentId + Secret

- 企微管理后台 → **应用管理** → 点击你创建的应用
- 页面上直接能看到 **AgentId**（一个数字，如 `1000003`）
- **Secret**：点「查看」，微信扫码后复制

### 3.3 Token + EncodingAESKey

- 应用详情页 → 往下翻到 **接收消息** → 点「设置 API 接收」
- **Token**：点「随机获取」→ 复制
- **EncodingAESKey**：点「随机获取」→ 复制
- **URL 先不填！** 等 Karvis 启动后再填

---

## 4. 配置回调 URL

Karvis 启动后，回到刚才的「设置 API 接收」页面，填写 URL：

### 场景 A：服务器有公网 IP

```
http://你的服务器IP:9000/wework
```

例如：`http://119.29.237.199:9000/wework`

### 场景 B：本地电脑（用 Cloudflare Tunnel）

运行 `setup.sh` 或手动启动隧道后，会得到一个地址：

```
https://abc-def-ghi.trycloudflare.com/wework
```

### 场景 C：想要固定域名（Cloudflare 命名隧道，免费）

如果你不想每次重启都换 URL：

```bash
# 1. 登录 Cloudflare（一次性）
cloudflared tunnel login

# 2. 创建隧道（一次性）
cloudflared tunnel create karvis

# 3. 配置路由（一次性）
# 在 Cloudflare Dashboard 添加 DNS 记录：
#   karvis.你的域名.com → CNAME → <隧道ID>.cfargotunnel.com

# 4. 启动（每次）
cloudflared tunnel --hostname karvis.你的域名.com --url http://localhost:9000
```

> 需要一个在 Cloudflare 托管的域名。没有域名的话用场景 A 或 B 就好。

填好 URL、Token、EncodingAESKey 后，点 **保存**。

如果提示「验证成功」就对了 ✅。如果提示「回调验证失败」：
- 确认 Karvis 正在运行
- 确认 Token 和 EncodingAESKey 与 `.env` 完全一致（不要多空格）
- 确认 URL 可以从公网访问

---

## 5. 配置企业可信 IP

这一步**很重要**，不配的话 Karvis 能收消息但**发不出去**。

1. 应用详情页 → 往下翻到 **企业可信 IP**
2. 点击「配置」
3. 填入你的服务器公网 IP（如 `119.29.237.199`）

> 不知道公网 IP？在服务器上运行 `curl ifconfig.me`。
>
> 用 Cloudflare Tunnel 的话，这里需要填 Cloudflare 的出口 IP。可以先试试不填，如果发不出消息再排查。

---

## 6. 验证

1. 打开手机上的企业微信 app
2. 找到你创建的 Karvis 应用（在「工作台」或聊天列表里搜索）
3. 发一条「你好」
4. 如果 Karvis 回复了欢迎消息 → 配置成功 🎉

### 小技巧：置顶应用

在企微 app 里，长按 Karvis 的聊天 → 置顶。这样它就像一个普通联系人，随时能找到。

---

## 常见配置问题

| 问题 | 原因 | 解决 |
|---|---|---|
| 回调验证失败 | Karvis 没启动 / URL 不对 | 确认服务在跑，确认 URL 能从外部访问 |
| 发消息没回复 | 企业可信 IP 没配 | 应用详情 → 企业可信 IP → 填服务器 IP |
| Token 不匹配 | `.env` 和企微后台填的不一样 | 对照检查，注意不要有多余空格 |
| cloudflared 地址变了 | 免费隧道每次重启会变 | 用命名隧道（免费）或直接用服务器公网 IP |
