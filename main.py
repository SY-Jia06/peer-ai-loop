#!/usr/bin/env python3
"""Multi-AI Code Review System - 主程序"""
import asyncio
import sys
import toml
import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from ai_clients import create_client
from reviewer import ParallelReviewer
from aggregator import ReviewAggregator
from reporter import MarkdownReporter


console = Console()


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return toml.load(f)
    except Exception as e:
        console.print(f"[red]配置文件加载失败: {e}[/red]")
        sys.exit(1)


async def run_review_workflow(
    prompt: str,
    implementer_name: str,
    reviewer_names: list,
    context_files: list,
    output_path: str,
    config: dict,
    enable_iteration: bool = True
):
    """执行完整的审查工作流（包含迭代改进）"""

    # 初始化客户端
    try:
        implementer = create_client(implementer_name, config['ai'][implementer_name])
        reviewers = [
            create_client(name, config['ai'][name])
            for name in reviewer_names
        ]
    except Exception as e:
        console.print(f"[red]客户端初始化失败: {e}[/red]")
        return

    # 构建上下文
    context = ""
    if context_files:
        context = "\n".join([f"文件: {f}" for f in context_files])

    # Phase 1: 实现
    console.print(f"\n[bold cyan]阶段 1/4: {implementer_name.upper()} 正在实现代码...[/bold cyan]")

    with console.status(f"[bold green]实现中...") as status:
        implementation = await implementer.implement(prompt, list(context_files))

    if not implementation.success:
        console.print(f"[red]实现失败: {implementation.errors}[/red]")
        return

    console.print(f"[green]✓ 实现完成 ({implementation.execution_time:.2f}秒)[/green]")
    console.print(Panel(implementation.output[:500] + "..." if len(implementation.output) > 500 else implementation.output,
                       title="生成的代码（预览）", border_style="green"))

    # Phase 2: 并行审查
    console.print(f"\n[bold cyan]阶段 2/4: 并行审查中...[/bold cyan]")
    console.print(f"审查者: {', '.join([r.upper() for r in reviewer_names])}")

    parallel_reviewer = ParallelReviewer(timeout_seconds=config['execution']['timeout_seconds'])

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(
            f"[cyan]等待 {len(reviewers)} 个审查完成...",
            total=None
        )

        review_results = await parallel_reviewer.review_code(
            implementation=implementation,
            reviewers=reviewers,
            original_prompt=prompt,
            context=context
        )

        progress.update(task, completed=True)

    console.print(f"[green]✓ 审查完成 ({len(review_results)}/{len(reviewers)} 成功)[/green]")

    # Phase 3: 迭代改进（新增）- 审查者直接编辑文件
    improvement_logs = {}
    if enable_iteration and review_results:
        console.print(f"\n[bold cyan]阶段 3/4: 审查者直接编辑文件改进代码...[/bold cyan]")

        # 先将原始代码保存到临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(implementation.output)
            code_file = f.name

        console.print(f"[dim]代码已保存到: {code_file}[/dim]")

        for review in review_results:
            reviewer = next((r for r in reviewers if r.name == review.ai_name), None)
            if not reviewer or not hasattr(reviewer, 'improve_file'):
                continue

            console.print(f"[yellow]→ {review.ai_name.upper()} 正在直接编辑文件改进代码...[/yellow]")

            with console.status(f"[bold green]{review.ai_name} 改进中..."):
                improved = await reviewer.improve_file(
                    file_path=code_file,
                    review_output=review.output,
                    original_prompt=prompt
                )

            if improved.success:
                improvement_logs[review.ai_name] = improved.output
                console.print(f"[green]✓ {review.ai_name.upper()} 改进完成 ({improved.execution_time:.2f}秒)[/green]")
            else:
                console.print(f"[red]✗ {review.ai_name.upper()} 改进失败: {improved.errors}[/red]")

        # 读取最终改进后的文件
        try:
            with open(code_file, 'r', encoding='utf-8') as f:
                final_improved_code = f.read()
        except:
            final_improved_code = None

    # Phase 4: 聚合和报告
    console.print(f"\n[bold cyan]阶段 4/4: 生成报告...[/bold cyan]")

    aggregator = ReviewAggregator()
    summary = aggregator.aggregate(review_results)
    common_themes = aggregator.find_common_themes(review_results)

    reporter = MarkdownReporter()
    report = reporter.generate(
        prompt=prompt,
        implementation=implementation,
        reviews=summary,
        common_themes=common_themes,
        improvements=improvement_logs if enable_iteration else None,
        final_code=final_improved_code if enable_iteration and 'final_improved_code' in locals() else None
    )

    # 输出报告
    if output_path:
        reporter.save(report, output_path)
        console.print(f"[green]✓ 报告已保存到: {output_path}[/green]")
    else:
        console.print("\n" + "="*80 + "\n")
        console.print(report)

    console.print(f"\n[bold green]审查流程完成！[/bold green]")
    console.print(summary)
    if improvement_logs:
        console.print(f"[green]✓ {len(improvement_logs)} 个审查者完成了代码改进[/green]")


