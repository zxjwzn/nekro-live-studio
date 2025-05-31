from vts_client import VTSPlugin
from configs.config import config

plugin = VTSPlugin(
    plugin_name=config.plugin.plugin_name,
    plugin_developer=config.plugin.plugin_developer,
    endpoint=config.plugin.default_vts_endpoint,
)
