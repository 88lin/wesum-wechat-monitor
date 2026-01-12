# WeSum - 微信公众号小时级摘要推送助手

> 自动监控微信公众号更新，生成 AI 摘要并推送到你的微信

---

## 📖 项目简介

WeSum 是一个轻量级的公众号文章聚合工具，可以：

- ✅ 自动监控多个公众号更新（支持 Wechat2RSS）
- ✅ AI 生成文章摘要（通义千问）
- ✅ 智能分类干扰文章（招聘、带货、广告等）
- ✅ 推送到企业微信（GitHub Gist 存储完整摘要）
- ✅ 避免重复推送（智能去重）
- ✅ 支持无新文章通知
- ✅ 单体架构，易于部署
- ✅ 支持 GitHub Actions 自动运行

**适用场景**：关注了大量公众号，无法及时查看，需要定时汇总。

---

## 🚀 快速开始

### 前置要求

- Windows 10/11 或 Linux
- Python 3.9+
- RSS 数据源（Wechat2RSS）

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

编辑 `.env` 文件：

```bash
DASHSCOPE_API_KEY=your_api_key_here
WEBHOOK_URL=your_webhook_url_here
GITHUB_TOKEN=your_github_token_here  # 可选
WECHAT2RSS_DOMAIN=your_wechat2rss_domain_here
RSS_TOKEN=your_rss_token_here
```

#### 3. 配置公众号订阅（推荐方式）

**方式 1：使用 config.json（推荐）**

复制 `config.json.example` 为 `config.json`：

```bash
cp config.json.example config.json
```

编辑 `config.json`，修改公众号配置：

```json
{
  "rss_subscriptions": [
    {
      "name": "新智元",
      "url": "${WECHAT2RSS_DOMAIN}/feed/1f977d0059386d49693f1be76b2773f6d3380e1e.xml?token=${RSS_TOKEN}",
      "enabled": true
    },
    {
      "name": "量子位",
      "url": "${WECHAT2RSS_DOMAIN}/feed/43df61dc721c56c8bf0ad68e808bc986c57a9000.xml?token=${RSS_TOKEN}",
      "enabled": true
    }
    // ... 添加更多公众号
  ],
  "filters": {
    "max_hours": 24,
    "max_articles_per_run": null
  }
}
```

**注意**：`config.json` 使用环境变量占位符（`${WECHAT2RSS_DOMAIN}` 和 `${RSS_TOKEN}`），实际值从 `.env` 文件读取。

**方式 2：使用环境变量（备用）**

在 `.env` 文件中添加：

```bash
# 公众号 1
RSS_1_NAME=新智元
RSS_1_URL=https://${WECHAT2RSS_DOMAIN}/feed/xxxxx.xml?token=${RSS_TOKEN}
RSS_1_ENABLED=true

# 公众号 2
RSS_2_NAME=量子位
RSS_2_URL=https://${WECHAT2RSS_DOMAIN}/feed/yyyyy.xml?token=${RSS_TOKEN}
RSS_2_ENABLED=true
```

**配置加载优先级**：`config.json` > 环境变量 > 默认配置

#### 4. 运行测试

```bash
python main.py
```

---

## ⚙️ 配置说明

### 环境变量（.env 文件）

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `DASHSCOPE_API_KEY` | 通义千问 API Key | ✅ |
| `WEBHOOK_URL` | 企业微信 Webhook URL | ✅ |
| `GITHUB_TOKEN` | GitHub Token（用于 Gist） | ❌ |
| `WECHAT2RSS_DOMAIN` | Wechat2RSS 域名 | ✅ |
| `RSS_TOKEN` | Wechat2RSS 访问令牌 | ✅ |

### 公众号订阅配置（config.json）

**推荐使用 `config.json` 配置公众号**，支持：

- ✅ JSON 格式，结构清晰
- ✅ 支持添加/删除/禁用公众号
- ✅ 无需修改 main.py
- ✅ 便于备份和迁移

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

**备用方案**：使用环境变量配置公众号（见"快速开始"部分）

---

## 🆕 新功能（v2.0）

### GitHub Gist 集成
- 完整摘要存储到 GitHub Gist（Markdown 格式）
- 企业微信推送 Gist 链接（避免消息长度限制）
- 永久存储，可回看历史

### 多公众号订阅
- 支持同时监控多个公众号
- 每个公众号独立启用/禁用
- 自动合并所有文章到一个推送

### 无新文章通知
- 即使没有新文章也会发送运行确认
- 方便监控定时任务是否正常运行

### 时区修复
- 正确处理 RSS 时区（+0800）
- 避免时间比较错误

---

## 📁 项目结构

```
WeSum/
├── main.py                 # 主程序（单体架构，957行）
├── .env.example            # 环境变量模板
├── .gitignore              # Git 忽略规则
├── requirements.txt        # Python 依赖
├── README.md               # 项目文档
├── LICENSE                 # MIT 许可证
├── config.json.example     # 配置模板
├── data/                   # 数据目录
│   └── seen_articles.json  # 已读文章记录
└── logs/                   # 日志目录
```

---

## 🤖 账号申请

### 通义千问 API Key
1. 访问 https://dashscope.aliyun.com/
2. 注册/登录账号
3. 创建 API Key
4. 免费额度：100 万 tokens / 月

### 企业微信 Webhook（推荐）
1. 登录企业微信管理后台
2. 创建机器人，获取 Webhook URL
3. 免费且无限制

### Wechat2RSS（推荐）
1. 访问 https://wechat2rss.xlab.app
2. 浏览免费公众号列表（300+）
3. 或付费私有部署（15元/月，不限数量）

---

## 📅 定时任务（GitHub Actions）

### 自动运行配置

项目支持 GitHub Actions 自动运行，无需本地服务器：

1. **Fork 本项目到你的 GitHub 账号**

2. **配置 Secrets**：
   - 进入仓库 Settings → Secrets and variables → Actions
   - 添加以下 Secrets：
     - `QWEN_API_KEY`: 通义千问 API Key
     - `WEBHOOK_URL`: 企业微信 Webhook URL
     - `WECHAT2RSS_DOMAIN`: Wechat2RSS 域名
     - `RSS_TOKEN`: Wechat2RSS Token
     - `PERSONAL_GITHUB_TOKEN`: GitHub Token（可选，用于 Gist）

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

### 本地运行
- 通义千问：约 ¥0.72 / 月（5 个公众号）
- Wechat2RSS：免费
- 企业微信：免费
- **合计**：¥0.72 / 月

### GitHub Actions 运行
- 通义千问：约 ¥0.72 / 月（5 个公众号）
- GitHub Actions：免费（2000 分钟/月）
- 企业微信：免费
- Wechat2RSS：免费
- **合计**：¥0.72 / 月

**推荐**：使用 GitHub Actions 运行，无需本地服务器。

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
**A**: 可以在 `main.py` 中自定义提示词，或调整 `max_tokens` 参数。

### Q5: GitHub Actions 记忆文件丢失
**A**: 首次运行需要手动触发一次，之后会自动管理记忆文件。

---

## 📝 License

MIT

---

## 🙏 致谢

- [Wechat2RSS](https://github.com/ttttmr/Wechat2RSS) - 微信公众号 RSS 生成
- [通义千问](https://dashscope.aliyun.com/) - 阿里云 AI 服务
- [企业微信](https://work.weixin.qq.com/) - 腾讯企业通讯工具

---

**开发者**：Jason + Claude Code
**最后更新**：2026-01-13
**版本**：v2.0
