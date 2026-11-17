"""ASGI entry point: `uvicorn app.asgi:app` or `gunicorn -k uvicorn.workers.UvicornWorker app.asgi:app`."""

from app.main import create_app

app = create_app()
