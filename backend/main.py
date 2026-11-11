"""Ponto de entrada: `uvicorn main:app --host 0.0.0.0 --port 8000` (dentro de backend/)."""
from app.api.routes import create_app

app = create_app()
