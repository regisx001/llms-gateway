/**
 * Reactive download store — tracks active model downloads with progress.
 *
 * Usage:
 *   import { downloads, startDownload } from "$lib/stores/downloads.svelte";
 *   startDownload(modelId, apiBase);
 *   // downloads array auto-updates via polling
 */

import { config } from "$lib/config";

export interface DownloadProgress {
    modelId: string;
    repoId: string;
    filename: string;
    status: string; // "downloading" | "installed" | "active" | "error"
    downloadedBytes: number;
    totalBytes: number;
    progressPct: number;
    error: string | null;
}

let _downloads = $state<DownloadProgress[]>([]);
let _pollIntervals = new Map<string, ReturnType<typeof setInterval>>();

export const downloads = {
    get all(): DownloadProgress[] {
        return _downloads;
    },
    get active(): DownloadProgress[] {
        return _downloads.filter((d) => d.status === "downloading");
    },
    get hasActive(): boolean {
        return _downloads.some((d) => d.status === "downloading");
    },
};

function formatSize(bytes: number): string {
    const units = ["B", "KB", "MB", "GB", "TB"];
    let n = bytes;
    for (const u of units) {
        if (n < 1024) return `${n.toFixed(1)} ${u}`;
        n /= 1024;
    }
    return `${n.toFixed(1)} PB`;
}

export { formatSize as downloadFormatSize };

async function pollProgress(
    modelId: string,
    apiBase: string,
): Promise<boolean> {
    try {
        const res = await fetch(
            `${apiBase}/api/v1/models/${modelId}/progress`,
        );
        if (!res.ok) return false;

        const data = await res.json();
        const idx = _downloads.findIndex((d) => d.modelId === modelId);
        if (idx === -1) return data.status === "downloading";

        _downloads[idx] = {
            modelId: data.model_id,
            repoId: data.repo_id || _downloads[idx].repoId,
            filename: data.filename || _downloads[idx].filename,
            status: data.status,
            downloadedBytes: data.downloaded_bytes,
            totalBytes: data.total_bytes,
            progressPct: data.progress_pct,
            error: data.error || null,
        };

        return data.status === "downloading";
    } catch {
        return true; // keep polling on network errors
    }
}

export function startDownload(modelId: string, repoId: string, filename: string) {
    // Check if already tracking
    if (_downloads.some((d) => d.modelId === modelId)) return;

    _downloads.push({
        modelId,
        repoId,
        filename,
        status: "downloading",
        downloadedBytes: 0,
        totalBytes: 0,
        progressPct: 0,
        error: null,
    });

    const apiBase = config.apiBase;

    // Poll every 1.5 seconds
    const interval = setInterval(async () => {
        const keepPolling = await pollProgress(modelId, apiBase);
        if (!keepPolling) {
            stopPolling(modelId);
            // Keep completed/error state for 8 seconds then auto-dismiss
            setTimeout(() => dismiss(modelId), 8000);
        }
    }, 1500);

    _pollIntervals.set(modelId, interval);
}

function stopPolling(modelId: string) {
    const interval = _pollIntervals.get(modelId);
    if (interval) {
        clearInterval(interval);
        _pollIntervals.delete(modelId);
    }
}

export function dismiss(modelId: string) {
    stopPolling(modelId);
    _downloads = _downloads.filter((d) => d.modelId !== modelId);
}

export function dismissAll() {
    for (const [id] of _pollIntervals) {
        stopPolling(id);
    }
    _downloads = [];
}
