# Multi-AI Code Review Report
**任务**: 实现一个支持优先级队列、延迟执行、任务重试的异步任务调度器
**时间**: 2026-02-09 23:36:37
**实现者**: gemini
**审查者**: claude
**执行时间**: 131.93秒

---

## 生成的代码

```
MCP server 'notion' requires authentication using: /mcp auth notion这是一份基于 Python `asyncio` 实现的异步任务调度器。

它采用了 **“时间等待交由事件循环 (`loop.call_later`) + 就绪任务交由优先级队列 (`asyncio.PriorityQueue`)”** 的高效模式。

### 核心特性：
1.  **优先级队列**：支持任务优先级（数值越小优先级越高）。
2.  **延迟执行**：支持指定延迟时间后执行。
3.  **任务重试**：任务失败后自动重试，支持最大重试次数和重试间隔。
4.  **并发执行**：支持配置并发 Worker 数量。

### 代码实现

```python
import asyncio
import time
import logging
import uuid
from dataclasses import dataclass, field
from typing import Callable, Any, Tuple, Dict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Scheduler")

@dataclass(order=True)
class Task:
    """
    任务数据结构。
    使用 @dataclass(order=True) 生成比较方法，默认按字段顺序比较。
    因此 priority 为第一排序键 (数值越小优先级越高)。
    """
    priority: int
    create_time: float
    
    # 以下字段不参与比较 (compare=False)
    id: str = field(compare=False)
    coro_func: Callable = field(compare=False)  # 异步任务函数
    args: Tuple = field(compare=False, default_factory=tuple)
    kwargs: Dict = field(compare=False, default_factory=dict)
    
    # 重试配置
    max_retries: int = field(compare=False, default=3)
    current_retries: int = field(compare=False, default=0)
    retry_delay: float = field(compare=False, default=1.0)

