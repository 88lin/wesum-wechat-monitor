"""
微信推送模块
使用 Server酱 推送消息到微信
"""

import requests
from typing import List, Dict
from datetime import datetime
import time


class PushNotifier:
    """推送通知器"""

    def __init__(self, sendkey: str, title_prefix: str = ""):
        """
        初始化推送通知器

        Args:
            sendkey: Server酱 SendKey
            title_prefix: 标题前缀
        """
        self.sendkey = sendkey
        self.title_prefix = title_prefix
        self.api_url = f"https://sctapi.ftqq.com/{sendkey}.send"

    def send_single_article(self, article: Dict) -> bool:
        """
        推送单篇文章总结（支持正常文章、干扰文章、公关文章）

        Args:
            article: 文章信息（包含 title, summary, link, author, categories, noise_type, noise_level, published）

        Returns:
            是否成功
        """
        # 标题格式：【公众号名】文章标题【-YYYYMMDDHHMM】
        author = article.get('author', '')
        published_time = self._format_published_time(article.get('published', ''))

        if author and author != 'Unknown':
            title = f"【{author}】{article['title']}{published_time}"
        else:
            title = f"{self.title_prefix} {article['title']}{published_time}"

        # 根据文章类型生成不同的推送内容
        content = self._format_content(article)

        return self._send_request(title, content)

    def _format_content(self, article: Dict) -> str:
        """
        根据文章类型格式化推送内容

        Args:
            article: 文章信息

        Returns:
            格式化后的内容
        """
        noise_level = article.get('noise_level')
        noise_type = article.get('noise_type')
        categories = article.get('categories', [])

        # 格式化分类标签
        category_str = "、".join(categories) if categories else "未分类"

        # 正常文章：完整总结
        if noise_level is None or noise_level == "light":
            content = f"🏷️ {category_str}\n\n{article.get('summary', '无总结')}\n\n[查看原文]({article['link']})"

        # 干扰文章（招聘、带货等）：简化要点
        elif noise_level == "noise":
            noise_type_name = self._get_noise_type_name(noise_type)
            content = f"🏷️ {category_str}\n\n⚠️ 本文识别为【{noise_type_name}】类型，仅推送关键要点：\n\n{article.get('summary', '无总结')}\n\n[查看原文]({article['link']})"

        # 公关文章（融资等）：简化要点
        elif noise_level == "pr":
            content = f"🏷️ {category_str}\n\n⚠️ 本文识别为【{noise_type}】类型，仅推送关键要点：\n\n{article.get('summary', '无总结')}\n\n[查看原文]({article['link']})"

        else:
            content = f"{article.get('summary', '无总结')}\n\n[查看原文]({article['link']})"

        return content

    def _get_noise_type_name(self, noise_type: str) -> str:
        """获取干扰类型的中文名称"""
        type_names = {
            "招聘": "招聘广告",
            "带货": "产品推广",
            "广告": "商业广告",
            "课程": "付费课程",
            "社群": "社群推广",
            "活动推广": "活动推广"
        }
        return type_names.get(noise_type, noise_type)

    def _format_published_time(self, published: str) -> str:
        """
        格式化发布时间为 -YYYY-MM-DD HH:MM 格式

        Args:
            published: RSS 中的 published 字段（如 "Sat, 11 Jan 2026 10:30:00 GMT"）

        Returns:
            格式化后的时间字符串（如 "-2026-01-11 10:30"），如果解析失败返回空字符串
        """
        if not published or published == 'Unknown':
            print(f"[DEBUG] Published time is empty or Unknown: '{published}'")
            return ""

        try:
            print(f"[DEBUG] Parsing published time: '{published}'")

            # 尝试解析 RSS 时间格式（RFC 2822）
            # feedparser 会将时间解析为 time.struct_time
            import feedparser

            # 先尝试用 feedparser 解析
            parsed = feedparser.parse(published)
            if hasattr(parsed, 'entries') and len(parsed.entries) > 0:
                time_struct = parsed.entries[0].get('published_parsed')
                if time_struct:
                    dt = datetime.fromtimestamp(time.mktime(time_struct))
                    result = f"-{dt.strftime('%Y-%m-%d %H:%M')}"
                    print(f"[DEBUG] Successfully parsed with feedparser: {result}")
                    return result

            # 如果 feedparser 解析失败，尝试其他常见格式
            # RFC 2822 格式：Sat, 11 Jan 2026 10:30:00 GMT
            try:
                dt = datetime.strptime(published, '%a, %d %b %Y %H:%M:%S %Z')
                result = f"-{dt.strftime('%Y-%m-%d %H:%M')}"
                print(f"[DEBUG] Successfully parsed with strptime: {result}")
                return result
            except Exception as e:
                print(f"[DEBUG] strptime failed: {e}")

            # ISO 8601 格式：2026-01-11T10:30:00Z
            try:
                dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
                result = f"-{dt.strftime('%Y-%m-%d %H:%M')}"
                print(f"[DEBUG] Successfully parsed with fromisoformat: {result}")
                return result
            except Exception as e:
                print(f"[DEBUG] fromisoformat failed: {e}")

            # 如果所有解析都失败，返回空字符串
            print(f"[DEBUG] All parsing methods failed for: '{published}'")
            return ""

        except Exception as e:
            print(f"[ERROR] Failed to parse published time '{published}': {e}")
            return ""

    def send_articles_batch(self, articles: List[Dict]) -> bool:
        """
        批量推送文章汇总（所有文章合并为1条推送）

        Args:
            articles: 文章列表

        Returns:
            是否成功
        """
        if not articles:
            print("No articles to push.")
            return False

        # 统计文章类型
        normal_count = sum(1 for a in articles if a.get('noise_level') in [None, 'light'])
        noise_count = len(articles) - normal_count

        # 构建标题
        title = f"{self.title_prefix} 公众号摘要汇总（{len(articles)}篇）"

        # 构建汇总内容
        from datetime import datetime, timezone, timedelta

        # 使用北京时间（UTC+8）
        beijing_tz = timezone(timedelta(hours=8))
        now_beijing = datetime.now(beijing_tz)

        content = f"📰 本次更新：共 {len(articles)} 篇文章\n"
        content += f"🕐 更新时间：{now_beijing.strftime('%Y-%m-%d %H:%M')}\n\n"
        content += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # 遍历每篇文章
        for i, article in enumerate(articles, 1):
            # 标题：包含公众号名、文章标题和发布时间
            author = article.get('author', 'Unknown')
            published_time = self._format_published_time(article.get('published', ''))

            if author and author != 'Unknown':
                article_title = f"【{author}】{article['title']}{published_time}"
            else:
                article_title = f"{article['title']}{published_time}"

            content += f"### {i}. {article_title}\n\n"

            # 分类标签
            categories = article.get('categories', [])
            print(f"[DEBUG] Article {i} categories: {categories}")
            if categories:
                category_str = "、".join(categories)
                content += f"🏷️ {category_str}\n\n"
                print(f"[DEBUG] Added tags to content: 🏷️ {category_str}")
            else:
                # 没有标签时，添加空行保持格式一致
                content += "\n"
                print(f"[DEBUG] No tags found for article {i}")

            # 根据文章类型添加内容
            noise_level = article.get('noise_level')
            noise_type = article.get('noise_type')

            # 正常文章：完整总结
            if noise_level is None or noise_level == "light":
                content += f"{article.get('summary', '无总结')}\n\n"

            # 干扰文章（招聘、带货等）：简化要点
            elif noise_level == "noise":
                noise_type_name = self._get_noise_type_name(noise_type)
                content += f"⚠️ 本文识别为【{noise_type_name}】类型，仅推送关键要点：\n\n"
                content += f"{article.get('summary', '无总结')}\n\n"

            # 公关文章（融资等）：简化要点
            elif noise_level == "pr":
                content += f"⚠️ 本文识别为【{noise_type}】类型，仅推送关键要点：\n\n"
                content += f"{article.get('summary', '无总结')}\n\n"

            # 查看原文链接
            content += f"🔗 [查看原文]({article['link']})\n\n"
            content += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # 添加统计信息
        content += f"📊 数据统计：\n"
        content += f"• 正常文章：{normal_count} 篇\n"
        content += f"• 简化摘要：{noise_count} 篇\n"

        return self._send_request(title, content)

    def _send_request(self, title: str, content: str) -> bool:
        """
        发送推送请求

        Args:
            title: 标题
            content: 内容（支持 Markdown）

        Returns:
            是否成功
        """
        try:
            response = requests.post(
                self.api_url,
                data={
                    "title": title,
                    "desp": content
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    print(f"Push success: {title}")
                    return True
                else:
                    print(f"Push failed: {result.get('message', 'Unknown error')}")
                    return False
            else:
                print(f"HTTP error: {response.status_code}")
                return False

        except Exception as e:
            print(f"Push error: {str(e)}")
            return False


# 测试代码
if __name__ == "__main__":
    notifier = PushNotifier(
        sendkey="your-sendkey-here",
        title_prefix="【WeSum 测试】"
    )

    test_articles = [
        {
            'title': '测试文章1',
            'summary': '- 摘要1\n- 摘要2',
            'link': 'https://example.com/1'
        },
        {
            'title': '测试文章2',
            'summary': '- 摘要3\n- 摘要4',
            'link': 'https://example.com/2'
        }
    ]

    notifier.send_batch_summary(test_articles)
