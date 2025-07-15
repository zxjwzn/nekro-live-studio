from functools import partial, wraps
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar

import anyio
import anyio.to_thread

P = ParamSpec("P")
R = TypeVar("R")

def run_sync(call: Callable[P, R]) -> Callable[P, Coroutine[None, None, R]]:
    """一个用于包装 sync function 为 async function 的装饰器
    参数:
        call: 被装饰的同步函数
    """

    @wraps(call)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await anyio.to_thread.run_sync(partial(call, *args, **kwargs), abandon_on_cancel=True)

    return _wrapper