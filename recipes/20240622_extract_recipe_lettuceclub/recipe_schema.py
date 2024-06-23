from langchain_core.pydantic_v1 import BaseModel, Field, AnyUrl
from typing import Optional

class Ingredient(BaseModel):
    name: str = Field(..., description='ingredient name. must be single. If a composite, decompose and generate each ingredient.')
    quantity: str = Field('', description='quantity. if not found in text, return "".')

class RecipeCreate(BaseModel):
    "Extract a recipe from the given text."
    name: str = Field(..., description='recipe name')
    recipe_description: str = Field(..., description='recipe description')
    servings: int = Field(..., description='servings')
    ingredients: list[Ingredient] = Field(..., description='ingredients')
    preparation_steps: list[str] = Field(..., description='preparation steps')
    category: Optional[str] = Field(None, description='category')
    cooking_time: Optional[int] = Field(None, description='cooking time')
    kcal: Optional[int] = Field(None, description='kcal')
    cooking_tools: Optional[list[str]] = Field(..., description='cooking tools')

class RecipeWithURL(RecipeCreate):
    url: Optional[AnyUrl]
    image_url: Optional[AnyUrl]