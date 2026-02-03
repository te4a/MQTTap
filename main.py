import asyncio
import logging.config
import sys

import uvicorn

from mqttap.logging_config import get_logging_config

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


if __name__ == "__main__":
    logging.config.dictConfig(get_logging_config())
    uvicorn.run(
        "mqttap.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_config=get_logging_config(),
    )
