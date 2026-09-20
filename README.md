# WeSum - 微信公众号小时级摘要推送助手

> 自动监控微信公众号更新，多模型生成 AI 摘要并推送到你的微信

---

## 📖 项目简介

WeSum 是一个轻量级的公众号文章聚合工具，可以：

- ✅ 自动监控多个公众号更新（支持 Wechat2RSS）
- ✅ 多模型生成文章摘要：智谱 GLM、通义千问 Qwen、OpenAI GPT、DeepSeek、Kimi 等（OpenAI 兼容接口，任意服务商通用）
- ✅ 智能分类干扰文章（招聘、带货、广告等）
- ✅ 推送到企业微信（GitHub Gist 存储完整摘要）
- ✅ 避免重复推送（智能去重）
- ✅ RSS 源失效自动告警，不再静默失效
- ✅ AI 调用自动重试、消息长度自动裁剪等容错机制
- ✅ 单体架构，易于部署，支持 GitHub Actions 自动运行

**适用场景**：关注了大量公众号，无法及时查看，需要定时汇总。

---

## 🚀 快速开始

### 前置要求

- Python 3.10+（GitHub Actions 上使用 3.12）
- RSS 数据源（Wechat2RSS）
- 任一 OpenAI 兼容的大模型服务 API Key

### 安装步骤

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的配置：

```bash
cp .env.example .env
```

编辑 `.env`，选择你使用的大模型服务（三选一即可）：

```bash
# 方式一：智谱 GLM（推荐，glm-5.3-flash 速度快、价格低）
LLM_PROVIDER=zhipu
LLM_API_KEY=your_zhipu_api_key
WECHAT_MODEL=glm-5.3-flash

# 方式二：阿里云百炼（通义千问）
LLM_PROVIDER=dashscope
LLM_API_KEY=your_dashscope_api_key
WECHAT_MODEL=qwen3.8-flash

# 方式三：OpenAI
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_api_key
WECHAT_MODEL=gpt-5.6

# 企业微信 Webhook（必需）
WEBHOOK_URL=your_webhook_url_here
```

#### 3. 配置公众号订阅

编辑 `config.json`，修改公众号列表：

```json
{
  "rss_subscriptions": [
    {
      "name": "新智元",
      "url": "https://${WECHAT2RSS_DOMAIN}/feed/1f977d0059386d49693f1be76b2773f6d3380e1e.xml?token=${RSS_TOKEN}",
      "enabled": true
    }
  ],
  "filters": {
    "max_hours": 24,
    "max_articles_per_run": null
  }
}
```

**注意**：`config.json` 中的 `${WECHAT2RSS_DOMAIN}` 和 `${RSS_TOKEN}` 占位符会从 `.env` 读取替换，更换 RSS 实例只需改一个环境变量。

#### 4. 运行测试

```bash
python main.py
```

---

## 🤖 模型配置

所有模型调用统一走 **OpenAI 兼容接口**，只需三个变量即可切换服务商。

### 服务商预设

| `LLM_PROVIDER` | 服务商 | 端点 | 常用模型 |
|----------------|--------|------|----------|
| `zhipu` / `glm` | 智谱 AI | `open.bigmodel.cn/api/paas/v4` | `glm-5.3-flash`（高速）、`glm-5.2`（更强） |
| `dashscope` / `qwen` | 阿里云百炼 | `dashscope.aliyuncs.com/compatible-mode/v1` | `qwen3.8-flash`、`qwen-plus` |
| `openai` | OpenAI | `api.openai.com/v1` | `gpt-5.6` |
| `deepseek` | DeepSeek | `api.deepseek.com/v1` | `deepseek-chat` |
| `moonshot` | Moonshot（Kimi） | `api.moonshot.cn/v1` | Kimi 系列 |

> 模型名以各服务商文档中的模型 ID 为准；`glm-5.3-flash` 这类 Flash 版本速度快、成本低，适合摘要类任务。

### 自定义端点

