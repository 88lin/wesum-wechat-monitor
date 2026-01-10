"""
文章分类模块
使用 AI + 关键词判断文章类型和是否为干扰内容
"""

import json
import re
from typing import Dict, List


class ArticleClassifier:
    """文章分类器"""

    def __init__(self, noise_keywords: Dict[str, List[str]] = None):
        """
        初始化文章分类器

        Args:
            noise_keywords: 干扰类型的关键词字典
        """
        self.noise_keywords = noise_keywords or self._default_noise_keywords()

    def _default_noise_keywords(self) -> Dict[str, List[str]]:
        """默认的干扰关键词"""
        return {
            "招聘": ["招聘", "诚聘", "猎头", "职位", "JD", "简历", "应聘", "面试"],
            "带货": ["购买", "下单", "优惠", "限时", "折扣", "促销", "购买链接", "立即抢"],
            "广告": ["赞助", "广告", "品牌推广", "商业合作"],
            "课程": ["课程", "训练营", "扫码", "立减", "报名", "学习"],
            "社群": ["知识星球", "付费社群", "会员", "加入社群", "社群"],
            "活动推广": ["会议报名", "展会报名", "早鸟票", "活动报名", "立即报名", "报名开启"],
            "融资": ["融资", "轮融资", "估值", "投资方", "募资"],
            "公关": ["发布", "新品发布", "隆重推出", "盛大发布", "战略合作", "签署协议", "获奖"]
        }

    def classify(self, article: Dict) -> Dict:
        """
        分类文章（AI + 关键词辅助）

        Args:
            article: 文章信息（包含 title, content）

        Returns:
            分类结果字典：
            {
                "categories": ["AI", "芯片"],  # 3-5个分类标签
                "is_noise": false,              # 是否为干扰内容
                "noise_type": null,             # 干扰类型（招聘、带货等）
                "noise_level": null             # 干扰级别（noise/pr/light）
            }
        """
        title = article.get('title', '')
        content = article.get('content', '')

        # 步骤1：关键词匹配（辅助判断）
        keyword_result = self._match_keywords(title + content)

        # 步骤2：如果关键词匹配度高，直接判断
        if keyword_result['confidence'] > 0.8:
            return self._build_result(
                categories=keyword_result['categories'],
                is_noise=True,
                noise_type=keyword_result['noise_type'],
                noise_level=self._get_noise_level(keyword_result['noise_type'])
            )

        # 步骤3：正常文章，返回空标签（后续由 AI 生成）
        return {
            "categories": [],
            "is_noise": False,
            "noise_type": None,
            "noise_level": None
        }

    def _match_keywords(self, text: str) -> Dict:
        """
        关键词匹配

        Args:
            text: 文章标题+内容

        Returns:
            匹配结果
        """
        matched_types = []
        total_keywords = 0
        matched_keywords = 0

        for noise_type, keywords in self.noise_keywords.items():
            type_count = 0
            for keyword in keywords:
                total_keywords += 1
                if keyword in text:
                    matched_keywords += 1
                    type_count += 1

            if type_count > 0:
                matched_types.append(noise_type)

        # 计算置信度
        confidence = matched_keywords / total_keywords if total_keywords > 0 else 0

        # 确定主要的干扰类型
        noise_type = matched_types[0] if matched_types else None

        return {
            "categories": matched_types,
            "confidence": confidence,
            "noise_type": noise_type
        }

    def _get_noise_level(self, noise_type: str) -> str:
        """
        获取干扰级别

        Args:
            noise_type: 干扰类型

        Returns:
            noise（必须过滤）/pr（仅推送标题）/light（可推送）
        """
        # 必须过滤的类型
        if noise_type in ["招聘", "带货", "广告", "课程", "社群", "活动推广"]:
            return "noise"

        # 仅推送标题的类型
        if noise_type in ["融资", "公关"]:
            return "pr"

        return "light"

    def _build_result(self, categories: List[str], is_noise: bool,
                     noise_type: str, noise_level: str) -> Dict:
        """构建分类结果"""
        return {
            "categories": categories,
            "is_noise": is_noise,
            "noise_type": noise_type,
            "noise_level": noise_level
        }
