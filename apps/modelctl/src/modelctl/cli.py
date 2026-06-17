"""CLI — modelctl commands."""

from __future__ import annotations

import datetime
import os
import sys
import time
from pathlib import Path

from modelctl_core import registry
from modelctl_core import huggingface as hf
from modelctl_core import validator
from modelctl_core.models import Model, Artifact, Download

from . import __version__


def _storage_path(model) -> Path:
    """Resolve the absolute storage path for a model, works in host and container."""
    rel = model.storage_path
    if rel.startswith("storage/"):
        rel = rel[len("storage/"):]
    return registry.STORAGE_DIR / rel


def _size_str(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def cmd_search(args):
    """Search HuggingFace for GGUF repositories."""
    query = " ".join(args)
    if not query:
        print("Usage: modelctl search <query>")
        return

    print(f"Searching for '{query}'...\n")
    try:
        results = hf.search(query)
    except Exception as e:
        print(f"Search failed: {e}")
        return

    if not results:
        print("No GGUF repositories found.")
        return

    for r in results:
        print(f"{'='*60}")
        print(f"  {r['repo_id']}")
        print(
            f"  Type: {r['type']}  |  Downloads: {r['downloads']:,}  |  Likes: {r['likes']}")
        tags = [t for t in r['tags'] if t]
        if tags:
            print(f"  Tags: {', '.join(tags[:5])}")
        if r['license']:
            print(f"  License: {r['license']}")
        print(f"  (use 'modelctl inspect {r['repo_id']}' to see files)")
        print()

    print(f"{len(results)} results shown.")


def cmd_inspect(repo_id: str):
    """Show repository details and available files."""
    try:
        info = hf.inspect(repo_id)
    except Exception as e:
        print(f"Inspect failed: {e}")
        return

    if not info:
        print(f"Repository not found: {repo_id}")
        return

    print(f"Repository: {info['repo_id']}")
    print(f"Type:       {info['type']}")
    print(f"Pipeline:   {info['pipeline_tag']}")
    print(f"Library:    {info['library_name']}")
    print(f"License:    {info['license']}")
    print(f"Downloads:  {info['downloads']:,}")
    print(f"Likes:      {info['likes']}")
    if info["description"]:
        print(f"About:      {info['description'][:200]}")

    print(f"\nAvailable GGUF files ({len(info['gguf_files'])}):")
    for f in info["gguf_files"]:
        print(f"  \u2022 {f}")

    print(f"\nTotal files in repo: {len(info['all_files'])}")


def cmd_install(repo_id: str, filename: str):
    """Download and register a model artifact."""
    if not repo_id:
        print("Usage: modelctl install <repo_id> <filename>")
        return

    existing = None
    for m in registry.load_models():
        if m.repo_id == repo_id and any(a.name == filename for a in m.artifacts):
            if m.status == "installed":
                print(f"Already installed: {repo_id} / {filename}")
                return
            existing = m.id
            print(f"Resuming interrupted install for {existing}...")
            break

    print(f"Analyzing {repo_id}...")
    try:
        info = hf.inspect(repo_id)
    except Exception as e:
        print(f"Failed to fetch repo: {e}")
        return

    if not info:
        print(f"Repository not found: {repo_id}")
        return

    if filename not in info["all_files"]:
        print(f"File '{filename}' not found in repository.")
        print(f"Available GGUF files: {', '.join(info['gguf_files'])}")
        return

    if existing:
        model = hf.build_model_from_repo(repo_id, filename, repo_info=info)
        model.id = existing
        registry.update_model(existing, status="downloading", artifacts=[
                              Artifact(name=filename, role="primary", file_type="gguf")])
        storage_dir = registry.resolve_storage(model.type, model.id)
    else:
        model = hf.build_model_from_repo(repo_id, filename, repo_info=info)
        model.status = "downloading"
        registry.add_model(model)
        storage_dir = registry.resolve_storage(model.type, model.id)

    files_dir = storage_dir / "files"
    if files_dir.exists():
        import shutil
        shutil.rmtree(files_dir)
    files_dir.mkdir(parents=True, exist_ok=True)

    print(f"Installing {repo_id} / {filename}")
    print(f"  \u2192 {files_dir / filename}\n")

    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    dl = Download(url=url, destination=str(
        files_dir / filename), status="downloading")
    registry.add_download(dl)

    last_update = [time.time()]

    def on_progress(current, total):
        now = time.time()
        if now - last_update[0] > 0.3 or current >= total:
            pct = current * 100 // total
            bar = "\u2588" * (pct // 5) + "\u2591" * (20 - pct // 5)
            sys.stdout.write(
                f"\r  [{bar}] {pct}%  {_size_str(current)} / {_size_str(total)}  ")
            sys.stdout.flush()
            last_update[0] = now
            registry.update_download(
                url, downloaded_bytes=current, total_bytes=total)

    try:
        dest = hf.download_file(
            repo_id, filename, files_dir, on_progress=on_progress)
    except Exception as e:
        print(f"\nDownload failed: {e}")
        registry.update_download(url, status="failed", error=str(e))
        registry.update_model(model.id, status="error")
        return

    print()

    issues = validator.validate_file(dest)
    if issues:
        print("Validation issues:")
        for i in issues:
            print(f"  \u26a0 {i}")

    actual_size = dest.stat().st_size
    artifact = Artifact(
        name=filename,
        role="primary",
        path=f"files/{filename}",
        size=actual_size,
        file_type="gguf",
        sha256=validator.sha256(dest),
    )
    installed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    registry.update_model(
        model.id,
        status="installed",
        storage_path=f"{model.type}/{model.id}",
        artifacts=[artifact],
        installed_at=installed_at,
    )

    registry.update_download(
        url, status="completed", downloaded_bytes=actual_size,
        total_bytes=actual_size, completed_at=installed_at,
    )

    print(f"Done. Model ID: {model.id}")
    print(f"Run: modelctl activate {model.id}")


def cmd_list():
    """Show all installed models."""
    models = registry.load_models()
    if not models:
        print("No models installed.")
        print("Search: modelctl search <query>")
        print("Install: modelctl install <repo_id> <filename>")
        return

    active_data = registry.load_active()
    active_ids = {e["model_id"] for e in active_data.get("active", [])}

    print(f"{'ID':<30} {'Name':<25} {'Type':<15} {'Status':<15} {'Size':>10}")
    print("-" * 100)
    for m in models:
        total_size = sum(a.size for a in m.artifacts)
        indicator = "\u25cf " if m.id in active_ids else "  "
        print(f"{indicator}{m.id:<28} {m.name:<25} {m.type:<15} {m.status:<15} {_size_str(total_size):>10}")


def cmd_info(model_id: str):
    """Show detailed info about an installed model."""
    m = registry.find_model(model_id)
    if not m:
        print(f"Model not found: {model_id}")
        return

    print(f"ID:          {m.id}")
    print(f"Name:        {m.name}")
    print(f"Type:        {m.type}")
    print(f"Provider:    {m.provider}")
    print(f"Repository:  {m.repo_id}")
    print(f"Storage:     {m.storage_path}")
    print(f"Status:      {m.status}")
    print(f"Installed:   {m.installed_at or 'N/A'}")
    print(f"\nArtifacts ({len(m.artifacts)}):")
    for a in m.artifacts:
        print(f"  \u2022 {a.name}  ({_size_str(a.size)})  [{a.role}]")
        if a.sha256:
            print(f"    SHA256: {a.sha256}")


def cmd_activate(model_id: str, no_reload: bool = False):
    """Activate a model for serving."""
    m = registry.find_model(model_id)
    if not m:
        print(f"Model not found: {model_id}")
        return
    if m.status != "installed":
        print(f"Model status is '{m.status}', must be 'installed'")
        return

    # Find primary artifact
    primary = next((a for a in m.artifacts if a.role == "primary"),
                   m.artifacts[0] if m.artifacts else None)
    if not primary:
        print(f"No artifacts found for {model_id}")
        return

    # Remove all existing .gguf symlinks, then create the new one
    storage_dir = registry.STORAGE_DIR
    storage_dir.mkdir(exist_ok=True)
    for p in storage_dir.glob("*.gguf"):
        if p.is_symlink() or p.exists():
            p.unlink()
    symlink = storage_dir / f"{m.id}.gguf"
    target = _storage_path(m) / primary.path
    relative_target = os.path.relpath(target, storage_dir)
    symlink.symlink_to(relative_target)

    registry.set_active(model_id, m.type)
    print(f"Activated: {model_id} ({m.type})")
    print(f"  Symlink: storage/{m.id}.gguf → {relative_target}")

    if not no_reload:
        cmd_reload()


def cmd_deactivate(model_id: str):
    """Deactivate a model."""
    m = registry.find_model(model_id)
    if not m:
        print(f"Model not found: {model_id}")
        return
    registry.clear_active(model_id)
    symlink = registry.STORAGE_DIR / f"active-{m.type}.gguf"
    if symlink.is_symlink() or symlink.exists():
        symlink.unlink()
    print(f"Deactivated: {model_id}")


def cmd_active():
    """Show active models."""
    data = registry.load_active()
    entries = data.get("active", [])
    if not entries:
        print("No active models.")
        return
    print("Active models by type:\n")
    for e in entries:
        m = registry.find_model(e["model_id"])
        name = m.name if m else e["model_id"]
        print(f"  \u25cf {e['model_id']}  ({e['type']})  \u2192  {name}")
        print(f"    Activated: {e.get('activated_at', '?')}")


def cmd_remove(model_id: str):
    """Remove a model and its files."""
    m = registry.find_model(model_id)
    if not m:
        print(f"Model not found: {model_id}")
        return

    registry.clear_active(model_id)

    symlink = registry.STORAGE_DIR / f"{m.id}.gguf"
    if symlink.is_symlink() or symlink.exists():
        symlink.unlink()

    storage_path = _storage_path(m)
    if storage_path.exists():
        import shutil
        shutil.rmtree(storage_path)
        print(f"Removed files: {storage_path}")

    registry.remove_model(model_id)
    print(f"Removed from registry: {model_id}")


def cmd_verify(model_id: str):
    """Verify an installed model's files."""
    m = registry.find_model(model_id)
    if not m:
        print(f"Model not found: {model_id}")
        return

    storage_path = _storage_path(m)
    print(f"Verifying {model_id}...\n")

    all_ok = True
    for a in m.artifacts:
        full_path = storage_path / a.path
        issues = validator.validate_file(full_path, a.size)
        if issues:
            all_ok = False
            for i in issues:
                print(f"  \u2717 {i}")
        else:
            if a.sha256:
                actual = validator.sha256(full_path)
                if actual != a.sha256:
                    print(f"  \u2717 SHA256 mismatch: {a.name}")
                    all_ok = False
                else:
                    print(f"  \u2713 {a.name}  ({_size_str(a.size)})")
            else:
                print(f"  \u2713 {a.name}  ({_size_str(a.size)})")

    if all_ok:
        print(f"\nAll artifacts verified for {model_id}")
    else:
        print(f"\nSome checks failed for {model_id}")


def cmd_reload():
    """Reload the server with the currently active model."""
    try:
        # Read PID file written by entrypoint, or pkill as fallback
        pid_file = "/tmp/llama-server.pid"
        if os.path.exists(pid_file):
            with open(pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)  # SIGTERM
            print("Reloading server with active model...")
        else:
            import subprocess
            result = subprocess.run(
                ["pkill", "-SIGTERM", "-x", "llama-server"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                print("Reloading server with active model...")
            else:
                print("No running llama-server found to reload")
    except Exception as e:
        print(f"Reload failed: {e}")


def cmd_version():
    """Show version."""
    print(f"modelctl v{__version__}")


# ── main ───────────────────────────────────────────────────────────────

COMMANDS = {
    "search":    (cmd_search,    "Search HuggingFace for GGUF models"),
    "inspect":   (cmd_inspect,   "Show repository details and files"),
    "install":   (cmd_install,   "Download and register a model"),
    "list":      (cmd_list,      "List installed models"),
    "info":      (cmd_info,      "Show model details"),
    "activate":  (cmd_activate,  "Activate a model for serving"),
    "deactivate":(cmd_deactivate,"Deactivate a model"),
    "active":    (cmd_active,    "Show active models"),
    "remove":    (cmd_remove,    "Remove a model and its files"),
    "verify":    (cmd_verify,    "Verify installed model files"),
    "reload":    (cmd_reload,    "Reload server with active model"),
    "version":   (cmd_version,   "Show modelctl version"),
}


def main():
    if len(sys.argv) < 2:
        print("modelctl — Model Management CLI\n")
        print("Usage: modelctl <command> [args]\n")
        print("Commands:")
        for name, (_, desc) in COMMANDS.items():
            print(f"  {name:<14} {desc}")
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS)}")
        sys.exit(1)

    handler, _ = COMMANDS[cmd]

    if cmd == "search":
        handler(args)
    elif cmd == "inspect":
        if not args:
            print("Usage: modelctl inspect <repo_id>")
            return
        handler(args[0])
    elif cmd == "install":
        if not args:
            print("Usage: modelctl install <repo_id> <filename>")
            return
        handler(args[0], args[1] if len(args) > 1 else "")
    elif cmd in ("info", "activate", "deactivate", "remove", "verify"):
        if not args:
            print(f"Usage: modelctl {cmd} <model_id>")
            return
        handler(args[0])
    else:
        handler()
