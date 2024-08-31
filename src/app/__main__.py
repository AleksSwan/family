import granian
from granian.constants import Interfaces, Loops
from granian.log import LogLevels

from app.settings import Settings


settings: Settings = Settings()
log_level_enum: LogLevels = LogLevels[settings.log_level.lower()]


if __name__ == "__main__":
    granian.Granian(
        target="app.application:application",
        address="0.0.0.0",  # noqa: S104
        port=settings.app_port,
        interface=Interfaces.ASGI,
        log_dictconfig={"root": {"level": "INFO"}} if settings.debug else {},
        log_level=log_level_enum,
        loop=Loops.uvloop,
        log_access=True,
        log_access_format='[%(time)s] %(dt_ms).0f ms "%(method)s %(path)s %(protocol)s" %(status)d',
    ).serve()
