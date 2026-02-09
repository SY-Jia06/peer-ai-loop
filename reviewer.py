"""并行审查执行器"""
import asyncio
from typing import List
from ai_clients import BaseAIClient, AIResponse


class ParallelReviewer:
    """并行执行多个 AI 审查"""

    def __init__(self, timeout_seconds: int = 300):
        self.timeout_seconds = timeout_seconds

    async def review_code(
        self,
        implementation: AIResponse,
        reviewers: List[BaseAIClient],
        original_prompt: str,
        context: str
    ) -> List[AIResponse]:
        """
        并行执行所有审查

        Args:
            implementation: 实现阶段的输出
            reviewers: 审查者客户端列表
            original_prompt: 原始需求
            context: 上下文信息

        Returns:
            成功的审查结果列表
        """
        # 创建所有审查任务
        tasks = [
            reviewer.review(
                code=implementation.output,
                original_prompt=original_prompt,
                context=context
            )
            for reviewer in reviewers
        ]

        try:
            # 并行执行，设置超时
            reviews = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.timeout_seconds
            )

            # 过滤成功的审查
            successful_reviews = []
            for review in reviews:
                if isinstance(review, AIResponse):
                    if review.success:
                        successful_reviews.append(review)
                    else:
                        # 记录失败但继续
                        print(f"⚠️  {review.ai_name} 审查失败: {review.errors}")
                elif isinstance(review, Exception):
                    print(f"⚠️  审查出错: {review}")

            return successful_reviews

        except asyncio.TimeoutError:
            print(f"❌ 审查超时（{self.timeout_seconds}秒）")
            return []
