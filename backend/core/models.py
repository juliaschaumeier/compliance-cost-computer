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


class TileUpdate(BaseModel):
    title: str | None = None
    text: str | None = None
    meta_information: Dict[str, Any] | None = None
    column: int | None = None
    row: int | None = None
    deletable: bool | None = None
    link_from_tile: List[str] | None = None


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


class ModelsResponse(BaseModel):
    models: List[ModelInfo]
    default: str


class OrganizedModelsResponse(BaseModel):
    organized: OrganizedModels
    default: str
