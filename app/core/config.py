from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SeedFarm"

    oracle_user: str
    oracle_password: str
    oracle_dsn: str

    mongo_uri: str
    mongo_db: str


    telegram_bot_token: str
    telegram_chat_id: str
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()