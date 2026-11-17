"""
Structure-Aware STAR-RAG Configuration Settings.
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StructureAwareStarRagConfig(BaseModel):
    """Configuration parameters for Structure-Aware STAR-RAG retrieval."""

    enabled: bool = Field(default=False)
    snr_enabled: bool = Field(default=True)
    dtp_enabled: bool = Field(default=True)
    ssaf_enabled: bool = Field(default=True)

    # SNR parameters
    snr_noise_threshold: float = Field(default=0.30)
    snr_semantic_weight: float = Field(default=0.70)
    snr_temperature: float = Field(default=1.0)

    # DTP parameters
    dtp_max_hops: int = Field(default=3)
    dtp_decay_factor: float = Field(default=0.75)
    dtp_in_degree_weight: float = Field(default=0.60)
    dtp_out_degree_weight: float = Field(default=0.40)

    # SSAF parameters
    ssaf_conflict_threshold: float = Field(default=0.40)
    ssaf_default_beta: float = Field(default=0.55)
    ssaf_temperature: float = Field(default=1.0)

    # Evidence path parameters
    max_path_depth: int = Field(default=4)
    max_paths_per_candidate: int = Field(default=3)
