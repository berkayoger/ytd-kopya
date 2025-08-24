"""
Karar motorları paketi.
Her motor BaseDecisionEngine'den türemeli ve registry'ye kendini kaydetmeli.
"""

from .registry import ENGINE_REGISTRY, register_engine
from .base import DecisionRequest, DecisionResult, BaseDecisionEngine

# Orkestratör / rejim kapısı / risk & kalibrasyon yardımcıları
from .orchestrator import build_consensus_result, OrchestratorConfig
from .gate import detect_regime
from .utils import zscore, winsorize01

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

