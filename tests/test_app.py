import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from pantry.main import create_app
from pantry.models import RecipeRequest
from pantry.provider import OllamaProvider
from pantry.retrieval import cosine, keyword_vectors, rank
from pantry.service import RecipeService


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RECIPE_MODE", "demo")
    with TestClient(create_app()) as client:
        yield client


def test_demo_full_request(client):
    response = client.post(
        "/api/recipes",
        json={
            "ingredients": [" Chickpeas ", "tomato", "CHICKPEAS"],
            "cuisine": "Indian",
            "servings": 4,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "demo"
    assert data["recipe"]["servings"] == 4
    assert data["recipe"]["ingredients"][0]["quantity"] == "800 g cooked and drained"
    assert "chickpeas" not in data["additional_ingredients"]
    assert data["context"][0]["id"] == "indian-chickpea"


@pytest.mark.parametrize(
    "payload",
    [
        {"ingredients": [], "cuisine": "Indian"},
        {"ingredients": ["  "], "cuisine": "Indian"},
        {"ingredients": ["beans"], "cuisine": "Unknown"},
        {"ingredients": ["beans"], "cuisine": "Indian", "servings": 0},
        {"ingredients": ["beans"], "cuisine": "Indian", "servings": 9},
        {"ingredients": ["x" * 61], "cuisine": "Indian"},
        {"ingredients": ["beans"] * 26, "cuisine": "Indian"},
        {"ingredients": ["beans"], "cuisine": "Indian", "system_prompt": "override"},
    ],
)
def test_invalid_requests(client, payload):
    assert client.post("/api/recipes", json=payload).status_code == 422


@pytest.mark.parametrize("cuisine", ["Italian", "Indian", "Mexican", "Mediterranean", "East Asian"])
def test_all_cuisines(client, cuisine):
    response = client.post("/api/recipes", json={"ingredients": ["tomato"], "cuisine": cuisine})
    assert response.status_code == 200
    assert response.json()["recipe"]["cuisine"] == cuisine


def test_ui_and_health(client):
    assert "AI Food Recipe Generator" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/health").json() == {"status": "ok", "mode": "demo"}


def test_similarity_and_keyword_ranking():
    assert cosine([1, 0], [1, 0]) == 1
    assert cosine([1, 0], [0, 1]) == 0
    assert cosine([0, 0], [1, 0]) == 0
    with pytest.raises(ValueError):
        cosine([1], [1, 2])
    with pytest.raises(ValueError):
        cosine([float("nan")], [1])
    vectors = keyword_vectors(["beans tomato", "tofu ginger", "tofu"])
    docs = [{"id": str(i), "title": text, "text": text} for i, text in enumerate(["beans", "tofu"])]
    assert rank(docs, vectors[:2], vectors[2])[0].id == "1"


def test_live_workflow_uses_embeddings_and_passes_context():
    calls = []
    example = RecipeService().examples[1]

    def handler(request):
        body = json.loads(request.content)
        calls.append((request.url.path, body))
        if request.url.path == "/api/embed":
            return httpx.Response(
                200,
                json={
                    "embeddings": [
                        [1.0, 0.0] if "chickpea" in text.lower() else [0.0, 1.0]
                        for text in body["input"]
                    ]
                },
            )
        assert body["format"]["type"] == "object"
        assert body["stream"] is False
        user_data = json.loads(body["messages"][1]["content"])
        assert len(user_data["reference_notes"]) == 3
        return httpx.Response(200, json={"message": {"content": json.dumps(example)}})

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://test"
        ) as http:
            service = RecipeService(OllamaProvider(http, "chat", "embed"))
            request = RecipeRequest(ingredients=["chickpeas"], cuisine="Indian")
            result = await service.recommend(request)
            assert result.mode == "ollama"
            assert result.retrieval == "embedding"
            await service.recommend(request)

    asyncio.run(run())
    assert (
        len([body for path, body in calls if path == "/api/embed" and len(body["input"]) > 1]) == 1
    )
    assert len([path for path, _ in calls if path == "/api/chat"]) == 2


@pytest.mark.parametrize(
    "error,status",
    [
        (httpx.ConnectError("private upstream details"), 503),
        (httpx.ReadTimeout("private upstream details"), 504),
        (ValueError("private upstream details"), 502),
    ],
)
def test_upstream_errors_are_sanitized(error, status):
    class BrokenService:
        async def recommend(self, request):
            raise error

    with TestClient(create_app(BrokenService())) as client:
        response = client.post("/api/recipes", json={"ingredients": ["beans"], "cuisine": "Indian"})
        assert response.status_code == status
        assert "private upstream" not in response.text


@pytest.mark.parametrize("content", ["not json", "{}"])
def test_invalid_model_output_is_rejected(content):
    async def run():
        transport = httpx.MockTransport(
            lambda _: httpx.Response(200, json={"message": {"content": content}})
        )
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            provider = OllamaProvider(client, "chat", "embed")
            with pytest.raises(ValueError):
                await provider.generate(RecipeRequest(ingredients=["beans"], cuisine="Indian"), [])

    asyncio.run(run())
