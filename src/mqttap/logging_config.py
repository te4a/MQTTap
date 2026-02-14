import os
from pathlib import Path


def get_logging_config() -> dict:
    level = os.getenv("MQTTAP_LOG_LEVEL", "INFO").upper()
    app_log_file = os.getenv("MQTTAP_LOG_FILE", "logs/mqttap.log")
    uvicorn_log_file = os.getenv("MQTTAP_UVICORN_LOG_FILE", "logs/uvicorn.log")
    Path(app_log_file).parent.mkdir(parents=True, exist_ok=True)
    Path(uvicorn_log_file).parent.mkdir(parents=True, exist_ok=True)
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
                "filename": app_log_file,
                "encoding": "utf-8",
            },
            "uvicorn_file": {
                "class": "logging.FileHandler",
                "formatter": "default",
                "filename": uvicorn_log_file,
                "encoding": "utf-8",
            }
        },
        "root": {
            "handlers": ["console", "file"],
            "level": level,
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["console", "uvicorn_file"],
                "level": level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console", "uvicorn_file"],
                "level": level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["uvicorn_file"],
                "level": level,
                "propagate": False,
            },
        },
    }
