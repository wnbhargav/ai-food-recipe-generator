import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pantry.models import RecipeRequest, RecipeResponse
from pantry.provider import OllamaProvider
from pantry.service import RecipeService

logger = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"


def create_app(service=None):
    mode = os.getenv("RECIPE_MODE", "demo")
    if mode not in {"demo", "ollama"}:
        raise ValueError("RECIPE_MODE must be demo or ollama")

    @asynccontextmanager
    async def lifespan(app):
        async with httpx.AsyncClient(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            timeout=httpx.Timeout(120, connect=5),
        ) as client:
            provider = (
                OllamaProvider(
                    client,
                    os.getenv("CHAT_MODEL", "qwen2.5:3b"),
                    os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
                )
                if mode == "ollama"
                else None
            )
            app.state.service = service or RecipeService(provider)
            yield

    app = FastAPI(title="AI Food Recipe Generator", version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/health")
    async def health():
        return {"status": "ok", "mode": mode}

    @app.post("/api/recipes", response_model=RecipeResponse)
    async def recipes(payload: RecipeRequest, request: Request):
        try:
            return await request.app.state.service.recommend(payload)
        except httpx.TimeoutException:
            raise HTTPException(504, "The model took too long. Please try again.") from None
        except httpx.HTTPError:
            logger.warning("Model service unavailable")
            raise HTTPException(
                503, "Cannot reach the model. Check Ollama and installed models."
            ) from None
        except (ValueError, KeyError, TypeError):
            logger.warning("Model returned an invalid response")
            raise HTTPException(
                502, "The model returned an invalid recipe. Please try again."
            ) from None

    return app


app = create_app()
