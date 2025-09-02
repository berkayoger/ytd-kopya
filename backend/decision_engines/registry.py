from __future__ import annotations

from typing import Dict, Type

from .base import BaseDecisionEngine

# Motor sınıfları bu registry'ye kaydedilir
ENGINE_REGISTRY: Dict[str, Type[BaseDecisionEngine]] = {}


def register_engine(cls: Type[BaseDecisionEngine]) -> Type[BaseDecisionEngine]:
    """Karar motorunu ID'siyle registry'ye ekleyen dekoratör."""

    ENGINE_REGISTRY[getattr(cls, "engine_id", cls.__name__)] = cls
    return cls
