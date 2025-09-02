"""
Karar motorları paketi.
Her motor BaseDecisionEngine'den türemeli ve registry'ye kendini kaydetmeli.
"""

from .base import BaseDecisionEngine, DecisionRequest, DecisionResult
from .gate import detect_regime
# Orkestratör / rejim kapısı / risk & kalibrasyon yardımcıları
from .orchestrator import OrchestratorConfig, build_consensus_result
from .registry import ENGINE_REGISTRY, register_engine
from .utils import winsorize01, zscore

__all__ = [
    "ENGINE_REGISTRY",
    "register_engine",
    "DecisionRequest",
    "DecisionResult",
    "BaseDecisionEngine",
    "build_consensus_result",
    "OrchestratorConfig",
    "detect_regime",
    "zscore",
    "winsorize01",
]

# Motorların import edilmesi (side-effect: registry dolumu)
# Not: Dosya adları bilinçli kısa tutuldu.
from .engines import km1, km2, km3, km4  # noqa: F401
