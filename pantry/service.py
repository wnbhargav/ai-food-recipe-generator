import asyncio
import json
from pathlib import Path

from pantry.models import Recipe, RecipeResponse
from pantry.retrieval import keyword_vectors, rank

DATA = Path(__file__).parent / "data"


class RecipeService:
    def __init__(self, provider=None):
        self.provider = provider
        self.documents = json.loads((DATA / "notes.json").read_text(encoding="utf-8"))
        self.examples = json.loads((DATA / "recipes.json").read_text(encoding="utf-8"))
        self.document_vectors = None
        self.index_lock = asyncio.Lock()

    async def recommend(self, request):
        query = request.cuisine + " " + " ".join(request.ingredients)
        texts = [item["title"] + " " + item["text"] for item in self.documents]
        if self.provider:
            async with self.index_lock:
                if self.document_vectors is None:
                    self.document_vectors = await self.provider.embed(texts)
            query_vector = (await self.provider.embed([query]))[0]
            context = rank(self.documents, self.document_vectors, query_vector)
            recipe = await self.provider.generate(request, context)
        else:
            vectors = keyword_vectors(texts + [query])
            context = rank(self.documents, vectors[:-1], vectors[-1])
            example = next(item for item in self.examples if item["cuisine"] == request.cuisine)
            recipe = Recipe.model_validate(example).model_copy(deep=True)
            factor = request.servings / recipe.servings
            for ingredient in recipe.ingredients:
                amount, unit = ingredient.quantity.split(" ", 1)
                ingredient.quantity = f"{float(amount) * factor:g} {unit}"
            recipe.servings = request.servings
        available = set(request.ingredients)
        additional = [
            item.name for item in recipe.ingredients if item.name.lower() not in available
        ]
        return RecipeResponse(
            recipe=recipe,
            additional_ingredients=additional,
            context=context,
            mode="ollama" if self.provider else "demo",
            retrieval="embedding" if self.provider else "keyword",
        )
