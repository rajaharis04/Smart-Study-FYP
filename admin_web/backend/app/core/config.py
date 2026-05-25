from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://admin:admin123@localhost:5432/smartstudy_admin"
    SECRET_KEY: str = "supersecretkey_change_in_production_2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ADMIN_EMAIL: str = "admin@smartstudy.edu"
    ADMIN_PASSWORD: str = "Admin@123"

    # SMTP Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
