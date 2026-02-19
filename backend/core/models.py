from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class Tile(BaseModel):
    id: str
    title: str
    text: str = ""
    meta_information: Dict[str, Any] = Field(default_factory=dict)
    column: int = 0
    row: int = 0
    deletable: bool = True
    link_from_tile: List[str] = Field(default_factory=list)


class TilesResponse(BaseModel):
    tiles: List[Tile]


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str


class ProviderModels(BaseModel):
    recommended: List[ModelInfo]
    additional: List[ModelInfo]


class OrganizedModels(BaseModel):
    openai: ProviderModels
    deepinfra: ProviderModels
    gemini: ProviderModels


class OrganizedModelsResponse(BaseModel):
    organized: OrganizedModels
    default: str
