import os

APPLICATION_NAME = "The Foreman"
COMPANY_NAME = "HardHead Works"
APPLICATION_VERSION = "0.8.0"

DATABASE_URL = os.getenv(
    "FOREMAN_DATABASE_URL",
    "sqlite:////data/foreman.db",
)
