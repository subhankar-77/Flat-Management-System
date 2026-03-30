from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    # Format: postgresql://USER:PASSWORD@HOST:PORT/DB_NAME
    # Example: postgresql://postgres:secret@localhost:5432/society_db
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/society_db"

    # ── JWT Auth ──────────────────────────────────────────────────────────────
    # Generate a strong random secret: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY_BEFORE_DEPLOYING"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── Admin credentials (initial seed) ─────────────────────────────────────
    ADMIN_EMAIL: str = "admin@sunriseheights.com"
    ADMIN_PASSWORD: str = "Admin@123"   # Change after first login!
    ADMIN_NAME: str = "Society Admin"

    # ── Razorpay ──────────────────────────────────────────────────────────────
    # Get these from https://dashboard.razorpay.com → Settings → API Keys
    RAZORPAY_KEY_ID: str = "rzp_test_XXXXXXXXXXXXXXXX"
    RAZORPAY_KEY_SECRET: str = "XXXXXXXXXXXXXXXXXXXXXXXX"

    # ── Society Info ──────────────────────────────────────────────────────────
    SOCIETY_NAME: str = "Sunrise Heights Society"
    SOCIETY_TOTAL_FLATS: int = 9
    DEFAULT_MAINTENANCE_CHARGE: int = 3000  # in INR

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
