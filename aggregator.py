"""审查结果聚合器"""
from dataclasses import dataclass
from typing import List, Dict
from ai_clients import AIResponse


@dataclass
class ReviewSummary:
    """审查摘要"""
    total_reviews: int
    successful_reviews: int
    reviews_by_ai: Dict[str, str]  # AI名称 -> 审查内容

    def __str__(self):
        return f"审查完成: {self.successful_reviews}/{self.total_reviews} 成功"


class ReviewAggregator:
    """聚合多个 AI 的审查结果"""

    def aggregate(self, reviews: List[AIResponse]) -> ReviewSummary:
        """
        聚合审查结果

        Args:
            reviews: 审查响应列表

        Returns:
            ReviewSummary 对象
        """
        reviews_by_ai = {}

        for review in reviews:
            if review.success:
                reviews_by_ai[review.ai_name] = review.output

        return ReviewSummary(
            total_reviews=len(reviews),
            successful_reviews=len(reviews_by_ai),
            reviews_by_ai=reviews_by_ai
        )

    def find_common_themes(self, reviews: List[AIResponse]) -> List[str]:
        """
        查找共识主题（简化版，未来可以用 NLP 改进）

        Args:
            reviews: 审查列表

        Returns:
            共同提到的关键词列表
        """
        # 简化实现：提取常见关键词
        keywords = ['bug', '错误', 'error', 'issue', '问题',
                   'security', '安全', 'performance', '性能',
                   'optimize', '优化', 'improve', '改进']

        common_themes = []
        for keyword in keywords:
            count = sum(1 for r in reviews if keyword.lower() in r.output.lower())
            if count >= 2:  # 至少两个 AI 提到
                common_themes.append(f"{keyword} (提到 {count} 次)")

        return common_themes
