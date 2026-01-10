"""
AI 总结生成模块
使用通义千问 API 生成文章深度总结
"""

import dashscope
from dashscope import Generation
from typing import Dict


class AISummarizer:
    """AI 总结生成器"""

    def __init__(self, api_key: str, model: str = "qwen-turbo", max_tokens: int = 1000):
        """
        初始化 AI 总结生成器

        Args:
            api_key: 通义千问 API Key
            model: 模型名称
            max_tokens: 最大 token 数（默认 1000，适合 500 字总结）
        """
        dashscope.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    def generate_summary(self, article: Dict, prompt_template: str = None) -> Dict:
        """
        生成单篇文章深度总结（包含分类标签）

        Args:
            article: 文章信息（包含 title, content）
            prompt_template: 自定义提示词模板

        Returns:
            {
                "summary": "总结文本",
                "categories": ["标签1", "标签2", "标签3"]
            }
        """
        # 使用默认提示词或自定义提示词
        if prompt_template is None:
            prompt_template = """请将以下公众号文章生成总结，要求：

**分类标签**：
1. 首先输出 3-5 个分类标签（关键词）
2. 使用简洁的中文词汇（2-4个字）
3. 标签之间用顿号分隔
4. 标签应该反映文章的核心主题

**文章总结**：
5. 结构化输出：使用 Emoji 图标作为段落标记（如🎯、🔄、🤖等）
6. 分段清晰：每个大段有明确的主题标题
7. 深度解析：不是简单摘要点，而是保留关键信息和数据的深度解析
8. 格式规范：
   - 使用分级标题（一、二、三）
   - 关键数据用加粗标记
   - 包含具体案例和细节
9. 内容长度：控制在500字以内
10. 补充细节：最后补充关键细节和背景信息

**输出格式**：
【标签】标签1、标签2、标签3

【总结】
（文章总结内容...）

---

文章标题：{title}

文章内容：
{content}

请按格式生成："""

        # 构建提示词
        prompt = prompt_template.format(
            title=article['title'],
            content=article.get('content', '')[:4000]  # 扩大内容长度限制
        )

        try:
            # 调用 API
            response = Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=self.max_tokens
            )

            if response.status_code == 200:
                ai_text = response.output.text
                # 解析 AI 返回的内容，提取标签和摘要
                return self._parse_ai_response(ai_text)
            else:
                return {
                    "summary": f"API 错误: {response.code} - {response.message}",
                    "categories": []
                }

        except Exception as e:
            return {
                "summary": f"生成摘要失败: {str(e)}",
                "categories": []
            }

    def _parse_ai_response(self, ai_text: str) -> Dict:
        """
        解析 AI 返回的内容，提取标签和摘要

        Args:
            ai_text: AI 返回的完整文本

        Returns:
            {
                "summary": "摘要内容",
                "categories": ["标签1", "标签2"]
            }
        """
        import re

        # 尝试提取【标签】部分
        categories = []
        summary = ai_text

        # 查找【标签】标记
        tag_match = re.search(r'【标签】(.+?)(?:\n|$)', ai_text)
        if tag_match:
            tag_text = tag_match.group(1).strip()
            # 解析标签（支持顿号、逗号分隔）
            categories = re.split(r'[、,，\s]+', tag_text)
            categories = list(set([c for c in categories if c.strip()]))
            categories = categories[:5]  # 限制为 5 个

        # 查找【总结】标记
        summary_match = re.search(r'【总结】\s*\n(.+)', ai_text, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        else:
            # 如果没有【总结】标记，去除【标签】部分
            summary = re.sub(r'【标签】.+\n', '', ai_text).strip()

        return {
            "summary": summary,
            "categories": categories
        }

    def generate_simple_summary(self, article: Dict, noise_type: str) -> str:
        """
        生成干扰文章的简化摘要（3-5个关键要点，100字以内）

        Args:
            article: 文章信息
            noise_type: 干扰类型（招聘、带货、融资等）

        Returns:
            简化摘要文本
        """
        # 根据干扰类型定制要点要求
        points_requirements = {
            "招聘": "- 招聘公司\n- 招聘岗位\n- 薪资范围\n- 工作地点\n- 岗位要求",
            "带货": "- 产品名称\n- 产品价格\n- 优惠信息\n- 购买方式\n- 活动时间",
            "广告": "- 品牌/产品\n- 核心信息\n- 推广内容",
            "课程": "- 课程名称\n- 讲师/机构\n- 课程价格\n- 课程时长\n- 报名方式",
            "社群": "- 社群名称\n- 社群类型\n- 加入方式\n- 费用信息",
            "活动推广": "- 活动名称\n- 活动时间\n- 活动地点\n- 票价信息\n- 报名方式",
            "融资": "- 融资公司\n- 融资轮次\n- 融资金额\n- 投资方\n- 公司估值",
            "公关": "- 公司/品牌\n- 核心信息\n- 发布时间\n- 相关数据"
        }

        requirements = points_requirements.get(noise_type, "- 要点1\n- 要点2\n- 要点3")

        prompt_template = f"""请将以下公众号文章提取为关键要点，要求：

1. 提炼3-5个关键要点
2. 每个要点不超过15字
3. 严格控制在100字以内
4. 必须包含以下信息：
{requirements}

文章标题：{{title}}

文章内容：
{{content}}

请生成关键要点（列表格式）："""

        # 使用较少的 token
        prompt = prompt_template.format(
            title=article['title'],
            content=article.get('content', '')[:2000]
        )

        try:
            response = Generation.call(
                model=self.model,
                prompt=prompt,
                max_tokens=300  # 简化摘要用更少的 token
            )

            if response.status_code == 200:
                return response.output.text
            else:
                return f"API 错误: {response.code}"

        except Exception as e:
            return f"生成简化摘要失败: {str(e)}"

    def generate_batch_summaries(self, articles: list[Dict]) -> list[Dict]:
        """
        批量生成文章深度总结

        Args:
            articles: 文章列表

        Returns:
            带总结的文章列表
        """
        results = []
        for i, article in enumerate(articles, 1):
            print(f"Generating summary {i}/{len(articles)}: {article['title'][:30]}...")

            summary = self.generate_summary(article)
            article['summary'] = summary
            results.append(article)

        return results


# 测试代码
if __name__ == "__main__":
    summarizer = AISummarizer(api_key="your-api-key-here")

    test_article = {
        'title': '老黄All in物理AI！最新GPU性能5倍提升',
        'content': '英伟达 CEO 黄仁勋在 CES 2025 上发表主题演讲，宣布推出新一代 GPU 产品 Blackwell。据介绍，Blackwell GPU 相比上一代性能提升 5 倍，能效比提升 2 倍。'
    }

    summary = summarizer.generate_summary(test_article)
    print("Summary:")
    print(summary)
