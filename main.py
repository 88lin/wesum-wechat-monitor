"""
WeSum - 微信公众号小时级摘要推送助手
主程序
"""

import json
import sys
import os
from datetime import datetime

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rss_parser import RSSParser
from ai_summarizer import AISummarizer
from push_notifier import PushNotifier
from article_classifier import ArticleClassifier


def load_config(config_file: str = "config.json") -> dict:
    """加载配置文件"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """主函数"""
    print("=" * 60)
    print("WeSum - 微信公众号摘要推送助手")
    print("=" * 60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. 加载配置
        print("\n[Step 1] Loading configuration...")
        config = load_config()
        print("Configuration loaded successfully.")

        # 2. 初始化模块
        print("\n[Step 2] Initializing modules...")
        rss_parser = RSSParser(
            rss_url=config['rss']['url'],
            seen_articles_file=config['storage']['seen_articles_file']
        )

        ai_summarizer = AISummarizer(
            api_key=config['ai']['api_key'],
            model=config['ai']['model'],
            max_tokens=config['ai']['max_tokens']
        )

        article_classifier = ArticleClassifier()

        push_notifier = PushNotifier(
            sendkey=config['push']['sendkey'],
            title_prefix=config['push']['title_prefix']
        )
        print("Modules initialized successfully.")

        # 3. 获取新文章
        print("\n[Step 3] Fetching new articles...")
        max_articles = config['filters'].get('max_articles_per_run', None)  # 支持无限制
        max_hours = config['filters'].get('max_hours', 24)  # 默认24小时
        articles = rss_parser.fetch_articles(max_articles=max_articles, max_hours=max_hours)

        if not articles:
            print("No new articles found. Exiting.")
            return

        print(f"Found {len(articles)} new articles.")

        # 4. 分类文章（关键词匹配）
        print("\n[Step 4] Classifying articles...")
        for article in articles:
            classification = article_classifier.classify(article)
            article['categories'] = classification['categories']
            article['is_noise'] = classification['is_noise']
            article['noise_type'] = classification['noise_type']
            article['noise_level'] = classification['noise_level']
        print("Classification completed.")

        # 5. 生成摘要（根据分类使用不同的摘要方式）
        print("\n[Step 5] Generating summaries...")
        for i, article in enumerate(articles, 1):
            print(f"Processing {i}/{len(articles)}: {article['title'][:30]}...")

            # 干扰文章：生成简化摘要（100字以内）
            if article['is_noise'] and article['noise_level'] in ['noise', 'pr']:
                summary = ai_summarizer.generate_simple_summary(article, article['noise_type'])
                article['summary'] = summary
                print(f"  → Simple summary ({article['noise_type']})")
            # 正常文章：生成完整总结（500字，包含分类标签）
            else:
                result = ai_summarizer.generate_summary(article)
                article['summary'] = result['summary']
                # 如果 AI 生成了标签，使用 AI 的标签；否则保留关键词匹配的标签
                if result['categories']:
                    article['categories'] = result['categories']
                print(f"  → Full summary with tags: {article['categories']}")

        print("Summaries generated successfully.")

        # 6. 批量推送到微信
        print("\n[Step 6] Pushing to WeChat...")
        if push_notifier.send_articles_batch(articles):
            print(f"Batch push notification sent successfully! ({len(articles)} articles)")
        else:
            print("Failed to send push notification.")

        # 7. 完成
        print("\n" + "=" * 60)
        print(f"WeSum completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Processed {len(articles)} articles.")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"\n[ERROR] Config file not found: {e}")
        print("Please create 'config.json' based on 'config.example.json'")
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
