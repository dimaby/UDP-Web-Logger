from __future__ import annotations

import uvicorn

from .config import get_config


def main() -> None:
    config = get_config()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.web_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
