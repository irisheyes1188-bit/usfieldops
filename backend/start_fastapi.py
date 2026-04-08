from __future__ import annotations

import uvicorn

from config import load_config


def main() -> None:
    config = load_config()
    uvicorn.run(
        "fastapi_app:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
    )


if __name__ == "__main__":
    main()
