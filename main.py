# -*- coding: utf-8 -*-
"""
WeSum - 微信公众号摘要推送助手
主程序：多公众号订阅、AI摘要、智能推送
"""

import sys
import io
import json
import os
import re
import time
import html
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

# 设置 stdout 编码为 UTF-8
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# 通义千问 API
import dashscope
from dashscope import Generation

# ==================== 配置加载 ====================

# 从环境变量加载配置
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 未安装，跳过

# 通义千问 API Key（必需）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请设置环境变量 DASHSCOPE_API_KEY（在 .env 文件中）")

# 企业微信 Webhook URL（必需）
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise ValueError("请设置环境变量 WEBHOOK_URL（在 .env 文件中）")

# GitHub Token（可选，用于创建 Gist）
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# RSS Token（可选）
RSS_TOKEN = os.getenv("RSS_TOKEN", "")

# 已推送文章记录文件
SEEN_ARTICLES_FILE = "data/seen_articles.json"

# 记忆库上限（防止无限增长；远大于 max_hours 时间窗口，不会导致重复推送）
MAX_SEEN_LINKS = 2000

# 北京时间（UTC+8）
CST = timezone(timedelta(hours=8))


def substitute_env_vars(value: str) -> str:
    """
    替换字符串中的 ${VAR} 环境变量占位符

    未定义（或为空）的占位符保持原样，便于上层检测并给出明确提示。
    """
    def _replace(match):
        return os.getenv(match.group(1)) or match.group(0)
    return re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}', _replace, value)

# ==================== 公众号订阅配置 ====================

# 过滤配置默认值（可被 config.json 的 filters 字段覆盖）
RSS_FILTERS = {
    "max_hours": 24,            # 只处理最近 N 小时的文章
    "max_articles_per_run": None  # 每轮最多处理的文章数（None 不限制）
}

def load_subscriptions():
    """
    从 config.json 加载公众号订阅配置

    优先级：config.json > 环境变量 > 默认配置
    同时读取 filters 字段更新 RSS_FILTERS。
    """
    global RSS_FILTERS

    # 方案 1: 从 config.json 加载（推荐）
    config_file = "config.json"

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                subscriptions = config.get("rss_subscriptions", [])
                for sub in subscriptions:
                    sub['url'] = substitute_env_vars(sub.get('url', ''))
                filters = config.get("filters")
                if isinstance(filters, dict):
                    RSS_FILTERS.update(filters)
                print(f"✅ 从 config.json 加载了 {len(subscriptions)} 个公众号配置")
                return subscriptions
        except Exception as e:
            print(f"⚠️ 读取 config.json 失败: {e}")

    # 方案 2: 从环境变量加载（备用方案）
    # 格式：RSS_1_NAME, RSS_1_URL, RSS_1_ENABLED
    subscriptions = []
    i = 1
    while True:
        name = os.getenv(f"RSS_{i}_NAME")
        url = os.getenv(f"RSS_{i}_URL")
        enabled_str = os.getenv(f"RSS_{i}_ENABLED", "true")

        if not name or not url:
            break  # 没有更多配置了

        subscriptions.append({
            "name": name,
            "url": url,
            "enabled": enabled_str.lower() == "true"
        })
        i += 1

    if subscriptions:
        print(f"✅ 从环境变量加载了 {len(subscriptions)} 个公众号配置")
        return subscriptions

    # 方案 3: 默认示例配置（仅用于演示）
    print("⚠️ 未找到配置文件，使用默认示例配置（请在 config.json 中配置你的公众号）")
    return [
        {
            "name": "示例公众号1",
            "url": "https://wec.zeabur.app/feed/xxxxx.xml",
            "enabled": False
        },
    ]

# 加载公众号订阅配置
RSS_SUBSCRIPTIONS = load_subscriptions()

# ==================== AI 处理器 ====================

