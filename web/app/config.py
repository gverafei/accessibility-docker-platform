import os
from zoneinfo import ZoneInfo


class Config:
    # Esta no se usa por el momento, pero es buena práctica tenerla para futuras configuraciones cuando se implemente un sistema de autenticación de usuarios.
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "accessibility-docker-platform-secret"
    )

    EVALUATOR_URL = os.getenv(
        "EVALUATOR_URL",
        "http://evaluator:3000"
    )

    APP_TIMEZONE = ZoneInfo(
        os.getenv("APP_TIMEZONE", "America/Mexico_City")
    )

    DB_HOST = os.getenv("DB_HOST", "db")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME", "accessibility_experiments")
    DB_USER = os.getenv("DB_USER", "access_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "access_pass")