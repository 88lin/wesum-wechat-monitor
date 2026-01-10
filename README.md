# WeSum - 微信公众号小时级摘要推送助手

> 自动监控微信公众号更新，生成 AI 摘要并推送到你的微信

---

## 📖 项目简介

WeSum 是一个轻量级的公众号文章聚合工具，可以：

- ✅ 自动监控公众号更新（基于 Wewe-RSS）
- ✅ AI 生成文章摘要（通义千问）
- ✅ 推送到个人微信（Server酱）
- ✅ 避免重复推送（智能去重）
- ✅ 无封号风险（基于微信读书 API）

**适用场景**：关注了大量公众号，无法及时查看，需要定时汇总。

---

## 🚀 快速开始

### 前置要求

- Windows 10/11
- Python 3.9+
- Docker Desktop（用于 Wewe-RSS）

### 安装步骤

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置 Wewe-RSS

```bash
# 启动 Wewe-RSS
docker compose up -d

# 访问 http://localhost:4000
# 使用微信读书账号登录
# 添加需要监控的公众号
# 复制 RSS 地址
```

#### 3. 配置 WeSum

复制 `config.example.json` 为 `config.json`，填入你的 API Key：

```json
{
  "ai": {
    "api_key": "你的通义千问API Key"
  },
  "push": {
    "sendkey": "你的Server酱SendKey"
  }
}
```

#### 4. 运行测试

```bash
python main.py
```

---

## 📁 项目结构

```
WeSum/
├── main.py                  # 主程序
├── config.json              # 配置文件（包含敏感信息）
├── config.example.json      # 配置模板
├── requirements.txt         # Python 依赖
├── docker-compose.yml       # Wewe-RSS 配置
├── src/                     # 核心模块
│   ├── rss_parser.py        # RSS 解析
│   ├── ai_summarizer.py     # AI 摘要
│   └── push_notifier.py     # 微信推送
├── data/                    # 数据存储
│   └── seen_articles.json   # 已抓取文章记录
├── logs/                    # 日志文件
└── wewe-rss-data/           # Wewe-RSS 数据
```

---

## ⚙️ 配置说明

### config.json 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `rss.url` | RSS 地址 | http://localhost:4000/feeds/all.atom |
| `rss.update_interval` | 更新间隔（秒） | 3600 |
| `ai.api_key` | 通义千问 API Key | - |
| `ai.model` | AI 模型 | qwen-turbo |
| `push.sendkey` | Server酱 SendKey | - |
| `filters.max_articles_per_run` | 单次最大文章数 | 20 |

---

## 🤖 账号申请

### 通义千问 API Key
1. 访问 https://dashscope.aliyun.com/
2. 注册/登录账号
3. 创建 API Key
4. 免费额度：100 万 tokens / 月

### Server酱 SendKey
1. 访问 https://sct.ftqq.com/
2. 微信登录
3. 获取 SendKey
4. 免配额：5 条/天

---

## 📅 定时任务（Windows）

### 方法 1：任务计划程序（推荐）

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每小时
4. 操作：启动程序
   - 程序：`python.exe`
   - 参数：`main.py`
   - 起始于：项目目录路径

### 方法 2：批处理脚本

创建 `run.bat`：

```batch
@echo off
cd /d "你的项目路径"
python main.py
```

然后在任务计划程序中定时运行此脚本。

---

## 💰 成本估算

### MVP（5 个公众号）
- 通义千问：约 ¥0.72 / 月
- Server酱：免费
- **合计**：¥0.72 / 月

### 扩展（1000 个公众号）
- 通义千问：约 ¥144 / 月
- Server酱：¥4 / 月（付费版）
- **合计**：¥148 / 月

---

## 🛠️ 开发日志

### Phase 0: 假设验证 ✅
- [x] 验证 Wewe-RSS 可行性
- [x] 验证 RSS 解析可行性
- [x] 验证 AI 摘要质量
- [x] 验证微信推送功能

### Phase 1: 核心开发 ✅
- [x] 创建项目结构
- [x] 编写 RSS 解析模块
- [x] 编写 AI 摘要模块
- [x] 编写微信推送模块
- [x] 整合主程序
- [x] 测试完整流程

---

## 🐛 常见问题

### Q1: 提示 "No new articles found"
**A**: 第一次运行会抓取所有文章，后续只推送新文章。

### Q2: 微信收不到推送
**A**: 检查 Server酱 SendKey 是否正确，确认已关注"Server酱"公众号。

### Q3: Wewe-RSS 无法访问
**A**: 确认 Docker Desktop 已启动，运行 `docker compose up -d`。

### Q4: AI 摘要质量不好
**A**: 可以在 `config.json` 中自定义 `summary_prompt` 优化提示词。

---

## 📝 License

MIT

---

## 🙏 致谢

- [Wewe-RSS](https://github.com/cooderl/wewe-rss) - 微信公众号 RSS 生成
- [通义千问](https://dashscope.aliyun.com/) - 阿里云 AI 服务
- [Server酱](https://sct.ftqq.com/) - 微信推送服务

---

**开发者**：Jason + Claude Code
**最后更新**：2026-01-11
