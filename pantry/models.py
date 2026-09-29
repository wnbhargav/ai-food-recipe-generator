from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=600)]
Cuisine = Literal["Italian", "Indian", "Mexican", "Mediterranean", "East Asian"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecipeRequest(StrictModel):
    ingredients: list[Annotated[str, StringConstraints(min_length=1, max_length=60)]] = Field(
        min_length=1, max_length=25
    )
    cuisine: Cuisine
    servings: int = Field(default=2, ge=1, le=8)

    @field_validator("ingredients")
    @classmethod
    def normalize_ingredients(cls, values):
        result = list(dict.fromkeys(value.strip().lower() for value in values))
        if any(not value for value in result):
            raise ValueError("Ingredient names cannot be blank")
        return result


class Ingredient(StrictModel):
    name: Text
    quantity: Text


class Recipe(StrictModel):
    title: Text
    cuisine: Cuisine
    servings: int = Field(ge=1, le=8)
    minutes: int = Field(ge=1, le=240)
    ingredients: list[Ingredient] = Field(min_length=1, max_length=30)
    preparation: list[Text] = Field(min_length=1, max_length=12)
    instructions: list[Text] = Field(min_length=1, max_length=15)
    tips: list[Text] = Field(min_length=1, max_length=5)


class Context(StrictModel):
    id: str
    title: str
    text: str
    score: float


class RecipeResponse(StrictModel):
    recipe: Recipe
    additional_ingredients: list[str]
    context: list[Context]
    mode: Literal["demo", "ollama"]
    retrieval: Literal["keyword", "embedding"]