使用其他 OpenAI 兼容服务（SiliconFlow、OpenRouter、本地 vLLM / Ollama 等）时，直接指定完整端点：

```bash
LLM_BASE_URL=http://localhost:11434/v1   # 例如本地 Ollama
LLM_API_KEY=ollama
WECHAT_MODEL=你的模型名
```

`LLM_BASE_URL` 优先级高于 `LLM_PROVIDER`。

### 旧配置兼容

此前版本使用的 `DASHSCOPE_API_KEY` 变量仍然有效（等价于 `LLM_API_KEY` + dashscope 预设），旧 `.env` 无需修改即可继续使用。

---

## ⚙️ 配置说明

### 环境变量（.env 文件）

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `LLM_API_KEY` | 大模型服务 API Key（兼容旧变量 `DASHSCOPE_API_KEY`） | ✅ |
| `WEBHOOK_URL` | 企业微信 Webhook URL | ✅ |
| `WECHAT2RSS_DOMAIN` | Wechat2RSS 实例域名 | ✅ |
| `LLM_PROVIDER` | 服务商预设（不填默认 dashscope） | ❌ |
| `LLM_BASE_URL` | 自定义 OpenAI 兼容端点（优先级高于 `LLM_PROVIDER`） | ❌ |
| `WECHAT_MODEL` | 模型名称（默认 `qwen-plus`） | ❌ |
| `GITHUB_TOKEN` | GitHub Token（用于 Gist；未配置时降级为仅标题列表推送） | ❌ |
| `RSS_TOKEN` | RSS 访问 Token（私有部署需要时） | ❌ |

### 公众号订阅配置（config.json）

配置格式：

```json
{
  "rss_subscriptions": [
    {
      "name": "公众号名称",
      "url": "完整的RSS URL",
      "enabled": true
    }
  ],
  "filters": {
    "max_hours": 24,
    "max_articles_per_run": null
  }
}
```

`filters` 字段说明：

- `max_hours`：只处理最近 N 小时内发布的文章（默认 24）
- `max_articles_per_run`：每轮最多处理的文章数，超出的按发布时间取最新的一批，其余留待下次运行（`null` 表示不限制）

**备用方案**：使用环境变量配置公众号（`RSS_1_NAME` / `RSS_1_URL` / `RSS_1_ENABLED`，见 `.env.example` 注释）。

---

## 📁 项目结构

```
WeSum/
├── main.py                 # 主程序（单体架构）
├── .env.example            # 环境变量模板
├── .gitignore              # Git 忽略规则
├── requirements.txt        # Python 依赖
├── README.md               # 项目文档
├── LICENSE                 # MIT 许可证
├── config.json             # 订阅配置（提交到仓库供 Actions 使用）
├── data/                   # 数据目录
│   └── seen_articles.json  # 已读文章记录
└── .github/workflows/      # GitHub Actions 定时任务
```

---

## 🤖 API Key 申请

| 服务商 | 申请地址 | 备注 |
|--------|----------|------|
| 智谱 AI | https://open.bigmodel.cn/ | 有免费模型额度 |
| 阿里云百炼 | https://dashscope.aliyun.com/ | 新用户有免费 token 额度 |
| OpenAI | https://platform.openai.com/ | 需海外支付方式 |
| DeepSeek | https://platform.deepseek.com/ | 价格低 |

### 企业微信 Webhook

1. 登录企业微信管理后台
2. 创建机器人，获取 Webhook URL
3. 免费且无限制

### Wechat2RSS

1. 访问 https://wechat2rss.xlab.app
2. 浏览免费公众号列表（300+）
3. 或付费私有部署（15元/月，不限数量）

---

## 📅 定时任务（GitHub Actions）

### 自动运行配置

项目支持 GitHub Actions 自动运行，无需本地服务器：

1. **Fork 本项目到你的 GitHub 账号**

