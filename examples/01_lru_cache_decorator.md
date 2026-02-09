# Multi-AI Code Review Report
**任务**: 实现一个带LRU缓存和过期时间的装饰器，支持异步函数，要考虑线程安全
**时间**: 2026-02-09 23:24:46
**实现者**: gemini
**审查者**: 
**执行时间**: 50.75秒

---

## 生成的代码

```
MCP server 'notion' requires authentication using: /mcp auth notion这是一个满足你所有要求的 Python 装饰器实现：

1.  **LRU 策略**：使用 `collections.OrderedDict` 实现。
2.  **TTL 过期**：在缓存值中存储时间戳，并在访问时检查。
3.  **异步支持**：自动检测函数是否为协程（async），并分别处理。
4.  **线程安全**：使用 `threading.Lock` 保护对缓存字典的读写操作。

```python
import time
import functools
import threading
import asyncio
from collections import OrderedDict
from typing import Any, Callable, Tuple

def lru_cache_ttl(maxsize: int = 128, ttl: int = 60):
    """
    一个支持 LRU 淘汰策略、TTL 过期时间、线程安全且兼容异步函数的装饰器。
    
    :param maxsize: 缓存的最大条目数。
    :param ttl: 缓存条目的存活时间（秒）。
    """
    def decorator(func: Callable) -> Callable:
        # 使用 OrderedDict 实现 LRU，最新使用的在右端，最旧的在左端
        cache: OrderedDict = OrderedDict()
        # 线程锁，保证多线程环境下对 cache 操作的原子性
        lock = threading.Lock()

        def _make_key(args: Tuple, kwargs: dict) -> Tuple:
            """生成缓存键，确保 kwargs 顺序一致性"""
            # 如果 kwargs 中的值是不可哈希的（如 list），这里会报错。
            # 生产环境通常需要更复杂的 key 生成逻辑，这里采用标准做法。
            key = (args, tuple(sorted(kwargs.items())))
            return key

        def _get_from_cache(key: Any) -> Tuple[Any, bool]:
            """尝试从缓存获取数据，处理 LRU 更新和 TTL 检查"""
            with lock:
                if key in cache:
                    result, timestamp = cache[key]
                    # 检查是否过期
                    if time.time() - timestamp < ttl:
                        # 命中且未过期，移动到末尾（标记为最近使用）
                        cache.move_to_end(key)
                        return result, True
                    else:
                        # 已过期，删除
                        del cache[key]
            return None, False

        def _set_to_cache(key: Any, value: Any):
            """写入缓存，并执行 LRU 淘汰"""
            with lock:
                # 写入新值和当前时间戳
                cache[key] = (value, time.time())
                # 移动到末尾
                cache.move_to_end(key)
                
                # 如果超过最大容量，弹出最久未使用的项（OrderedDict 的第一个项）
                if len(cache) > maxsize:
                    cache.popitem(last=False)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            """同步函数的包装器"""
            key = _make_key(args, kwargs)
            result, found = _get_from_cache(key)
            if found:
                return result
            
            # 未命中或已过期，执行原函数
            result = func(*args, **kwargs)
            _set_to_cache(key, result)
            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            """异步函数的包装器"""
            key = _make_key(args, kwargs)
            result, found = _get_from_cache(key)
            if found:
                return result
            
            # 未命中或已过期，await 执行原函数
            result = await func(*args, **kwargs)
            _set_to_cache(key, result)
            return result

        # 根据被装饰函数是否为协程，返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

# --- 使用示例 ---

if __name__ == "__main__":
    
    # 示例 1: 同步函数
    @lru_cache_ttl(maxsize=2, ttl=2)
    def heavy_computation(x):
        print(f"Sync computing {x}...")
        return x * x

    # 示例 2: 异步函数
    @lru_cache_ttl(maxsize=2, ttl=2)
    async def async_heavy_computation(x):
        print(f"Async computing {x}...")
        await asyncio.sleep(0.1)
        return x * x

    async def main():
        print("--- Testing Sync ---")
        print(heavy_computation(2)) # 计算
        print(heavy_computation(2)) # 缓存命中
        time.sleep(2.1)
        print(heavy_computation(2)) # TTL 过期，重新计算

        print("\n--- Testing Async ---")
        print(await async_heavy_computation(3)) # 计算
        print(await async_heavy_computation(3)) # 缓存命中
        
        print("\n--- Testing LRU ---")
        await async_heavy_computation(4) # 缓存: {3, 4}
        await async_heavy_computation(5) # 缓存: {4, 5} (3 被淘汰)
        print(await async_heavy_computation(3)) # 3 重新计算

    # 运行测试
    asyncio.run(main())
```

```

## 审查意见

## 统计信息

- 成功审查数: 0/0
- 总执行时间: 50.75秒

---
*由 ai-review 生成*
