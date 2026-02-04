from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MQTTAP_")

    # Bootstrap configuration (can be overridden by DB settings later)
    database_dsn: str = "postgresql+asyncpg://mqttap:mqttap@postgres:5432/mqttap"
    admin_database_dsn: str | None = None
    mqtt_host: str = "mqtt"
    mqtt_port: int = 1883
    mqtt_topics: str = "sensor/#"
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    float_precision: int = 3
    jwt_secret: str = "change-me"
    jwt_issuer: str = "mqttap"
    jwt_exp_minutes: int = 60
    cors_origins: str = "localhost,127.0.0.1"
    admin_username: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    default_agg: str = "avg"
    default_interval: str = "minute"


settings = Settings()
