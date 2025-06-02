from clients.vts_client import VTSPlugin
from configs.config import VTSModelControlConfig


class VTSManager:

    plugin: VTSPlugin

    def __init__(self, config: VTSModelControlConfig):
        self.plugin = VTSPlugin(
            config.plugin.PLUGIN_NAME,
            config.plugin.PLUGIN_DEVELOPER,
            endpoint=config.plugin.VTS_ENDPOINT,
        )
    
    def check_plugin_status(self) -> bool:
        if not self.plugin:  # noqa: SIM103
            return False
        return True
    
    async def connect(self) -> str:
        if not self.check_plugin_status():
            if await self.plugin.connect_and_authenticate():
                assert self.plugin.client.authentication_token is not None
                return self.plugin.client.authentication_token
            return ""
        return ""
    
    async def disconnect(self) -> bool:
        if not self.check_plugin_status():
            return False
        await self.plugin.disconnect()
        return True
    
