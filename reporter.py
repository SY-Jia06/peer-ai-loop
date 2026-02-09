"""报告生成器"""
from datetime import datetime
from typing import Dict
from ai_clients import AIResponse
from aggregator import ReviewSummary


class MarkdownReporter:
    """生成 Markdown 格式的审查报告"""

    def generate(
        self,
        prompt: str,
        implementation: AIResponse,
        reviews: ReviewSummary,
        common_themes: list,
        improvements: dict = None,
        final_code: str = None
    ) -> str:
        """
        生成完整的 Markdown 报告

        Args:
            prompt: 原始任务提示
            implementation: 实现结果
            reviews: 审查摘要
            common_themes: 共识主题

        Returns:
            Markdown 格式的报告
        """
        report_parts = []

        # 标题和元数据
        report_parts.append("# Multi-AI Code Review Report\n")
        report_parts.append(f"**任务**: {prompt}\n")
        report_parts.append(f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_parts.append(f"**实现者**: {implementation.ai_name}\n")
        report_parts.append(f"**审查者**: {', '.join(reviews.reviews_by_ai.keys())}\n")
        report_parts.append(f"**执行时间**: {implementation.execution_time:.2f}秒\n")
        report_parts.append("\n---\n\n")

        # 生成的代码
        report_parts.append("## 生成的代码\n\n")
        report_parts.append(f"```\n{implementation.output}\n```\n\n")

        # 共识主题（如果有）
        if common_themes:
            report_parts.append("## 共识主题\n\n")
            report_parts.append("多个审查者都提到的关键点：\n")
            for theme in common_themes:
                report_parts.append(f"- {theme}\n")
            report_parts.append("\n")

        # 各 AI 的审查意见
        report_parts.append("## 审查意见\n\n")

        for ai_name, review_content in reviews.reviews_by_ai.items():
            report_parts.append(f"### {ai_name.capitalize()} 的审查\n\n")
            report_parts.append(f"{review_content}\n\n")
            report_parts.append("---\n\n")

        # 改进过程日志（如果有）
        if improvements:
            report_parts.append("## 改进过程\n\n")
            report_parts.append("审查者直接编辑文件进行了改进：\n\n")

            for ai_name, log in improvements.items():
                report_parts.append(f"### {ai_name.capitalize()} 的改进日志\n\n")
                report_parts.append(f"{log}\n\n")
                report_parts.append("---\n\n")

        # 最终改进后的代码
        if final_code:
            report_parts.append("## 最终改进后的代码\n\n")
            report_parts.append(f"```python\n{final_code}\n```\n\n")

        # 统计信息
        report_parts.append("## 统计信息\n\n")
        report_parts.append(f"- 成功审查数: {reviews.successful_reviews}/{reviews.total_reviews}\n")
        report_parts.append(f"- 总执行时间: {implementation.execution_time:.2f}秒\n")
        if improvements:
            report_parts.append(f"- 改进版本数: {len(improvements)}\n")

        report_parts.append(f"\n---\n*由 ai-review 生成*\n")

        return "".join(report_parts)

    def save(self, report: str, output_path: str):
        """保存报告到文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
