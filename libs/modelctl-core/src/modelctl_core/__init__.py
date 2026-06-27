"""modelctl_core — Core library for model management.

Exposes:
  - Data models: Model, Artifact, Download
  - Registry: persistence layer (JSON or SQLite backend)
  - HuggingFace: search, inspect, download
  - Validator: file integrity checks
  - Store: abstract backend interface + concrete implementations
"""

from .models import Model, Artifact, Download  # noqa: F401
from .store import RegistryStore  # noqa: F401

__version__ = "0.2.0"
