from clients.vts_client import VTSPlugin
from configs.config import config

plugin: VTSPlugin  = VTSPlugin(
    plugin_name=config.PLUGIN.PLUGIN_NAME,
    plugin_developer=config.PLUGIN.PLUGIN_DEVELOPER,
    endpoint=config.PLUGIN.VTS_ENDPOINT,
)
