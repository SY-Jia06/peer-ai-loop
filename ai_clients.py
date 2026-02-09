"""AI 客户端封装模块"""
import asyncio
import time
import tempfile
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path


@dataclass
class AIResponse:
    """AI 响应数据结构"""
    success: bool
    output: str
    errors: Optional[str]
    execution_time: float
    model: str
    ai_name: str


class BaseAIClient:
    """AI 客户端基类"""

    def __init__(self, config: dict, name: str):
        self.config = config
        self.name = name

    async def _run_subprocess(self, cmd: List[str], input_text: Optional[str] = None) -> tuple:
        """运行子进程"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if input_text else None
        )

        stdout, stderr = await process.communicate(
            input=input_text.encode() if input_text else None
        )

        return process.returncode, stdout.decode(), stderr.decode()

    async def implement(self, prompt: str, context_files: List[str]) -> AIResponse:
        """实现代码（由子类实现）"""
        raise NotImplementedError

    async def review(self, code: str, original_prompt: str, context: str) -> AIResponse:
        """审查代码（由子类实现）"""
        raise NotImplementedError

    def _build_context(self, context_files: List[str]) -> str:
        """构建上下文信息"""
        if not context_files:
            return ""

        context_parts = ["相关上下文文件：\n"]
        for file_path in context_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    context_parts.append(f"\n--- {file_path} ---\n{content}\n")
            except Exception as e:
                context_parts.append(f"\n--- {file_path} (读取失败: {e}) ---\n")

        return "\n".join(context_parts)


class GeminiClient(BaseAIClient):
    """Gemini AI 客户端"""

    async def implement(self, prompt: str, context_files: List[str]) -> AIResponse:
        """使用 Gemini 实现代码"""
        context = self._build_context(context_files)
        full_prompt = f"""{context}

请实现以下需求：
{prompt}

请直接输出代码实现，包含必要的注释。"""

        cmd = [
            self.config['command'],
            '--model', self.config['model'],  # 添加模型参数
            self.config['prompt_flag'],
            full_prompt
        ]

        # 添加跳过权限参数（如果配置了）
        if 'skip_permissions' in self.config:
            cmd.insert(1, self.config['skip_permissions'])

        start = time.time()
        returncode, stdout, stderr = await self._run_subprocess(cmd)

        return AIResponse(
            success=returncode == 0,
            output=stdout,
            errors=stderr if returncode != 0 else None,
            execution_time=time.time() - start,
            model=self.config.get('model', 'gemini'),
            ai_name=self.name
        )

    async def review(self, code: str, original_prompt: str, context: str) -> AIResponse:
        """使用 Gemini 审查代码"""
        review_prompt = f"""{context}

原始需求：{original_prompt}

生成的代码：
```
{code}
```

请作为代码审查专家，审查以上代码并提供：
1. 代码质量评估
2. 潜在的 bug 或问题
3. 安全性考虑
4. 性能优化建议
5. 改进建议（如有）

请用清晰的结构化格式输出审查意见。"""

        cmd = [
            self.config['command'],
            '--model', self.config['model'],  # 添加模型参数
            self.config['prompt_flag'],
            review_prompt
        ]

        # 添加跳过权限参数（如果配置了）
        if 'skip_permissions' in self.config:
            cmd.insert(1, self.config['skip_permissions'])

        start = time.time()
        returncode, stdout, stderr = await self._run_subprocess(cmd)

        return AIResponse(
            success=returncode == 0,
            output=stdout,
            errors=stderr if returncode != 0 else None,
            execution_time=time.time() - start,
            model=self.config.get('model', 'gemini'),
            ai_name=self.name
        )


    async def improve_file(self, file_path: str, review_output: str, original_prompt: str) -> AIResponse:
        """让 Gemini 直接编辑文件进行改进"""
        improve_prompt = f"""你之前审查了这段代码，现在请根据你的审查建议直接改进它。

原始需求：{original_prompt}

你的审查意见：
{review_output}