class AIArticleProcessor:
    """AI 文章处理器"""

    def __init__(self, api_key: str, model: str = "qwen-plus"):
        dashscope.api_key = api_key
        self.model = model
        self.noise_keywords = self._default_noise_keywords()

    def _default_noise_keywords(self) -> Dict[str, List[str]]:
        """干扰关键词配置"""
        return {
            "招聘": [
                "诚聘", "热招", "急聘", "招聘", "猎头", "招贤纳士",
                "职位描述", "岗位要求", "岗位职责", "任职要求",
                "投递简历", "发送简历", "简历投递", "简历请发",
                "薪资待遇", "年薪", "月薪", "底薪", "薪资面议", "五险一金"
            ],
            "带货": [
                "限时优惠", "限时特惠", "特价", "清仓", "秒杀", "抢购", "大促",
                "立减", "满减", "优惠卷", "优惠券", "领券", "折扣",
                "立即购买", "马上抢", "点击购买", "扫码购买", "购买链接",
                "下单链接", "抢购链接", "立即下单", "马上抢购",
                "爆款推荐", "热销爆款", "火爆销售", "热销产品", "畅销",
                "包邮", "货到付款", "七天退换", "无理由退换", "正品保证",
                "原价", "现价", "促销价", "活动价", "特价"
            ],
            "课程": [
                "训练营报名", "扫码报名", "立即报名", "报名链接", "咨询报名",
                "课程优惠", "限时特价", "立减", "早鸟价", "团购价",
                "在线课程", "视频课程", "系列课程", "实战课程", "系统课程",
                "包学会", "学会为止", "免费试听", "试听课程"
            ],
            "社群": [
                "加入知识星球", "知识星球", "付费社群", "付费社群",
                "会员专区", "VIP会员", "会员服务", "成为会员",
                "加入社群", "扫码加群", "粉丝群", "交流群", "付费群",
                "社群福利", "会员福利", "专属福利", "会员专享"
            ],
            "活动推广": [
                "会议报名", "展会报名", "活动报名", "报名开启", "报名通道",
                "早鸟票", "早鸟优惠", "购票链接", "抢票", "门票",
                "名额有限", "仅限", "限时免费", "限时报名"
            ],
            "融资": [
                "轮融资", "完成融资", "获得融资", "募资完成",
                "估值", "IPO上市", "启动IPO", "挂牌上市"
            ],
            "广告": [
                "广告合作", "商业合作", "品牌赞助", "赞助商",
                "软文推广", "品牌推广", "产品推广", "商业推广"
            ]
        }

    def detect_noise(self, title: str, content: str) -> tuple:
        """
        检测文章是否为干扰内容

        Returns:
            (noise_level, noise_type, matched_keywords)
            noise_level: None/light/heavy
            noise_type: 干扰类型（如"招聘"、"带货"等）
            matched_keywords: 匹配到的关键词列表
        """
        title_matches = {}
        content_matches = {}

        # 检查标题（权重高）
        for noise_type, keywords in self.noise_keywords.items():
            matches = [kw for kw in keywords if kw in title]
            if matches:
                title_matches[noise_type] = matches

        # 检查内容
        for noise_type, keywords in self.noise_keywords.items():
            matches = [kw for kw in keywords if kw in content]
            if matches:
                content_matches[noise_type] = matches

        # 合并结果，标题优先
        all_matches = {}
        for noise_type in set(list(title_matches.keys()) + list(content_matches.keys())):
            title_count = len(title_matches.get(noise_type, []))
            content_count = len(content_matches.get(noise_type, []))
            # 标题中的关键词权重是内容的2.5倍
            weighted_count = title_count * 2.5 + content_count
            if weighted_count >= 2:  # 至少2个加权关键词
                all_matches[noise_type] = {
                    'title_kw': title_matches.get(noise_type, []),
                    'content_kw': content_matches.get(noise_type, []),
                    'weighted_count': weighted_count
                }

        if not all_matches:
            return None, None, []

        # 找到匹配度最高的类型
        max_type = max(all_matches.keys(), key=lambda k: all_matches[k]['weighted_count'])
        max_count = all_matches[max_type]['weighted_count']

        # 判断标准
        if max_count >= 5 or (max_count >= 4 and len(all_matches[max_type]['title_kw']) >= 2):
            return "heavy", max_type, []
        elif max_count >= 2.5:
            return "light", max_type, []
        else:
            return None, None, []

    def _call_model(self, prompt: str, max_tokens: int, temperature: float, max_retries: int = 3) -> str:
        """
        调用通义千问生成文本（messages 格式，DashScope 当前标准）

        对限流和服务端错误做有限次重试；认证/参数类错误不重试。

        Returns:
            模型输出文本；调用失败时返回空字符串
        """
        for attempt in range(max_retries):
            try:
                response = Generation.call(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    result_format="message",
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                if response.status_code == 200:
                    # message 格式：output.choices[0].message.content
                    choices = getattr(response.output, 'choices', None)
                    if choices:
                        return (choices[0].message.content or "").strip()
                    # 兼容旧的 text 格式
                    return (getattr(response.output, 'text', '') or '').strip()

                status = response.status_code
                print(f"模型调用失败: HTTP {status} {getattr(response, 'code', '')} {getattr(response, 'message', '')}")
                # 限流/服务端错误可重试，认证/参数错误重试无意义
                retryable = status == 429 or status >= 500
            except Exception as e:
                print(f"模型调用异常：{str(e)}")
                retryable = True

            if not retryable or attempt == max_retries - 1:
                break
            wait = 2 * (attempt + 1)
            print(f"   {wait}s 后重试（第 {attempt + 2}/{max_retries} 次）...")
            time.sleep(wait)

        return ""

    def _parse_summary_sections(self, ai_text: str) -> Tuple[str, List[str]]:
        """
        从模型输出中解析【标签】和【总结】两部分

        Returns:
            (summary, categories)
        """
        categories = []
        tag_match = re.search(r'【标签】\s*([^\n]+)', ai_text)
        if tag_match:
            categories = [t.strip() for t in re.split(r'[、,，\s]+', tag_match.group(1)) if t.strip()][:5]

        summary_match = re.search(r'【总结】\s*\n(.+)', ai_text, re.DOTALL)
        if summary_match:
            return summary_match.group(1).lstrip().rstrip(), categories

        # 没有【总结】标记时，去掉【标签】行后整体作为摘要
        summary = re.sub(r'【标签】[^\n]*', '', ai_text).lstrip().rstrip()
        return summary, categories

    def summarize_article(self, content: str, title: str = "", author: str = "") -> Tuple[str, List[str]]:
        """
        使用 AI 生成文章摘要和分类标签（单次调用）

        Args:
            content: 文章内容
            title: 文章标题（可选）
            author: 公众号名称（可选）

        Returns:
            (摘要文本, 分类标签列表)
        """
        # 截取内容（避免超出 token 限制）
        if len(content) > 4000:
            content = content[:4000]

        prompt = f"""请将以下公众号文章生成总结，要求：

【标签】
1. 输出3-5个分类标签（关键词）
2. 使用简洁的中文词汇（2-4个字）
3. 标签之间用顿号、分隔
4. 标签应该反映文章的核心主题（如：科技、互联网、商业分析等）

【总结】
1. **结构化输出**：使用 Emoji 图标作为段落标记（如🎯、🔄、🤖、💡、📊、🔍等）
2. **分段清晰**：3-5个大段，每个大段有明确的主题标题
3. **深度解析**：不是简单摘要点，而是保留关键信息和数据的深度解析
4. **格式规范**：
   - 使用分级标题（一、二、三）
   - 所有标题必须加粗（使用 **标题** 格式）
   - 关键数据用加粗标记
   - 包含具体案例和细节
5. **内容长度**：控制在500字以内
6. **段落分隔**：段落之间用空行分隔
7. **补充细节**：最后补充关键细节和背景信息（"补充细节"或者"关键细节补充"也要加粗，使用 **补充细节** 格式）

文章标题：{title}

公众号：{author}

文章内容：
{content}

请按以下格式输出：

【标签】标签1、标签2、标签3

【总结】
🎯 **第一个要点的标题**

第一个要点的详细内容...

🔄 **第二个要点的标题**

第二个要点的详细内容...

第三到第五个类似上面继续

💡 **补充细节**

关键细节和背景信息...
"""

        ai_text = self._call_model(prompt, max_tokens=1000, temperature=0.5)

        if not ai_text:
            return content[:200] + "...", []

        # 调试：打印 AI 原始返回的前 200 个字符
        print(f"       [DEBUG] AI 原始返回（前200字符）:")
        print(f"       {ai_text[:200]}...")

        summary, categories = self._parse_summary_sections(ai_text)

        if not summary or len(summary) < 50:
            print(f"       ⚠️  警告：摘要过短或为空，AI 可能未按预期生成")
            print(f"       [DEBUG] 完整 AI 返回:")
            print(f"       {ai_text}")
            return content[:500] + "...", categories

        return summary, categories


# ==================== 辅助函数 ====================

def load_seen_articles() -> Dict[str, bool]:
    """
    加载已推送文章的链接集合

    用 dict 的键保存链接（保持插入顺序，便于按时间裁剪旧记录），
    `in` / `len()` 用法与 set 一致。
    """
    if os.path.exists(SEEN_ARTICLES_FILE):
        with open(SEEN_ARTICLES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return dict.fromkeys(data.get('seen_links', []))
    return {}


def save_seen_articles(seen_links: Dict[str, bool]):
    """保存已推送文章的链接集合（超出上限时丢弃最早的记录）"""
    os.makedirs(os.path.dirname(SEEN_ARTICLES_FILE), exist_ok=True)
    links = list(seen_links.keys())
    if len(links) > MAX_SEEN_LINKS:
        links = links[-MAX_SEEN_LINKS:]
    with open(SEEN_ARTICLES_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'seen_links': links,
            'updated_at': datetime.now(CST).isoformat()
        }, f, ensure_ascii=False, indent=2)


def format_published_time(published: str) -> str:
    """
    格式化发布时间为 -YYYY-MM-DD HH:MM 格式

    Args:
        published: RSS 中的 published 字段（如 "Mon, 12 Jan 2026 12:36:00 +0800"）

    Returns:
        格式化后的时间字符串（如 "-2026-01-12 12:36"）
    """
    if not published or published == 'Unknown':
        return ""

    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(published)
        return f"-{dt.strftime('%Y-%m-%d %H:%M')}"
    except:
        return ""


def parse_published_time(published: str) -> datetime:
    """解析发布时间为 datetime 对象（用于排序）"""
    if not published or published == 'Unknown':
        # 返回带时区的最小时间，避免与带时区的发布时间比较时抛 TypeError
        return datetime.min.replace(tzinfo=timezone.utc)

    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(published)
    except:
        return datetime.min.replace(tzinfo=timezone.utc)


def _is_within_time_range(entry, time_threshold: datetime) -> bool:
    """检查文章发布时间是否在指定时间范围内"""
    from email.utils import parsedate_to_datetime

    try:
        published_str = entry.get('published') or entry.get('updated', '')
        if not published_str:
            return False  # 无法解析时间时默认过滤

        dt = parsedate_to_datetime(published_str)

        # 统一用带时区的时间比较，混合时区由 datetime 自动换算
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CST)
        if time_threshold.tzinfo is None:
            time_threshold = time_threshold.astimezone()

        return dt >= time_threshold
    except:
        return False  # 解析失败时默认过滤


