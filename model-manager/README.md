# modelctl — Model Management System

Single source of truth for all models on your platform.

```
Filesystem = physical files
Registry   = logical metadata
```

- Never use the filesystem as your database.
- Never scan directories to discover models.
- Everything must come from the registry.

---

## Philosophy

```
Repository ≠ Model
Model      ≠ File
Model      = Metadata + Artifacts + Registry Entry
```

A HuggingFace repo may contain multiple quantizations (`Q2_K`, `Q4_K_M`, `Q8_0`), a tokenizer, config files, etc. Each of these is an **artifact**. The registry tracks them all. The inference layer never cares where the model came from — it reads the active symlink.

---

## Project Structure

```
model-manager/
├── modelctl/               # Python package
│   ├── __init__.py
│   ├── cli.py              # CLI commands
│   ├── models.py           # Dataclasses (Model, Artifact, Download)
│   ├── registry.py         # JSON file persistence
│   ├── huggingface.py      # HuggingFace Hub provider
│   └── validator.py        # File validation + SHA256
├── registry/               # JSON state — the source of truth
│   ├── models.json         # All installed models
│   ├── active.json         # Currently active model per type
│   └── downloads.json      # Download audit trail
├── storage/                # Physical model files by type
│   ├── chat/               #   e.g. chat/qwen3-8b/files/q4_k_m.gguf
│   ├── embedding/
│   ├── reranker/
│   ├── vision/
│   └── experimental/
├── pyproject.toml
└── README.md
```

---

## Quick Start

```bash
# Install
pip install -e .

# Search HuggingFace
modelctl search qwen

# Inspect a repo to see available files
modelctl inspect Qwen/Qwen3-8B-Instruct-GGUF

# Download and register a specific file
modelctl install Qwen/Qwen3-8B-Instruct-GGUF qwen3-8b-instruct-q4_k_m.gguf

# List what's installed
modelctl list

# See details
modelctl info <model-id>

# Activate (creates the symlink for inference)
modelctl activate <model-id>

# See what's active
modelctl active

# Remove
modelctl remove <model-id>
```

---

## Command Reference

### `modelctl search <query>`

Search HuggingFace for repositories matching the query. Results include repo ID, type, download count, tags, and license.

```
$ modelctl search qwen
Searching for 'qwen'...

============================================================
  Qwen/Qwen3-0.6B
  Type: chat  |  Downloads: 18,337,841  |  Likes: 1327
  Tags: text-generation, transformers, safetensors, qwen3
  (use 'modelctl inspect Qwen/Qwen3-0.6B' to see files)
```

### `modelctl inspect <repo_id>`

Show detailed repository info and list all available GGUF files.

```
$ modelctl inspect TheBloke/Llama-2-7B-GGUF
Repository: TheBloke/Llama-2-7B-GGUF
Type:       chat
Pipeline:   text-generation
Library:    transformers
License:    llama2

Available GGUF files (12):
  • llama-2-7b.Q2_K.gguf
  • llama-2-7b.Q3_K_L.gguf
  ...
```

### `modelctl install <repo_id> <filename>`

Download a single artifact from a HuggingFace repo, validate it, and register it in the registry.

```
$ modelctl install tensorblock/tiny_starcoder_py-GGUF tiny_starcoder_py-Q2_K.gguf
Analyzing tensorblock/tiny_starcoder_py-GGUF...
Installing tensorblock/tiny_starcoder_py-GGUF / tiny_starcoder_py-Q2_K.gguf
  → storage/chat/tiny-starcoder-py-gguf/files/tiny_starcoder_py-Q2_K.gguf

  [████████████████████] 100%  99.1 MB / 99.1 MB

Done. Model ID: tiny-starcoder-py-gguf
Run: modelctl activate tiny-starcoder-py-gguf
```

Flow: **Download → Validate (GGUF magic bytes, SHA256) → Register in models.json.**

If interrupted, running `install` again with the same repo+file detects the incomplete state and resumes.

### `modelctl list`

List all registered models with their status, type, and size. Active models are marked with `●`.

```
$ modelctl list
ID                             Name                      Type            Status                Size
----------------------------------------------------------------------------------------------------
● tiny-starcoder-py-gguf      tiny_starcoder_py-GGUF    chat            installed          99.1 MB
```

### `modelctl info <model_id>`

Detailed view of a single model: metadata, storage path, artifacts, and SHA256 hashes.

```
$ modelctl info tiny-starcoder-py-gguf
ID:          tiny-starcoder-py-gguf
Name:        tiny_starcoder_py-GGUF
Type:        chat
Provider:    huggingface
Repository:  tensorblock/tiny_starcoder_py-GGUF
Storage:     storage/chat/tiny-starcoder-py-gguf
Status:      installed
Installed:   2026-06-15T18:20:33+00:00

Artifacts (1):
  • tiny_starcoder_py-Q2_K.gguf  (99.1 MB)  [primary]
    SHA256: a0463c7f7c590f64674e9bbcfdb273d15ee77eeb3e2902b362549c40a64c13f2
```

### `modelctl activate <model_id>`

Activate a model by creating a **relative symlink** at `storage/active.gguf` pointing to the model's primary artifact. This symlink is the contract with the inference server (llama.cpp).

