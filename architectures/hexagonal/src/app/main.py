from fastapi import FastAPI

from app.bootstrap import create_app as build_app


def create_app(database_url: str | None = None) -> FastAPI:
    """Keep the documented Uvicorn factory path stable."""
    return build_app(database_url)
