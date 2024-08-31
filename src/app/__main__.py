import granian
from granian.constants import Interfaces, Loops
from granian.log import LogLevels

from app.settings import Settings


settings: Settings = Settings()
log_level_enum: LogLevels = LogLevels[settings.log_level.lower()]

log_dictconfig = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": log_level_enum.name,
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": log_level_enum.name,
    },
}


if __name__ == "__main__":
    granian.Granian(
        target="app.application:application",
        address="0.0.0.0",  # noqa: S104
        port=settings.app_port,
        interface=Interfaces.ASGI,
        log_dictconfig=log_dictconfig if not settings.debug else {},
        log_level=log_level_enum,
        loop=Loops.uvloop,
    ).serve()
