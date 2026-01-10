"""
RSS 解析模块
负责从 Wewe-RSS 获取公众号文章并解析
"""

import feedparser
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class RSSParser:
    """RSS 解析器"""

    def __init__(self, rss_url: str, seen_articles_file: str):
        """
        初始化 RSS 解析器

        Args:
            rss_url: RSS 地址
            seen_articles_file: 已抓取文章记录文件路径
        """
        self.rss_url = rss_url
        self.seen_articles_file = seen_articles_file
        self.seen_articles = self._load_seen_articles()

    def _load_seen_articles(self) -> set:
        """加载已抓取文章的链接集合"""
        if os.path.exists(self.seen_articles_file):
            with open(self.seen_articles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('seen_links', []))
        return set()

    def _save_seen_articles(self):
        """保存已抓取文章的链接集合"""
        os.makedirs(os.path.dirname(self.seen_articles_file), exist_ok=True)
        with open(self.seen_articles_file, 'w', encoding='utf-8') as f:
            json.dump({
                'seen_links': list(self.seen_articles),
                'updated_at': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

    def fetch_articles(self, max_articles: Optional[int] = None, max_hours: int = 24) -> List[Dict]:
        """
        获取新文章

        Args:
            max_articles: 最大文章数量（None = 无限制）
            max_hours: 只抓取最近 N 小时内发布的文章

        Returns:
            文章列表，每篇文章包含 title, link, published, content
        """
        # 解析 RSS
        feed = feedparser.parse(self.rss_url)

        # 计算时间阈值
        time_threshold = datetime.now() - timedelta(hours=max_hours)

        # 提取文章信息
        articles = []
        for entry in feed.entries:
            article = {
                'title': entry.title,
                'link': entry.link,
                'published': entry.get('published', 'Unknown'),
                'author': entry.get('author', 'Unknown'),  # 公众号名称
                'content': self._extract_content(entry)
            }

            # 检查是否已抓取
            if article['link'] not in self.seen_articles:
                # 检查发布时间是否在时间范围内
                if self._is_within_time_range(entry, time_threshold):
                    articles.append(article)
                    self.seen_articles.add(article['link'])

                    # 达到最大数量后停止（如果有上限）
                    if max_articles is not None and len(articles) >= max_articles:
                        break

        # 保存已抓取记录
        if articles:
            self._save_seen_articles()

        return articles

    def _is_within_time_range(self, entry, time_threshold: datetime) -> bool:
        """
        检查文章发布时间是否在指定时间范围内

        Args:
            entry: RSS 文章条目
            time_threshold: 时间阈值

        Returns:
            True 如果在时间范围内，False 否则
        """
        # 尝试解析发布时间
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            # feedparser 会将时间转换为 time.struct_time
            import time
            published_datetime = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            return published_datetime >= time_threshold
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            # 如果没有 published，尝试使用 updated
            import time
            updated_datetime = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            return updated_datetime >= time_threshold
        else:
            # 如果无法解析时间，默认保留（防止丢失文章）
            return True

    def _extract_content(self, entry) -> str:
        """提取文章内容"""
        # 尝试从不同字段获取内容
        if hasattr(entry, 'content') and entry.content:
            return entry.content[0].value
        elif hasattr(entry, 'summary') and entry.summary:
            return entry.summary
        elif hasattr(entry, 'description') and entry.description:
            return entry.description
        else:
            return ""


# 测试代码
if __name__ == "__main__":
    parser = RSSParser(
        rss_url="http://localhost:4000/feeds/all.atom",
        seen_articles_file="data/seen_articles.json"
    )

    articles = parser.fetch_articles(max_articles=5)

    print(f"Found {len(articles)} new articles:")
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}] {article['title']}")
        print(f"Link: {article['link']}")
        print(f"Published: {article['published']}")