class AsyncScheduler:
    def __init__(self, worker_count: int = 3):
        self.queue = asyncio.PriorityQueue()
        self.worker_count = worker_count
        self.workers = []
        self.running = False

    async def submit(self, 
                     coro_func: Callable, 
                     *args, 
                     priority: int = 10, 
                     delay: float = 0, 
                     max_retries: int = 3, 
                     retry_delay: float = 1.0, 
                     **kwargs):
        """
        提交任务到调度器。
        
        :param coro_func: 异步协程函数
        :param priority: 优先级 (越小越高)
        :param delay: 延迟执行秒数
        :param max_retries: 最大重试次数
        :param retry_delay: 重试前的等待秒数
        """
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            priority=priority,
            create_time=time.time(),
            id=task_id,
            coro_func=coro_func,
            args=args,
            kwargs=kwargs,
            max_retries=max_retries,
            retry_delay=retry_delay
        )

        if delay > 0:
            logger.info(f"Task {task_id} scheduled in {delay}s (Priority: {priority})")
            # 使用 asyncio 的 call_later 处理延迟，到期后直接推入队列
            asyncio.get_running_loop().call_later(
                delay, 
                self.queue.put_nowait, 
                task
            )
        else:
            logger.info(f"Task {task_id} submitted (Priority: {priority})")
            self.queue.put_nowait(task)

    async def start(self):
        """启动调度器和 Worker"""
        self.running = True
        logger.info(f"Starting scheduler with {self.worker_count} workers...")
        self.workers = [asyncio.create_task(self._worker(i)) for i in range(self.worker_count)]
        
        # 保持运行，直到被停止
        try:
            await asyncio.gather(*self.workers)
        except asyncio.CancelledError:
            logger.info("Scheduler stopped.")

    async def stop(self):
        """停止调度器"""
        self.running = False
        # 发送 None 作为停止信号
        for _ in range(self.worker_count):
            await self.queue.put(None)
        
        # 等待所有 Worker 结束
        await asyncio.gather(*self.workers, return_exceptions=True)

    async def _worker(self, worker_id: int):
        """消费者 Worker 循环"""
        logger.debug(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # 获取任务
                task = await self.queue.get()
                
                # 检查是否是停止信号
                if task is None:
                    self.queue.task_done()
                    break

                logger.info(f"[Worker {worker_id}] Processing Task {task.id} (Priority: {task.priority})")
                
                start_time = time.time()
                try:
                    # 执行任务
                    await task.coro_func(*task.args, **task.kwargs)
                    logger.info(f"[Worker {worker_id}] Task {task.id} output: Success ({time.time() - start_time:.2f}s)")
                
                except Exception as e:
                    logger.error(f"[Worker {worker_id}] Task {task.id} failed: {e}")
                    
                    # 重试逻辑
                    if task.current_retries < task.max_retries:
                        task.current_retries += 1
                        wait_time = task.retry_delay * task.current_retries # 简单的线性退避
                        
                        logger.warning(f"Task {task.id} retrying {task.current_retries}/{task.max_retries} in {wait_time}s...")
                        
                        # 重新调度（利用 call_later 实现重试延迟）
                        asyncio.get_running_loop().call_later(
                            wait_time,
                            self.queue.put_nowait,
                            task
                        )
                    else:
                        logger.error(f"Task {task.id} max retries reached. Dropped.")
                
                finally:
                    self.queue.task_done()

            except Exception as e:
                logger.critical(f"Worker {worker_id} crashed: {e}")

# ==========================================
# 示例使用代码
# ==========================================

async def sample_task(name: str, duration: float, should_fail: bool = False):
    """模拟一个异步任务"""
    await asyncio.sleep(duration)
    if should_fail:
        raise ValueError(f"Simulated error in {name}")
    print(f"--> {name} finished work.")

async def main():
    scheduler = AsyncScheduler(worker_count=2)

    # 创建调度器运行任务（后台运行）
    scheduler_task = asyncio.create_task(scheduler.start())

    # 1. 普通任务
    await scheduler.submit(sample_task, "Task A (Normal)", 1.0, priority=10)
    
    # 2. 高优先级任务 (Priority=0)
    await scheduler.submit(sample_task, "Task B (High Priority)", 0.5, priority=0)
    
    # 3. 延迟任务 (3秒后执行)
    await scheduler.submit(sample_task, "Task C (Delayed)", 1.0, priority=5, delay=3.0)
    
    # 4. 会失败并重试的任务
    await scheduler.submit(sample_task, "Task D (Flaky)", 0.5, priority=10, should_fail=True, max_retries=2)

    # 等待演示完成
    await asyncio.sleep(8)
    
    # 停止调度器
    await scheduler.stop()
    await scheduler_task

if __name__ == "__main__":
    asyncio.run(main())
```

```

## 审查意见

### Claude 的审查

# 代码审查报告

## 1. 正确性分析

### ✅ 已实现的需求
- **优先级队列**：通过 `@dataclass(order=True)` + `PriorityQueue` 实现
- **延迟执行**：使用 `loop.call_later()` 
- **任务重试**：包含重试计数和延迟机制

### ⚠️ 实现缺陷

**严重问题：任务优先级在重试时会改变**
```python
# Task 的排序基于 (priority, create_time)
# 重试时 create_time 不变，但任务会重新入队
# 这导致重试任务的"新鲜度"错位
```

**问题场景**：
```python
# t=0: Task A (priority=5, create_time=0) 入队
# t=1: Task A 失败，重试后重新入队
# t=2: Task B (priority=5, create_time=2) 入队
# 结果：Task A 会因为 create_time 更早而优先执行
# 但逻辑上，新提交的 Task B 应该和重试的 Task A 平等竞争
```

---

## 2. 代码质量问题

### 🔴 严重问题

#### A. 资源泄漏风险
```python
async def submit(self, ...):
    asyncio.get_running_loop().call_later(...)
```

**问题**：
- `call_later` 返回的 `TimerHandle` 未保存
- 无法取消已调度的延迟任务
- 调度器停止时，延迟任务仍会执行

**影响场景**：
```python
await scheduler.submit(task, delay=3600)  # 1小时后执行
await scheduler.stop()  # 立即停止
# ⚠️ 1小时后任务仍会尝试入队（此时队列可能已销毁）
```

#### B. 竞态条件
```python
async def stop(self):
    self.running = False  # ← 未加锁
    for _ in range(self.worker_count):
        await self.queue.put(None)
```

**问题**：
- `self.running` 的读写未同步
- `submit()` 可能在 `stop()` 期间继续添加任务

**异常场景**：
```python
# Thread A: await scheduler.stop()  设置 running=False
# Thread B: await scheduler.submit(...)  检查到 running=True (旧值)
# 结果：新任务入队但无 worker 处理
```

### 🟡 设计问题

#### C. 停止信号设计不当
```python
if task is None:
    self.queue.task_done()  # ← 对控制信号调用 task_done
    break
```

**问题**：
- `None` 作为停止信号混入业务队列
- 违反 `task_done()` 语义（用于业务任务完成标记）

#### D. 日志级别混乱
```python
logger.debug(f"Worker {worker_id} started")  # 关键信息用 DEBUG
logger.info(f"Task {task_id} submitted...")   # 噪音信息用 INFO
```

---

## 3. 潜在问题

### 🐛 Bug 清单

| 问题 | 严重性 | 场景 |
|------|--------|------|
| 延迟任务无法取消 | 高 | 长延迟任务 + 提前停止 |
| 重试任务优先级错乱 | 中 | 同优先级任务混合重试场景 |
| `task_done()` 语义滥用 | 低 | 队列监控场景 |
| 缺少任务结果收集机制 | 中 | 需要获取任务执行结果 |

### 🔒 安全问题

1. **任务函数未验证**
   ```python
   await task.coro_func(*task.args, **task.kwargs)
   # 如果 coro_func 不是协程函数会直接崩溃
   ```

2. **无资源限制**
   ```python
   self.queue = asyncio.PriorityQueue()  # 无界队列
   # 可能导致内存溢出
   ```

### ⚡ 性能问题

1. **线性退避策略过于简单**
   ```python
   wait_time = task.retry_delay * task.current_retries
   # 大量重试会导致队列积压
   ```

2. **日志过多影响性能**
   ```python
   logger.info(f"Task {task_id} submitted...")  # 每个任务都打印
   ```

---

## 4. 改进建议

### 🎯 关键修复

#### 修复 1: 管理延迟任务句柄
```python
class AsyncScheduler:
    def __init__(self, ...):
        self._timer_handles: set = set()  # 新增
    
    async def submit(self, ...):
        if delay > 0:
            handle = asyncio.get_running_loop().call_later(
                delay, self._enqueue_task, task
            )
            self._timer_handles.add(handle)
    
    def _enqueue_task(self, task):
        """包装入队逻辑，用于清理句柄"""
        self.queue.put_nowait(task)
        # 从集合中移除（如果还在）
    
    async def stop(self):
        # 取消所有待执行的延迟任务
        for handle in self._timer_handles:
            handle.cancel()
        self._timer_handles.clear()
        # ... 原有停止逻辑
```

#### 修复 2: 使用专用停止事件
```python
class AsyncScheduler:
    def __init__(self, ...):
        self._stop_event = asyncio.Event()
    
    async def _worker(self, worker_id):
        while not self._stop_event.is_set():
            try:
                task = await asyncio.wait_for(
                    self.queue.get(), 
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue  # 检查停止事件
            
            # 处理任务...
    
    async def stop(self):
        self._stop_event.set()  # 通知 worker
        # 等待队列清空或超时
        await asyncio.wait_for(self.queue.join(), timeout=5.0)
```

#### 修复 3: 修正任务排序逻辑
```python
@dataclass(order=True)
class Task:
    priority: int
    enqueue_time: float = field(default_factory=time.time)  # 改为入队时间
    
    # 在 submit() 和重试时都更新 enqueue_time
```

### 🚀 架构优化

#### 建议 1: 分离关注点
```python
class TaskExecutor:
    """负责任务执行和重试"""
    async def execute(self, task: Task) -> TaskResult:
        ...

class DelayedTaskManager:
    """负责延迟任务调度"""
    def schedule(self, task: Task, delay: float):
        ...

class AsyncScheduler:
    """负责整体协调"""
    def __init__(self):
        self.executor = TaskExecutor()
        self.delay_manager = DelayedTaskManager()
```

#### 建议 2: 添加可观测性
```python
@dataclass
class SchedulerMetrics:
    tasks_submitted: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_wait_time: float = 0.0
    
class AsyncScheduler:
    def get_metrics(self) -> SchedulerMetrics:
        ...
```

#### 建议 3: 支持任务取消
```python
class TaskHandle:
    """任务句柄，支持取消和查询状态"""
    def cancel(self) -> bool:
        ...
    
    async def result(self) -> Any:
        ...

async def submit(self, ...) -> TaskHandle:
    ...
```

---

## 5. 优化后的核心代码片段

```python
from enum import Enum
import asyncio
from typing import Optional

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass(order=True)
class Task:
    priority: int
    enqueue_time: float = field(default_factory=time.time)
    
    id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4())[:8])
    coro_func: Callable = field(compare=False)
    args: Tuple = field(compare=False, default_factory=tuple)
    kwargs: Dict = field(compare=False, default_factory=dict)
    
    max_retries: int = field(compare=False, default=3)
    current_retries: int = field(compare=False, default=0)
    retry_delay: float = field(compare=False, default=1.0)
    
    status: TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    result_future: asyncio.Future = field(compare=False, default_factory=asyncio.Future)

class AsyncScheduler:
    def __init__(self, worker_count: int = 3, max_queue_size: int = 1000):
        self.queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.worker_count = worker_count
        
        self._stop_event = asyncio.Event()
        self._timer_handles: set = set()
        self._tasks: Dict[str, Task] = {}  # 任务注册表
        
    async def submit(self, coro_func, *args, priority=10, delay=0, **kwargs) -> str:
        """返回 task_id 用于后续查询/取消"""
        # 验证是否为协程函数
        if not asyncio.iscoroutinefunction(coro_func):
            raise TypeError(f"{coro_func} is not a coroutine function")
        
        task = Task(
            priority=priority,
            coro_func=coro_func,
            args=args,
            kwargs=kwargs,
        )
        
        self._tasks[task.id] = task
        
        if delay > 0:
            handle = asyncio.get_running_loop().call_later(
                delay,
                self._safe_enqueue,
                task
            )
            self._timer_handles.add(handle)
        else:
            await self.queue.put(task)
        
        return task.id
    
    def _safe_enqueue(self, task: Task):
        """安全入队（处理调度器已停止的情况）"""
        if not self._stop_event.is_set():
            self.queue.put_nowait(task)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            task.result_future.cancel()
            return True
        return False
    
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """获取任务执行结果"""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        return await asyncio.wait_for(task.result_future, timeout=timeout)
```

---

## 总结

### 当前代码评分：**6.5/10**

**优点：**
- ✅ 核心架构清晰（生产者-消费者模式）
- ✅ 使用了合适的数据结构（PriorityQueue + dataclass）
- ✅ 基本功能完整

**主要问题：**
- ❌ 资源管理不完善（延迟任务泄漏）
- ❌ 缺少任务生命周期管理（取消、结果获取）
- ❌ 停止机制不够健壮
- ❌ 缺少错误边界和输入验证

**建议优先级：**
1. **立即修复**：延迟任务句柄管理、协程函数验证
2. **短期改进**：任务取消机制、停止事件优化
3. **长期重构**：分离关注点、添加可观测性

---

你想深入讨论哪个具体问题？或者需要我提供完整的优化版本代码？


---

## 统计信息

- 成功审查数: 1/1
- 总执行时间: 131.93秒

---
*由 ai-review 生成*
