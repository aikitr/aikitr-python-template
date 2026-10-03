from workers import asgi

from app.worker_app import create_worker_app

Default = asgi.entrypoint(create_worker_app())