def _clean_content(raw: str) -> str:
    """去除 HTML 标签、反转义 HTML 实体、压缩空白，保留纯文本"""
    text = html.unescape(re.sub(r'<[^>]+>', '', raw or ''))
    return re.sub(r'\s+', ' ', text).strip()


def _fetch_feed(url: str, max_retries: int = 2):
    """
    下载 RSS 内容并交给 feedparser 解析

    feedparser 自带抓取没有超时，慢源会挂死整个任务；
    这里改用 requests（带超时），失败时有限重试。

    Returns:
        feedparser 解析结果；下载失败返回 None
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(
                url,
                timeout=15,
                headers={"User-Agent": "WeSum/2.2 (+https://github.com/88lin/wesum-wechat-monitor)"}
            )
            resp.raise_for_status()
            return feedparser.parse(resp.content)
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                print(f"   获取失败（{str(e)}），2s 后重试...")
                time.sleep(2)

    print(f"❌ 获取 RSS 失败：{str(last_err)}")
    return None


def fetch_rss_articles(url, seen_links: Dict[str, bool] = None, max_hours: int = 24) -> Tuple[list, int]:
    """
    获取 RSS 文章列表（带记忆机制）

    Args:
        url: RSS 地址
        seen_links: 已推送文章链接集合
        max_hours: 只获取最近 N 小时内的文章（默认24小时）

    Returns:
        (文章列表, RSS 源返回的总条目数)；总条目数用于判断源是否失效
    """
    if seen_links is None:
        seen_links = {}

    if '${' in url:
        print(f"❌ RSS 地址包含未解析的环境变量占位符：{url}")
        print(f"   请在 .env 或 GitHub Secrets/Vars 中设置对应变量（如 WECHAT2RSS_DOMAIN）")
        return [], 0

    print(f"正在获取 RSS：{url}")

    feed = _fetch_feed(url)
    if feed is None:
        return [], 0

    try:
        time_threshold = datetime.now() - timedelta(hours=max_hours)

        # 基本信息
        print(f"📰 公众号：{feed.feed.get('title', 'Unknown')}")
        print(f"📊 RSS 文章总数：{len(feed.entries)}")
        print(f"⏰ 时间范围：最近 {max_hours} 小时")
        print()

        # 提取文章信息
        articles = []
        new_count = 0
        skipped_seen = 0
        skipped_time = 0

        for idx, entry in enumerate(feed.entries, 1):
            article = {
                'title': entry.get('title', '无标题'),
                'link': entry.get('link', ''),
                'author': feed.feed.get('title', 'Unknown'),
                'published': entry.get('published', entry.get('updated', '')),
                'content': ''
            }

            # 检查1: 是否已推送
            if article['link'] in seen_links:
                skipped_seen += 1
                continue

            # 检查2: 是否在时间范围内
            is_within_time = _is_within_time_range(entry, time_threshold)
            if not is_within_time:
                skipped_time += 1
                continue

            # 提取内容
            if hasattr(entry, 'content') and entry.content:
                article['content'] = entry.content[0].value
            elif hasattr(entry, 'summary'):
                article['content'] = entry.summary
            elif hasattr(entry, 'description'):
                article['content'] = entry.description

            # 清洗为纯文本并限制长度
            article['content'] = _clean_content(article['content'])
            if len(article['content']) > 2000:
                article['content'] = article['content'][:2000]

            articles.append(article)
            new_count += 1

            if new_count <= 3:  # 显示前3篇新文章的详情
                print(f"   ✅ 新文章：{article['title'][:50]}...")
                print(f"      链接：{article['link'][:80]}...")
                print(f"      时间：{article['published']}")

        print(f"   📊 统计信息：")
        print(f"      - 总文章数：{len(feed.entries)}")
        print(f"      - 已推送（跳过）：{skipped_seen}")
        print(f"      - 超时（跳过）：{skipped_time}")
        print(f"      - 新文章：{new_count}")
        print(f"   ✅ 获取到 {new_count} 篇新文章")
        return articles, len(feed.entries)

    except Exception as e:
        print(f"❌ 解析 RSS 失败：{str(e)}")
        return [], 0


# ==================== Gist 相关函数 ====================

def create_gist(content, account_name, github_token):
    """
    创建 GitHub Gist

    Args:
        content: 要存储的内容（Markdown 格式）
        account_name: 公众号名称（用于文件名）
        github_token: GitHub Personal Access Token

    Returns:
        Gist 的 HTML URL（如果成功）
        None（如果失败）
    """
    # 生成文件名（包含时间戳）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"{account_name}_摘要_{timestamp}.md"

    # Gist API 端点
    url = "https://api.github.com/gists"

    # 构建请求体
    data = {
        "description": f"{account_name} 公众号文章摘要 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "public": False,  # 私有 Gist
        "files": {
            filename: {
                "content": content
            }
        }
    }

    # 请求头
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        print(f"📤 正在创建 GitHub Gist...")
        response = requests.post(url, json=data, headers=headers, timeout=10)

        if response.status_code == 201:
            gist_data = response.json()
            gist_url = gist_data['html_url']
            print(f"✅ Gist 创建成功!")
            print(f"   URL: {gist_url}")
            return gist_url
        else:
            print(f"❌ Gist 创建失败: HTTP {response.status_code}")
            print(f"   错误信息: {response.text}")
            return None

    except Exception as e:
        print(f"❌ 创建 Gist 时发生错误: {str(e)}")
        return None


def format_push_message_for_gist(articles, title="公众号文章摘要汇总"):
    """
    格式化推送消息（用于存储到 Gist）

    Args:
        articles: 文章列表
        title: 汇总标题

    Returns:
        完整的文章摘要文本（Markdown 格式）
    """
    # 使用北京时间（UTC+8）
    now = datetime.now(CST).strftime('%Y-%m-%d %H:%M')

    # 统计公众号数量
    account_names = set(article.get('author', '') for article in articles if article.get('author'))
    account_count = len(account_names)

    # 构建完整的 Markdown 内容
    if account_count > 1:
        content = f"""# 📰 {title} ({now})