```
$ modelctl activate tiny-starcoder-py-gguf
Activated: tiny-starcoder-py-gguf (chat)
  Symlink: storage/active.gguf → chat/tiny-starcoder-py-gguf/files/tiny_starcoder_py-Q2_K.gguf
```

Inside Docker (where `storage/` is mounted at `/models/`), the server reads `/models/active.gguf` which resolves to the actual GGUF file.

### `modelctl deactivate <model_id>`

Remove the symlink and clear the active state.

```
$ modelctl deactivate tiny-starcoder-py-gguf
Deactivated: tiny-starcoder-py-gguf
```

### `modelctl active`

Show all currently active models.

```
$ modelctl active
Active models by type:

  ● tiny-starcoder-py-gguf  (chat)  →  tiny_starcoder_py-GGUF
    Activated: 2026-06-15T18:20:45+00:00
```

### `modelctl remove <model_id>`

Remove a model completely: deactivate if active, delete all files from `storage/`, and remove the registry entry.

```
$ modelctl remove tiny-starcoder-py-gguf
Removed files: .../storage/chat/tiny-starcoder-py-gguf
Removed from registry: tiny-starcoder-py-gguf
```

### `modelctl verify <model_id>`

Validate an installed model's files — checks file existence, size, GGUF magic bytes, and SHA256 hash against the stored value.

```
$ modelctl verify tiny-starcoder-py-gguf
Verifying tiny-starcoder-py-gguf...

  ✓ tiny_starcoder_py-Q2_K.gguf  (99.1 MB)

All artifacts verified for tiny-starcoder-py-gguf
```

---

## Registry (the source of truth)

### `registry/models.json`

```json
{
  "models": [
    {
      "id": "tiny-starcoder-py-gguf",
      "name": "tiny_starcoder_py-GGUF",
      "type": "chat",
      "provider": "huggingface",
      "repo_id": "tensorblock/tiny_starcoder_py-GGUF",
      "storage_path": "storage/chat/tiny-starcoder-py-gguf",
      "status": "installed",
      "installed_at": "2026-06-15T18:20:33+00:00",
      "artifacts": [
        {
          "name": "tiny_starcoder_py-Q2_K.gguf",
          "role": "primary",
          "path": "files/tiny_starcoder_py-Q2_K.gguf",
          "size": 103899744,
          "file_type": "gguf",
          "sha256": "a0463c7f7c590f64674e9bbcfdb273d15ee77eeb3e2902b362549c40a64c13f2"
        }
      ]
    }
  ]
}
```

### `registry/active.json`

```json
{
  "active": [
    {
      "model_id": "tiny-starcoder-py-gguf",
      "type": "chat",
      "activated_at": "2026-06-15T18:20:45+00:00"
    }
  ]
}
```

Model states: `registered` → `downloading` → `installed` → `active` | `error`

---

## Docker Integration

The symlink contract makes container coordination simple.

```yaml
services:
  llama-server:
    image: ${LLAMACPP_IMAGE}
    ports:
      - "${LLAMACPP_PORT}:8080"
    volumes:
      - ./model-manager/storage:/models
    command: >
      --host 0.0.0.0 --port 8080 -m /models/active.gguf
```

To swap models at runtime:

```bash
modelctl deactivate current-model-id
modelctl activate new-model-id
docker restart llama-server
```

No config changes, no volume re-mounting, no image rebuild. Just update the symlink and restart.

---

## Data Model

| Concept | Represented as | Persisted in |
|---------|---------------|--------------|
| **Model** | `Model` dataclass | `registry/models.json` |
| **Artifact** | `Artifact` dataclass (name, role, path, size, sha256) | Inside model entry |
| **Download** | `Download` dataclass (url, status, progress) | `registry/downloads.json` |
| **Active** | model_id + type mapping | `registry/active.json` |
| **Symlink** | `storage/active.gguf` | Filesystem (relative symlink) |

### Artifact Roles

| Role | Description |
|------|-------------|
| `primary` | Main model weights (GGUF) |
| `tokenizer` | Tokenizer files |
| `config` | Model configuration |
| `documentation` | README, license |
| `adapter` | LoRA/QLoRA adapters |
| `other` | Everything else |

---

## Storage Layout

```
storage/
├── active.gguf                 ← Symlink to the active model (managed by `activate`)
├── chat/
│   └── <model-id>/
│       ├── metadata.json       ← (future) Per-model metadata
│       └── files/
│           └── <filename>.gguf
├── embedding/
├── reranker/
├── vision/
└── experimental/
```

Model types match subdirectories: `chat`, `embedding`, `reranker`, `vision`, `experimental`.

---

## Lifecycle

```
Search (modelctl search)
   │
   ▼
Inspect (modelctl inspect)
   │
   ▼
Install (modelctl install)
   ├── Download from HuggingFace
   ├── Validate file integrity
   └── Register in models.json
   │
   ▼
Activate (modelctl activate)
   ├── Update active.json
   └── Create storage/active.gguf symlink
   │
   ▼
Serve (llama-server reads /models/active.gguf via Docker mount)
   │
   ▼
Deactivate / Remove (modelctl deactivate | remove)
```