请直接编辑文件 {file_path}，根据你的建议改进代码。不要只是给建议，要实际修改文件。"""

        cmd = [
            self.config['command'],
            '--model', self.config['model'],
            self.config['prompt_flag'],
            improve_prompt
        ]

        # 添加跳过权限参数
        if 'skip_permissions' in self.config:
            cmd.insert(1, self.config['skip_permissions'])

        start = time.time()
        returncode, stdout, stderr = await self._run_subprocess(cmd)

        return AIResponse(
            success=returncode == 0,
            output=stdout,
            errors=stderr if returncode != 0 else None,
            execution_time=time.time() - start,
            model=self.config.get('model', 'gemini'),
            ai_name=self.name
        )


class ClaudeClient(BaseAIClient):
    """Claude AI 客户端"""

    async def implement(self, prompt: str, context_files: List[str]) -> AIResponse:
        """使用 Claude 实现代码"""
        context = self._build_context(context_files)

        # 创建临时任务文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            task_content = f"""{context}

## 任务
{prompt}

请实现以上需求，直接输出代码。"""
            f.write(task_content)
            task_file = f.name

        try:
            # 使用 claude 命令的非交互模式
            cmd = [self.config['command'], '-p', f'读取 {task_file} 并实现其中描述的功能']

            # 添加跳过权限参数
            if 'skip_permissions' in self.config:
                cmd.insert(1, self.config['skip_permissions'])

            start = time.time()
            returncode, stdout, stderr = await self._run_subprocess(cmd)

            return AIResponse(
                success=returncode == 0,
                output=stdout,
                errors=stderr if returncode != 0 else None,
                execution_time=time.time() - start,
                model='claude',
                ai_name=self.name
            )
        finally:
            # 清理临时文件
            Path(task_file).unlink(missing_ok=True)

    async def review(self, code: str, original_prompt: str, context: str) -> AIResponse:
        """使用 Claude 审查代码"""
        review_prompt = f"""{context}

原始需求：{original_prompt}

生成的代码：
```
{code}
```

作为专业的代码审查者，请审查以上代码：
1. 正确性：代码是否正确实现了需求？
2. 代码质量：是否遵循最佳实践？
3. 潜在问题：是否有 bug、安全漏洞或性能问题？
4. 改进建议：如何优化这段代码？

请提供详细的审查报告。"""

        cmd = [self.config['command'], '-p', review_prompt]

        # 添加跳过权限参数
        if 'skip_permissions' in self.config:
            cmd.insert(1, self.config['skip_permissions'])

        start = time.time()
        returncode, stdout, stderr = await self._run_subprocess(cmd)

        return AIResponse(
            success=returncode == 0,
            output=stdout,
            errors=stderr if returncode != 0 else None,
            execution_time=time.time() - start,
            model='claude',
            ai_name=self.name
        )


    async def improve_file(self, file_path: str, review_output: str, original_prompt: str) -> AIResponse:
        """让 Claude 直接编辑文件进行改进"""
        improve_prompt = f"""你之前审查了这段代码，现在请根据你的审查建议直接改进它。

原始需求：{original_prompt}

你的审查意见：
{review_output}

请直接编辑文件 {file_path}，根据你的建议改进代码。不要只是给建议，要实际修改文件。"""

        cmd = [self.config['command'], '-p', improve_prompt]

        # 添加跳过权限参数
        if 'skip_permissions' in self.config:
            cmd.insert(1, self.config['skip_permissions'])

        start = time.time()
        returncode, stdout, stderr = await self._run_subprocess(cmd)

        return AIResponse(
            success=returncode == 0,
            output=stdout,
            errors=stderr if returncode != 0 else None,
            execution_time=time.time() - start,
            model='claude',
            ai_name=self.name
        )


class CodexClient(BaseAIClient):
    """Codex AI 客户端（预留接口）"""

    async def implement(self, prompt: str, context_files: List[str]) -> AIResponse:
        """使用 Codex 实现代码"""
        # 预留给未来 Codex API key 修复后使用
        return AIResponse(
            success=False,
            output="",
            errors="Codex is currently disabled (API key issue)",
            execution_time=0,
            model='codex',
            ai_name=self.name
        )

    async def review(self, code: str, original_prompt: str, context: str) -> AIResponse:
        """使用 Codex 审查代码"""
        return AIResponse(
            success=False,
            output="",
            errors="Codex is currently disabled (API key issue)",
            execution_time=0,
            model='codex',
            ai_name=self.name
        )


def create_client(ai_name: str, config: dict) -> BaseAIClient:
    """工厂函数：创建 AI 客户端"""
    clients = {
        'gemini': GeminiClient,
        'claude': ClaudeClient,
        'codex': CodexClient
    }

    client_class = clients.get(ai_name.lower())
    if not client_class:
        raise ValueError(f"Unknown AI: {ai_name}")

    return client_class(config, ai_name)