📊 订阅公众号：{account_count} 个

---

"""
    else:
        content = f"""# 📰 {title} ({now})

---

"""

    # 统计各类文章数量
    normal_count = 0
    light_noise_count = 0
    heavy_noise_count = 0

    for i, article in enumerate(articles, 1):
        noise_level = article.get('noise_level')
        noise_type = article.get('noise_type')

        # 统计文章类型
        if noise_level == "heavy":
            heavy_noise_count += 1
        elif noise_level == "light":
            light_noise_count += 1
        else:
            normal_count += 1

        # 格式化发布时间
        published_time = format_published_time(article.get('published', ''))

        # 标题（包含发布时间）
        if article.get('author'):
            content += f"## {i}. 【{article['author']}】{article['title']}{published_time}\n\n"
        else:
            content += f"## {i}. {article['title']}{published_time}\n\n"

        # 分类标签
        if article.get('categories'):
            category_str = "、".join(article['categories'])
            content += f"**🏷️ 分类**：{category_str}\n\n"

        # 根据噪音级别添加不同的提示和摘要
        if noise_level == "heavy":
            content += f"**📢 {noise_type}内容（简化版）**\n\n"
            if article.get('ai_summary'):
                content += f"{article['ai_summary']}\n\n"
        elif noise_level == "light":
            content += f"**⚠️ 可能包含{noise_type}内容**\n\n"
            if article.get('ai_summary'):
                content += f"{article['ai_summary']}\n\n"
        else:
            if article.get('ai_summary'):
                content += f"{article['ai_summary']}\n\n"

        # 原文链接
        content += f"**🔗 查看原文**：{article['link']}\n\n"
        content += "---\n\n"

    # 添加统计信息
    total_articles = normal_count + light_noise_count + heavy_noise_count

    content += f"""
