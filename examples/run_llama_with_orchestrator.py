#!/usr/bin/env python3
"""
Example: Run llama.cpp via the modelctl-orch library.

Demonstrates the full container orchestration lifecycle:

    1. Port allocation
    2. Container start
    3. Inspection and listing
    4. Live log capture
    5. Graceful stop and cleanup
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Ensure the project root is on sys.path so modelctl-orch is importable
# when running as a loose script.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load .env so LLAMACPP_IMAGE (and other env vars) are available
# to the orchestrator. Uses a simple parser — no python-dotenv dependency.
_env_path = REPO_ROOT / ".env"
if _env_path.is_file():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            os.environ.setdefault(_key, _val)

# ── Model resolution helpers ─────────────────────────────────────────────


def find_gguf_file(storage_dir: Path = REPO_ROOT / "storage") -> Path | None:
    """Walk *storage_dir* and return the first ``.gguf`` file found."""
    for root, _dirs, files in os.walk(storage_dir):
        for f in files:
            if f.endswith(".gguf"):
                return Path(root) / f
    return None


# ── Main demo ────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run llama.cpp via the modelctl-orch orchestrator",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate steps without interacting with Docker",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Path to a specific .gguf model file (auto-detected otherwise)",
    )
    args = parser.parse_args()

    # ── Logging setup ─────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s  %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger("orchestrator-demo")

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  modelctl-orch  —  llama.cpp orchestration demo        ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")

    # ── 1. Resolve model ──────────────────────────────────────────────
    logger.info("")
    logger.info("── Step 1: Resolve model ────────────────────────────────")

    model_path: Path | None
    if args.model:
        model_path = Path(args.model).resolve()
        if not model_path.is_file():
            logger.error("Specified model not found: %s", model_path)
            sys.exit(1)
    else:
        model_path = find_gguf_file()
        if model_path is None:
            logger.warning("No .gguf model file found in storage/")
            logger.warning("Using a placeholder path — real containers will fail.")
            model_path = Path("/models/placeholder.gguf")

    logger.info("Model path: %s", model_path)
    model_id = f"local/{model_path.stem}"
    logger.info("Model ID  : %s", model_id)

    # ── 2. Port allocation ────────────────────────────────────────────
    logger.info("")
    logger.info("── Step 2: Allocate port ────────────────────────────────")

    from modelctl_orch.port_allocator import PortAllocator

    allocator = PortAllocator()
    port = allocator.allocate("chat")
    logger.info("Allocated port %d for chat capability", port)

    # ── 3. Container start ────────────────────────────────────────────
    logger.info("")
    logger.info("── Step 3: Start container ──────────────────────────────")

    from modelctl_orch.models import ResourceProfile
    from modelctl_orch.container_manager import ContainerManager

    # Use a CPU-only profile for broader compatibility
    cpu_profile = ResourceProfile(
        memory_limit="4g",
        cpu_count=2.0,
        gpu_device=None,
        gpu_count=0,
    )

    if args.dry_run:
        logger.info("[DRY-RUN] Would start container with:")
        logger.info("          capability : chat")
        logger.info("          model_id   : %s", model_id)
        logger.info("          port       : %d", port)
        logger.info("          profile    : %s", cpu_profile)
        container_info = None
    else:
        try:
            mgr = ContainerManager()
            container_info = mgr.start(
                capability="chat",
                model_id=model_id,
                model_path=str(model_path),
                port=port,
                profile=cpu_profile,
            )
            logger.info("Container started!")
            logger.info("  ID       : %s", container_info.id)
            logger.info("  Name     : modelctl-chat-%s",
                        model_id.replace("/", "-"))
            logger.info("  Status   : %s", container_info.status.value)
            logger.info("  Port     : %d", container_info.port)
        except Exception as exc:
            logger.error("Failed to start container: %s", exc)
            logger.info("This is expected if Docker is not available or the")
            logger.info("inference image is not built yet.")
            container_info = None

    # ── 4. List containers ────────────────────────────────────────────
    logger.info("")
    logger.info("── Step 4: List managed containers ───────────────────────")

    if args.dry_run:
        logger.info("[DRY-RUN] Would list all containers with label modelctl.managed")
        containers = []
    else:
        try:
            mgr = ContainerManager()
            containers = mgr.list()
            logger.info("Found %d managed container(s)", len(containers))
            for c in containers:
                logger.info("  • %s  [%s]  %s  :%d",
                            c.id[:12],
                            c.status.value,
                            c.model_name,
                            c.port)
        except Exception as exc:
            logger.error("Failed to list containers: %s", exc)
            containers = []

    # ── 5. Health check ───────────────────────────────────────────────
    logger.info("")
    logger.info("── Step 5: Health check ──────────────────────────────────")

    if container_info and not args.dry_run:
        try:
            import asyncio
            healthy = asyncio.run(
                ContainerManager.wait_for_healthy(
                    host="localhost",
                    port=port,
                    timeout=15,
                )
            )
            if healthy:
                logger.info("Health check PASSED — container is serving")
            else:
                logger.warning("Health check timed out — container may still be starting")
        except Exception as exc:
            logger.warning("Health check failed: %s", exc)
    else:
        logger.info("[DRY-RUN / no container] Skipping health check")

    # ── 6. Inspect ────────────────────────────────────────────────────
    logger.info("")
    logger.info("── Step 6: Inspect container ─────────────────────────────")

    if container_info and not args.dry_run:
        try:
            detail = mgr.inspect(container_info.id)
            if detail:
                logger.info("Container details:")
                logger.info("  ID        : %s", detail.id)
                logger.info("  Capability: %s", detail.capability)
                logger.info("  Model     : %s", detail.model_name)
                logger.info("  Status    : %s", detail.status.value)
                logger.info("  Port      : %d", detail.port)
                logger.info("  Started   : %s", detail.started_at or "N/A")
            else:
                logger.warning("Container not found (already removed?)")
        except Exception as exc:
            logger.warning("Inspect failed: %s", exc)
    else:
        logger.info("[DRY-RUN / no container] Skipping inspect")

    # ── 7. Fetch logs ─────────────────────────────────────────────────
    logger.info("")
    logger.info("── Step 7: Fetch container logs ──────────────────────────")

    if container_info and not args.dry_run:
        try:
            log_text = mgr.logs(container_info.id, tail=20)
            if log_text:
                logger.info("Last 20 log lines:")
                for line in log_text.strip().splitlines():
                    logger.info("  │ %s", line)
            else:
                logger.info("(No log output yet)")
        except Exception as exc:
            logger.warning("Log fetch failed: %s", exc)
    else:
        logger.info("[DRY-RUN / no container] Skipping log fetch")

    # ── 8. Graceful stop ──────────────────────────────────────────────
    logger.info("")
    logger.info("── Step 8: Stop and clean up ─────────────────────────────")

    if container_info and not args.dry_run:
        try:
            mgr.stop(container_info.id, timeout=10)
            logger.info("Container %s stopped and removed", container_info.id[:12])
        except Exception as exc:
            logger.error("Failed to stop container: %s", exc)

        # Verify it's gone
        remaining = mgr.list()
        if remaining:
            logger.info("Remaining managed container(s): %d", len(remaining))
        else:
            logger.info("All managed containers cleaned up")
    else:
        logger.info("[DRY-RUN] Would stop container %s",
                    container_info.id[:12] if container_info else "(none)")

    # ── 9. Release port ───────────────────────────────────────────────
    logger.info("")
    logger.info("── Step 9: Release port ──────────────────────────────────")
    allocator.release(port)
    logger.info("Port %d released", port)

    # ── Summary ───────────────────────────────────────────────────────
    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  Demo complete                                          ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
