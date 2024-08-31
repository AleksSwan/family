from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import URL


class Settings(BaseSettings):
    # Database settings
    db_driver: str = Field(default="postgresql")
    db_user: str = Field(default="myuser")
    db_password: str = Field(default="mypassword")
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="family")

    # Application settings
    app_port: int = Field(default=8000)
    debug: bool = Field(default=True)
    service_name: str = Field(default="FastAPI")
    log_level: str = Field(default="INFO")

    @property
    def db_dsn(self) -> URL:
        return URL.create(
            drivername=self.db_driver,
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
