"""Uvicorn factory: uvicorn apps.api.main:create_app_from_env --factory."""

from apps.api.app import create_app
from apps.api.config import Settings


def create_app_from_env():
    return create_app(Settings.from_env())
