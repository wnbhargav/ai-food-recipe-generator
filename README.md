# AI Food Recipe Generator

Recipe suggestions from the ingredients in your kitchen and the cuisine you feel like cooking. A Python API retrieves relevant cooking notes, sends them with your request to a local language model, and validates the recipe before displaying it.

The browser interface includes ingredient quantities, preparation, cooking steps, estimated time, extra ingredients to pick up, and the notes retrieved for the request.

## Run locally

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn pantry.main:app --reload
```

Open [localhost:8000](http://localhost:8000). API documentation is at [/docs](http://localhost:8000/docs).

The default **demo mode** needs no model or API key. It serves one sample recipe per cuisine, scales quantities to the requested servings, and retrieves notes using keyword similarity. It does not generate a custom recipe from your ingredients.

## Enable local generation

Install [Ollama](https://ollama.com), start it, and download a chat model and an embedding model:

```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

Copy `.env.example` to `.env`, set `RECIPE_MODE=ollama`, then run:

```bash
uvicorn pantry.main:app --env-file .env --reload
```

`CHAT_MODEL`, `EMBEDDING_MODEL`, and `OLLAMA_URL` are configurable. The first live request embeds the cooking notes and keeps their vectors in memory; subsequent requests only embed the query. Restart after changing the notes or embedding model. Model downloads and generation speed depend on the selected models and your hardware.

## How it works

```text
Ingredients + cuisine + servings
             |
     Request validation
             |
     Query embedding -> cosine search over cooking notes
             |
     Top 3 notes + request + recipe schema
             |
     Local LLM -> response validation -> recipe card
```

The application uses Ollama's [embedding endpoint](https://docs.ollama.com/api/embed) and [chat endpoint](https://docs.ollama.com/api/chat), with the recipe JSON schema passed as the structured-output format. Invalid output is rejected, including mismatched cuisine or serving count. An unavailable model returns an explicit error; it does not silently switch to a sample recipe.

The ten notes and five demo recipes under `pantry/data/` are original project examples, not a scraped recipe collection. Retrieval scores and note text are returned with each recipe for inspection. Retrieved notes are context supplied to the model, not proof that every generated instruction is correct. This small corpus demonstrates RAG mechanics; it has not been benchmarked for recipe quality.

## API example

```bash
curl http://localhost:8000/api/recipes \
  -H 'Content-Type: application/json' \
  -d '{"ingredients":["chickpeas","tomato","onion"],"cuisine":"Indian","servings":2}'
```

Supported cuisines: Italian, Indian, Mexican, Mediterranean, and East Asian. Requests accept 1–25 ingredient names and 1–8 servings. The response contains `recipe`, `additional_ingredients`, `context`, `mode`, and `retrieval`. Ingredient availability uses normalized exact names, so synonyms such as “scallion” and “green onion” may appear as different ingredients.

Errors: `422` for invalid inputs, `502` for invalid model output, `503` for model connectivity errors, and `504` for model timeouts. `/health` reports application liveness and configured mode; it does not verify that models are installed or responsive.

## Development

```bash
pytest -q
ruff check .
ruff format --check .
```

Tests cover request validation, recipe scaling, cuisine selection, similarity search, retrieval context passed to generation, embedding cache reuse, malformed model output, and upstream errors. Provider tests use mocked HTTP responses; no model download is required for CI.

```text
pantry/
  main.py          FastAPI routes and service lifetime
  models.py        Request and response schemas
  provider.py      Ollama API calls and generation prompt
  retrieval.py     Keyword vectors and cosine ranking
  service.py       Retrieval and recipe workflow
  data/            Cooking notes and demo recipes
  static/          Browser interface
tests/             API, retrieval, and provider tests
deploy/            Example Kubernetes manifests
```

## Containers and deployment

```bash
docker compose up --build
```

Compose binds the app to localhost and starts in demo mode. To use Ollama running on the host, set `RECIPE_MODE=ollama` in `.env`. The host Ollama service must accept connections from the Docker network; restrict access to trusted clients if you change its bind address.

The [deployment notes](docs/deployment.md) cover a local Kubernetes example and limits of this setup. GitHub Actions runs linting, tests, a Docker build, and a container smoke test on pushes and pull requests. Deployment to a hosted environment is not automated.

## Scope

This is a personal project for experimenting with retrieval and structured generation. There is no account system, persistence, allergy filter, or nutrition calculator. Recipe text is model output and should be checked before cooking. Public deployment needs authentication, request limits, and resource budgeting for model calls.

## Publish to GitHub

Create an empty repository named `ai-food-recipe-generator` in your GitHub account, then run from this directory:

```bash
git add .
git commit -m "Add recipe API, retrieval, and browser interface"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-food-recipe-generator.git
git push -u origin main
```

Choose a license before inviting reuse; this repository does not include one yet.
