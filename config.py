"""
Configuration loaded from environment variables (.env file).
Never hardcode secrets/passwords directly in source code.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file into environment variables


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "fittrack_db")

    # Daily targets used for dashboard/insights (simple defaults,
    # could later be made per-user/editable in profile)
    DEFAULT_CALORIE_TARGET = 2200
    DEFAULT_STEP_GOAL = 10000
