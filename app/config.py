from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "cv_recommender"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    API_KEY: str = "dev-local-key"
    S3_BUCKET: str = "cv-recommender-uploads-dev"
    AWS_REGION: str = "eu-west-1"


settings = Settings()