## 📊 数据统计

- **正常文章**：{normal_count} 篇
- **轻度干扰**：{light_noise_count} 篇
- **重度干扰**：{heavy_noise_count} 篇（简化显示）
- **总计**：{total_articles} 篇

---

*Generated by WeSum AI 摘要助手*
"""

    return content


# ==================== 企业微信推送函数 ====================

# 企业微信 markdown 消息上限 4096 字节，留余量
WECOM_MAX_BYTES = 4000


def _build_wecom_digest(account_name, gist_url, articles, display_count, now):
    """构建企业微信摘要卡片内容（display_count 控制列表条数以便裁剪长度）"""
    article_list = ""
    for i in range(display_count):
        article = articles[i]
        published_time = format_published_time(article.get('published', ''))
        author = article.get('author', '')
        author_tag = f"【{author}】" if author else ""
        article_list += f"{i+1}. {author_tag}[{article['title']}]({article['link']}){published_time}\n"

    hidden = len(articles) - display_count
    if hidden > 0:
        article_list += f"\n... 还有 {hidden} 篇文章未显示\n"

    if gist_url:
        digest_link = f"\n👉 **[点击查看完整摘要]({gist_url})**\n"
    else:
        digest_link = "\n> ⚠️ 未配置 GITHUB_TOKEN，本次仅推送标题列表\n"

    return f"""# 📰 公众号文章更新

