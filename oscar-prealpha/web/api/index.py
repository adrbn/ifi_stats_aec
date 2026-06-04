"""Point d'entrée serverless Vercel : expose l'app FastAPI depuis server/."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server"))

from main import app  # noqa: E402,F401  (Vercel détecte `app` comme handler ASGI)