2. **配置 Secrets**（Settings → Secrets and variables → Actions）：

   | 类型 | 名称 | 说明 |
   |------|------|------|
   | Secret | `LLM_API_KEY` | 大模型 API Key（兼容旧名 `QWEN_API_KEY`） |
   | Secret | `WEBHOOK_URL` | 企业微信 Webhook URL |
   | Secret | `PERSONAL_GITHUB_TOKEN` | GitHub Token（可选，用于 Gist） |
   | Secret | `RSS_TOKEN` | RSS 访问 Token（可选） |
   | Variable | `LLM_PROVIDER` | 服务商预设（可选，默认 dashscope） |
   | Variable | `LLM_BASE_URL` | 自定义端点（可选） |
   | Variable | `WECHAT_MODEL` | 模型名称（可选，默认 qwen-plus） |
   | Variable | `WECHAT2RSS_DOMAIN` | Wechat2RSS 实例域名 |

3. **启用 GitHub Actions**：
   - 进入 Actions 页面
   - 点击 "I understand my workflows, go ahead and enable them"
   - 手动运行一次测试（Run workflow → Run workflow）

4. **定时任务**：
   - 默认：每小时运行一次（UTC 时间）
   - 可在 `.github/workflows/wesum.yml` 中修改 cron 表达式

### 工作原理

- GitHub Actions 每次运行都会：
  1. 拉取最新代码（包含上次的 `seen_articles.json`）
  2. 运行 `main.py` 处理新文章
  3. 自动提交更新后的 `seen_articles.json` 到仓库
  4. 实现"记忆"持久化

---

## 💰 成本估算

以摘要类任务、每天几十篇文章的用量计，各家 Flash/轻量模型均在每月几元以内；智谱 GLM 与部分厂商提供免费额度，可以做到零成本。Gist、企业微信、GitHub Actions（公开仓库）均免费。

---

## 🐛 常见问题

### Q1: 提示 "No new articles found"
**A**: 第一次运行会抓取所有文章，后续只推送新文章。

### Q2: 微信收不到推送
**A**:
- 企业微信：检查 Webhook URL 是否正确
- 检查公众号是否启用（`enabled: True`）

### Q3: Wechat2RSS 找不到想要的公众号
**A**: 可以考虑付费私有部署（15元/月），订阅任意公众号。

### Q4: AI 摘要质量不好
**A**: 换更强的模型（如 `glm-5.2`、`gpt-5.6`，改 `WECHAT_MODEL` 即可），或在 `main.py` 中自定义提示词。

### Q5: 模型调用报错 404 / model not found
**A**: 检查 `WECHAT_MODEL` 是否为服务商文档中的准确模型 ID，以及 `LLM_PROVIDER`（或 `LLM_BASE_URL`）是否指向对应服务商。

### Q6: GitHub Actions 记忆文件丢失
**A**: 首次运行需要手动触发一次，之后会自动管理记忆文件。

### Q7: 为什么凌晨没有收到空消息通知？
**A**: 系统设置了静默时段（0:00-9:00），这个时段内即使没有新文章也不会发送空消息，避免打扰休息。9:00 后会恢复正常推送。

### Q8: RSS 拉取一直失败怎么办？
**A**: 检查 `WECHAT2RSS_DOMAIN` 指向的 Wechat2RSS 实例是否可用（浏览器直接打开 `https://<域名>/feed/xxx.xml` 看是否返回内容）。所有源都拉不到内容时，系统会发送"源疑似失效"告警。自建实例下线后，换一个新实例只需更新 `WECHAT2RSS_DOMAIN`。

---

## 📝 License

MIT

---

## 🙏 致谢

- [Wechat2RSS](https://github.com/ttttmr/Wechat2RSS) - 微信公众号 RSS 生成
- [智谱 AI](https://open.bigmodel.cn/) / [通义千问](https://dashscope.aliyun.com/) / [OpenAI](https://platform.openai.com/) - 大模型服务
- [企业微信](https://work.weixin.qq.com/) - 腾讯企业通讯工具

---

**开发者**：Jason + Claude Code
**最后更新**：2026-09-20
**版本**：v3.0
