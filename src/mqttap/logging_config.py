import os
from pathlib import Path


def get_logging_config() -> dict:
    level = os.getenv("MQTTAP_LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("MQTTAP_LOG_FILE", "logs/mqttap.log")
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
            ,
            "file": {
                "class": "logging.FileHandler",
                "formatter": "default",
                "filename": log_file,
                "encoding": "utf-8",
            }
        },
        "root": {
            "handlers": ["console", "file"],
            "level": level,
        },
        "loggers": {
            "uvicorn": {"level": level},
            "uvicorn.error": {"level": level},
            "uvicorn.access": {"level": level},
        },
    }
