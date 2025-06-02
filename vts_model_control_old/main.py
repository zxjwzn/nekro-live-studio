import uvicorn
from api.server import app
from configs.config import load_config, save_config


def main():
    # 加载配置并启动 API 服务
    cfg = load_config()
    save_config(cfg)
    uvicorn.run(app, host=cfg.api.host, port=cfg.api.port)


if __name__ == "__main__":
    main()