from typing import Any, Callable, Optional, ParamSpec

from ....utils.sync import run_sync

P = ParamSpec("P")

class NCMResponseError(Exception):
    def __init__(self, name: str, data: dict[str, Any]):
        self.name = name
        self.data = data

    @property
    def code(self) -> Optional[int]:
        return self.data.get("code")

    @property
    def message(self) -> Optional[str]:
        return self.data.get("message")

    def __str__(self):
        return f"{self.name} failed: [{self.code}] {self.message}"

async def ncm_request(
    api: Callable[P, Any],
    *args: P.args,
    **kwargs: P.kwargs,
) -> dict[str, Any]:
    ret = await run_sync(api)(*args, **kwargs)
    if ret.get("code", 200) != 200:
        raise NCMResponseError(api.__name__, ret)
    return ret