@click.command()
@click.argument('prompt')
@click.option(
    '--implementer', '-i',
    default='gemini',
    type=click.Choice(['claude', 'gemini', 'codex'], case_sensitive=False),
    help='选择实现代码的 AI（默认: gemini）'
)
@click.option(
    '--reviewers', '-r',
    default='claude',
    help='审查者，逗号分隔（默认: claude）'
)
@click.option(
    '--context-file', '-f',
    multiple=True,
    type=click.Path(exists=True),
    help='提供上下文文件（可多次使用）'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='输出报告路径（不指定则输出到控制台）'
)
@click.option(
    '--config', '-c',
    default='config.toml',
    type=click.Path(exists=True),
    help='配置文件路径'
)
@click.option(
    '--no-iteration',
    is_flag=True,
    help='禁用迭代改进（只审查不改进）'
)
def main(prompt, implementer, reviewers, context_file, output, config, no_iteration):
    """
    Multi-AI Code Review System

    让不同 AI 互相审查代码，发挥各自优势。

    示例：

    \b
    # 基础使用
    python main.py "写一个计算斐波那契数列的函数"

    \b
    # 指定实现者和审查者
    python main.py "实现快速排序" -i gemini -r claude

    \b
    # 带上下文文件
    python main.py "优化这个函数" -f example.py -o report.md
    """

    # 加载配置
    cfg = load_config(config)

    # 解析审查者列表
    reviewer_list = [r.strip() for r in reviewers.split(',')]

    # 验证启用状态
    if not cfg['ai'][implementer]['enabled']:
        console.print(f"[red]错误: {implementer} 未启用[/red]")
        sys.exit(1)

    for reviewer in reviewer_list:
        if not cfg['ai'][reviewer]['enabled']:
            console.print(f"[yellow]警告: {reviewer} 未启用，将跳过[/yellow]")
            reviewer_list.remove(reviewer)

    if not reviewer_list:
        console.print("[red]错误: 没有可用的审查者[/red]")
        sys.exit(1)

    # 显示欢迎信息
    console.print(Panel.fit(
        "[bold cyan]Multi-AI Code Review System[/bold cyan]\n"
        f"实现者: {implementer.upper()}\n"
        f"审查者: {', '.join([r.upper() for r in reviewer_list])}",
        border_style="cyan"
    ))

    # 运行异步工作流
    asyncio.run(run_review_workflow(
        prompt=prompt,
        implementer_name=implementer,
        reviewer_names=reviewer_list,
        context_files=context_file,
        output_path=output,
        config=cfg,
        enable_iteration=not no_iteration  # 默认启用迭代改进
    ))


if __name__ == '__main__':
    main()