**公众号**: {account_name}
**更新时间**: {now}
**文章数量**: {len(articles)} 篇
{digest_link}
----
**📝 文章列表**:
-{article_list}

----
<font color="info">WeSum AI 摘要助手</font>
"""


def send_to_wechat_with_gist_link(account_name, gist_url, webhook_url, articles):
    """
    发送企业微信卡片消息（包含文章列表，可选 Gist 链接）

    Args:
        account_name: 公众号名称
        gist_url: Gist 链接（可为 None，此时仅推送标题列表）
        webhook_url: 企业微信 webhook 地址
        articles: 文章列表
    """
    # 使用北京时间（UTC+8）
    now = datetime.now(CST).strftime('%Y-%m-%d %H:%M')

    # 逐步减少列表条数，确保不超企业微信 4096 字节限制
    display_count = min(10, len(articles))  # 最多显示10篇
    content = _build_wecom_digest(account_name, gist_url, articles, display_count, now)
    while len(content.encode('utf-8')) > WECOM_MAX_BYTES and display_count > 1:
        display_count -= 1
        content = _build_wecom_digest(account_name, gist_url, articles, display_count, now)
    if len(content.encode('utf-8')) > WECOM_MAX_BYTES:
        content = content.encode('utf-8')[:WECOM_MAX_BYTES].decode('utf-8', errors='ignore') + '…'

    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }

    try:
        print(f"📤 正在发送企业微信卡片消息...")
        response = requests.post(webhook_url, json=message, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                print(f"✅ 企业微信推送成功!")
                return True
            else:
                print(f"❌ 企业微信推送失败: {result.get('errmsg')}")
                return False
        else:
            print(f"❌ 企业微信 API 错误: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 发送企业微信消息时发生错误: {str(e)}")
        return False


def send_no_new_articles_message(webhook_url):
    """
    发送无新文章通知

    Args:
        webhook_url: 企业微信 webhook 地址
    """
    # 使用北京时间（UTC+8）
    now = datetime.now(CST).strftime('%Y-%m-%d %H:%M')

    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""# 📰 公众号文章更新

**公众号**: 本次无新文章推送
**更新时间**: {now}

---
<font color="info">WeSum AI 摘要助手</font>
"""
        }
    }

    try:
        print(f"📤 正在发送无新文章通知...")
        response = requests.post(webhook_url, json=message, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                print(f"✅ 通知发送成功!")
                return True
            else:
                print(f"❌ 通知发送失败: {result.get('errmsg')}")
                return False
        else:
            print(f"❌ 企业微信 API 错误: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 发送通知时发生错误: {str(e)}")
        return False


def send_rss_source_warning_message(webhook_url, dead_feeds):
    """
    发送 RSS 源失效告警

    所有订阅源都返回 0 条内容时，大概率是 RSS 实例下线或 feed 路径失效，
    而不是"恰好没有新文章"——这种静默失效曾让本项目停摆 8 个月。

    Args:
        webhook_url: 企业微信 webhook 地址
        dead_feeds: 返回 0 条内容的公众号名称列表
    """
    # 使用北京时间（UTC+8）
    now = datetime.now(CST).strftime('%Y-%m-%d %H:%M')
    feed_names = "、".join(dead_feeds[:10])
    if len(dead_feeds) > 10:
        feed_names += f" 等 {len(dead_feeds)} 个"

    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""# ⚠️ WeSum RSS 源疑似失效

**更新时间**: {now}

所有订阅源均返回 0 条内容，可能原因：

1. `WECHAT2RSS_DOMAIN` 指向的实例已下线
2. `config.json` 中的 feed 路径失效

**受影响公众号**：{feed_names}

> 请检查 RSS 源并更新配置，否则将无法收到文章推送。
<font color="warning">WeSum AI 摘要助手</font>
"""
        }
    }

    try:
        print(f"📤 正在发送 RSS 源失效告警...")
        response = requests.post(webhook_url, json=message, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                print(f"✅ 告警发送成功!")
                return True
            else:
                print(f"❌ 告警发送失败: {result.get('errmsg')}")
                return False
        else:
            print(f"❌ 企业微信 API 错误: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 发送告警时发生错误: {str(e)}")
        return False


# ==================== 主程序 ====================

def main():
    """主函数"""
    print("=" * 60)
    print("WeSum - 微信公众号摘要推送助手")
    print("=" * 60)
    print(f"启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("工作流程：")
    print("1. 加载已推送文章记忆")
    print("2. 从多个公众号获取新文章（最近24小时）")
    print("3. AI 干扰文章识别")
    print("4. AI 分类标签生成")
    print("5. AI 摘要生成")
    print("6. 创建 GitHub Gist")
    print("7. 推送到企业微信")
    print("8. 保存已推送文章记忆")
    print()
    print("=" * 60)
    print()

    # 1. 加载已推送文章记忆
    print("[Step 1] 加载已推送文章记忆...")
    seen_links = load_seen_articles()
    print(f"   ✅ 已记录 {len(seen_links)} 篇文章")
    print()

    # 2. 筛选启用的订阅
    active_subscriptions = [sub for sub in RSS_SUBSCRIPTIONS if sub.get('enabled', True)]

    if not active_subscriptions:
        print("❌ 没有启用的公众号订阅")
        exit(1)

    print(f"[Step 2] 订阅配置：{len(active_subscriptions)} 个公众号")
    for sub in active_subscriptions:
        print(f"   - {sub['name']}")
    print()

    # 3. 从多个公众号获取文章
    print("[Step 3] 从多个公众号获取新文章...")
    all_articles = []
    dead_feeds = []       # 返回 0 条内容的订阅（源可能失效）
    total_entries = 0     # 所有源返回的总条目数

    max_hours = int(RSS_FILTERS.get("max_hours") or 24)
    print(f"   过滤配置：最近 {max_hours} 小时，每轮最多 "
          f"{RSS_FILTERS.get('max_articles_per_run') or '不限'} 篇")

    for subscription in active_subscriptions:
        account_name = subscription['name']
        rss_url = subscription['url']

        print(f"\n正在获取【{account_name}】的文章...")
        articles, feed_entries = fetch_rss_articles(rss_url, seen_links=seen_links, max_hours=max_hours)
        total_entries += feed_entries

        if articles:
            all_articles.extend(articles)
        elif feed_entries == 0:
            dead_feeds.append(account_name)
            print(f"   ⚠️ 该源返回 0 条内容（源可能已失效）")
        else:
            print(f"   ⚠️ 无新文章")

    if not all_articles:
        print("\n❌ 没有获取到任何新文章")

        # 所有源都返回 0 条 → RSS 源疑似失效，而不是"恰好没有新文章"
        if total_entries == 0 and dead_feeds:
            print(f"\n🚨 所有 RSS 源均返回 0 条内容，疑似源失效！受影响：{'、'.join(dead_feeds)}")
            print("   请检查 WECHAT2RSS_DOMAIN 指向的实例是否可用，以及 config.json 中的 feed 路径是否有效")
            send_rss_source_warning_message(WEBHOOK_URL, dead_feeds)
            print("\n❌ 运行失败（RSS 源疑似失效）")
            exit(1)

        # 检查当前时间是否在静默时段（0-9点）
        current_hour = datetime.now().hour
        if 0 <= current_hour < 9:
            print(f"\n⏰ 当前时间 {current_hour}:00 处于静默时段（0-9点），跳过空消息推送")
            print("\n✅ 运行完成（静默时段，无新文章）")
            exit(0)

        print("\n[Step 4] 发送无新文章通知...")
        send_no_new_articles_message(WEBHOOK_URL)
        print("\n✅ 运行完成（无新文章需要处理）")
        exit(0)

    # 同一篇文章出现在多个订阅时只处理一次
    unique_links = set()
    deduped_articles = []
    for article in all_articles:
        if article['link'] and article['link'] in unique_links:
            continue
        unique_links.add(article['link'])
        deduped_articles.append(article)
    all_articles = deduped_articles

    print(f"\n📊 总计获取 {len(all_articles)} 篇新文章")

    # 4. 按发布时间降序排序
    print("\n[Step 4] 按发布时间降序排序...")
    all_articles.sort(key=lambda a: parse_published_time(a.get('published', '')), reverse=True)
    print(f"   ✅ 排序完成")

    # 每轮处理数量上限（未处理的文章不记入记忆，下次运行继续）
    max_per_run = RSS_FILTERS.get("max_articles_per_run")
    if max_per_run and len(all_articles) > int(max_per_run):
        print(f"   ✂️ 每轮上限 {int(max_per_run)} 篇，剩余 {len(all_articles) - int(max_per_run)} 篇留待下次运行")
        all_articles = all_articles[:int(max_per_run)]

    print()
    print("=" * 60)
    print()

    # 创建 AI 处理器（模型可用环境变量 WECHAT_MODEL 覆盖）
    ai_processor = AIArticleProcessor(
        api_key=DASHSCOPE_API_KEY,
        model=os.getenv("WECHAT_MODEL", "qwen-plus")
    )

    processed_articles = []

    # 处理每篇文章
    for i, article in enumerate(all_articles, 1):
        print(f"正在处理第 {i}/{len(all_articles)} 篇文章...")
        print(f"标题: {article['title']}")
        print(f"公众号: {article.get('author', 'Unknown')}")
        print()

        # 步骤 1: 干扰文章识别
        print("  [1/2] 识别干扰内容...")
        noise_level, noise_type, matched_keywords = ai_processor.detect_noise(
            article['title'],
            article['content']
        )
        article['noise_level'] = noise_level
        article['noise_type'] = noise_type

        if noise_level:
            print(f"       检测到：{noise_type} ({noise_level})")
        else:
            print(f"       ✅ 正常文章")

        # 如果是重度干扰，跳过后续处理
        if noise_level == "heavy":
            print(f"       ⚠️ 已过滤，不进行后续处理")
            processed_articles.append(article)
            print()
            continue

        # 步骤 2: 单次调用生成摘要 + 分类标签
        print("  [2/2] 生成 AI 摘要与分类...")
        summary, categories = ai_processor.summarize_article(
            article['content'],
            article['title']
        )
        article['ai_summary'] = summary
        article['categories'] = categories
        print(f"       标签：{'、'.join(categories) if categories else '未生成'}")
        print(f"       ✅ 摘要生成完成")

        # 打印完整的 AI 摘要内容（便于调试）
        print()
        print("       📝 摘要内容：")
        print("       " + "=" * 56)
        # 打印摘要，每行前面加缩进
        for line in summary.split('\n'):
            print(f"       {line}")
        print("       " + "=" * 56)

        processed_articles.append(article)
        print()

    if not processed_articles:
        print("❌ 没有可推送的文章")
        exit(0)

    # 格式化 Gist 内容
    print("=" * 60)
    print("格式化 Gist 内容")
    print("=" * 60)
    print()

    # 生成汇总标题
    account_names = set(article.get('author', '') for article in processed_articles if article.get('author'))
    account_count = len(account_names)
    article_count = len(processed_articles)

    summary_title = f"文章摘要汇总【{account_count}个公众号、{article_count}篇文章】"

    gist_content = format_push_message_for_gist(processed_articles, summary_title)

    print(f"✅ Gist 内容格式化完成")
    print(f"内容长度: {len(gist_content)} 字符")
    print()

    # 创建 GitHub Gist（可选：未配置 token 时降级为仅标题列表推送）
    print("=" * 60)
    print("创建 GitHub Gist")
    print("=" * 60)
    print()

    if GITHUB_TOKEN:
        gist_url = create_gist(gist_content, summary_title, GITHUB_TOKEN)

        if not gist_url:
            # Gist 失败通常是暂时性问题；本轮终止，文章不记入记忆，下次运行自动重试
            print("❌ Gist 创建失败，终止流程（文章将留待下次运行重试）")
            exit(1)
    else:
        print("⚠️ 未配置 GITHUB_TOKEN，跳过 Gist，降级为仅标题列表推送")
        gist_url = None

    print()

    # 推送到企业微信（使用 Gist 链接）
    print()
    print("=" * 60)
    print("推送到企业微信（Gist 链接）")
    print("=" * 60)
    print()

    success = send_to_wechat_with_gist_link(
        account_name=summary_title,
        gist_url=gist_url,
        webhook_url=WEBHOOK_URL,
        articles=processed_articles
    )

    print()
    print("=" * 60)
    print("运行结果")
    print("=" * 60)
    print()

    if success:
        print("✅ 企业微信推送成功！")

        # 8. 保存已推送文章记忆
        print("\n[Step 8] 保存已推送文章记忆...")
        for article in processed_articles:
            seen_links[article['link']] = True
        save_seen_articles(seen_links)
        print(f"   ✅ 已保存 {len(processed_articles)} 篇文章到记忆库")
        print(f"   📝 记忆文件: {SEEN_ARTICLES_FILE}")
        print(f"   📊 总记忆数: {len(seen_links)} 篇")
        print()

        print("📊 处理统计：")
        print(f"   - 订阅公众号：{len(account_names)} 个")
        print(f"   - 本次文章：{len(processed_articles)} 篇")
        print(f"   - 历史记忆：{len(seen_links)} 篇")
        print(f"   - Gist 链接：{gist_url}")
        print(f"   - 企业微信：卡片消息已发送")
        print()
        print("💡 用户操作：")
        print("   1. 打开企业微信")
        print("   2. 点击卡片中的链接")
        print("   3. 查看完整的文章摘要（Markdown 格式）")
        print()
        print("⏰ 适合 GitHub Actions 定时任务：")
        print("   - 建议频率：每小时运行一次")
        print("   - 记忆机制：自动避免重复推送")
        print("   - 时间过滤：只处理最新24小时文章")
    else:
        print("❌ 推送失败，请检查配置")
        print("⚠️ 由于推送失败，本次文章未保存到记忆库")
        print("   下次运行时会重新处理这些文章")

    print()


if __name__ == "__main__":
    main()
