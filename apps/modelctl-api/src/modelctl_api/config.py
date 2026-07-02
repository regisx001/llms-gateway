"""Application configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Modelctl API settings — configure via MODELCTL_API_* env vars."""

    registry_dir: str = ""
    storage_dir: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    hf_token: str = ""

    # ── container orchestration ─────────────────────────────────────
    llamacpp_image: str = "ghcr.io/ggml-org/llama.cpp:server"
    docker_network: str = "modelctl-net"
    container_timeout: int = 30

    model_config = {"env_prefix": "MODELCTL_API_"}


settings = Settings()
