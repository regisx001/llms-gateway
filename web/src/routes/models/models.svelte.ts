import { config } from "$lib/config";

// ── State ──────────────────────────────────────────────────────────

export const ui = $state({
    models: [] as any[],
    loading: true,
    error: null as string | null,
    polling: false,
    pollInterval: null as ReturnType<typeof setInterval> | null,
    searchQuery: "",
    selectedType: "All Types",
    downloadProgress: new Map<
        string,
        {
            progressPct: number;
            downloadedBytes: number;
            totalBytes: number;
        }
    >(),
});

// ── Utilities ──────────────────────────────────────────────────────

export function sizeStr(bytes: number): string {
    const units = ["B", "KB", "MB", "GB", "TB"];
    let n = bytes;
    for (const u of units) {
        if (n < 1024) return `${n.toFixed(1)} ${u}`;
        n /= 1024;
    }
    return `${n.toFixed(1)} PB`;
}

export function typeColor(type: string): string {
    const colors: Record<string, string> = {
        chat: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
        embedding: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
        reranker: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
        vision: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
        experimental: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
    };
    return colors[type] ?? "bg-muted text-muted-foreground";
}

export function formatInstalled(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", {
        month: "2-digit",
        day: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

// ── Data fetching ──────────────────────────────────────────────────

export async function loadModels() {
    ui.error = null;
    try {
        const modelRes = await fetch(`${config.apiBase}/api/v1/models`);
        if (!modelRes.ok) throw new Error("Failed to load models");
        const modelData = await modelRes.json();

        // Store raw bytes for accurate total size calculation
        ui.models = modelData.models.map((m: any) => ({
            ...m,
            _rawBytes:
                m.artifacts?.reduce(
                    (a: number, art: any) => a + (art.size ?? 0),
                    0,
                ) ?? 0,
            size: sizeStr(
                m.artifacts?.reduce(
                    (a: number, art: any) => a + (art.size ?? 0),
                    0,
                ) ?? 0,
            ),
        }));

        // Fetch progress for downloading models
        const downloadingModels = ui.models.filter(
            (m: any) => m.status === "downloading",
        );
        if (downloadingModels.length > 0) {
            const progressResults = await Promise.allSettled(
                downloadingModels.map(async (m: any) => {
                    const res = await fetch(
                        `${config.apiBase}/api/v1/models/${m.id}/progress`,
                    );
                    if (!res.ok) return null;
                    return { id: m.id, ...(await res.json()) };
                }),
            );
            const newProgress = new Map(ui.downloadProgress);
            for (const r of progressResults) {
                if (r.status === "fulfilled" && r.value) {
                    newProgress.set(r.value.id, {
                        progressPct: r.value.progress_pct,
                        downloadedBytes: r.value.downloaded_bytes,
                        totalBytes: r.value.total_bytes,
                    });
                }
            }
            ui.downloadProgress = newProgress;
        }

        // Start polling if any models are downloading
        const hasDownloading = ui.models.some(
            (m: any) => m.status === "downloading",
        );
        if (hasDownloading && !ui.polling) {
            startPolling();
        } else if (!hasDownloading && ui.polling) {
            stopPolling();
        }
    } catch (e) {
        ui.error = e instanceof Error ? e.message : "Failed to load models";
    } finally {
        ui.loading = false;
    }
}

export function startPolling() {
    ui.polling = true;
    ui.pollInterval = setInterval(loadModels, 2000);
}

export function stopPolling() {
    ui.polling = false;
    if (ui.pollInterval) {
        clearInterval(ui.pollInterval);
        ui.pollInterval = null;
    }
}

export async function postAction(path: string) {
    await fetch(`${config.apiBase}${path}`, { method: "POST" });
    await loadModels();
}
