"""Point d'entrée serverless Vercel : expose l'app FastAPI (routes /api/*)."""
from main import app  # noqa: F401  (Vercel détecte `app` comme handler ASGI)
