import { config } from "$lib/config";

// ── Types ──────────────────────────────────────────────────────────

export interface ResourceProfile {
    memory_limit: string;
    cpu_count: number;
    gpu_device: string | null;
    gpu_count: number;
}

export interface ContainerInfo {
    id: string;
    capability: string;
    model_id: string;
    model_name: string;
    port: number;
    status: string;
    error: string | null;
    started_at: string | null;
    uptime_seconds: number | null;
    resource_profile: ResourceProfile | null;
}

export interface ModelEntry {
    id: string;
    name: string;
    type: string;
    status: string;
}

// ── Constants ──────────────────────────────────────────────────────

export const capabilities = [
    "chat",
    "embedding",
    "reranker",
    "vision",
    "experimental",
];

// ── State ──────────────────────────────────────────────────────────

// Wrapped in a single object for cross-module export: Svelte requires
// exported state to not be directly reassigned, but mutating properties
// of an exported object is fine.
export const state = $state({
    containers: [] as ContainerInfo[],
    loading: true,
    error: null as string | null,
    actionLoading: null as string | null,

    // Start container sheet
    startSheetOpen: false,
    startLoading: false,
    startError: null as string | null,
    availableModels: [] as ModelEntry[],
    modelsLoading: false,

    // Start form fields
    selectedModelId: "",
    selectedCapability: "chat",
    memoryLimit: "",
    cpuCount: "",
    gpuDevice: "",
    gpuCount: "",

    // Logs sheet
    logsSheetOpen: false,
    logsContent: "",
    logsLoading: false,
    logsContainerId: "",
    logsContainerName: "",
});

// ── Helpers ────────────────────────────────────────────────────────

export function shortId(id: string): string {
    return id.length > 12 ? id.slice(0, 12) : id;
}

export function formatUptime(seconds: number | null): string {
    if (seconds === null || seconds === undefined) return "—";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

export function statusVariant(
    status: string,
): "default" | "secondary" | "outline" | "destructive" {
    switch (status) {
        case "running":
            return "default";
        case "starting":
        case "stopping":
            return "secondary";
        case "stopped":
            return "outline";
        case "failed":
            return "destructive";
        default:
            return "outline";
    }
}

export function capabilityColor(cap: string): string {
    const colors: Record<string, string> = {
        chat: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
        embedding: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
        reranker: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
        vision: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
        experimental: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
    };
    return colors[cap] ?? "bg-muted text-muted-foreground";
}

// ── Data fetching ──────────────────────────────────────────────────

export async function loadContainers() {
    state.error = null;
    try {
        const res = await fetch(`${config.apiBase}/api/v1/containers`);
        if (!res.ok) throw new Error("Failed to load containers");
        const data = await res.json();
        state.containers = data.containers ?? [];
    } catch (e) {
        state.error =
            e instanceof Error ? e.message : "Failed to load containers";
    } finally {
        state.loading = false;
    }
}

export async function loadModels() {
    state.modelsLoading = true;
    try {
        const res = await fetch(`${config.apiBase}/api/v1/models`);
        if (!res.ok) throw new Error("Failed to load models");
        const data = await res.json();
        state.availableModels = (data.models ?? []).filter(
            (m: ModelEntry) =>
                m.status === "installed" || m.status === "active",
        );
    } catch {
        state.availableModels = [];
    } finally {
        state.modelsLoading = false;
    }
}

// ── Actions ────────────────────────────────────────────────────────

export async function startContainer() {
    if (!state.selectedModelId) return;
    state.startLoading = true;
    state.startError = null;
    try {
        const body: Record<string, unknown> = {
            model_id: state.selectedModelId,
            capability: state.selectedCapability,
        };
        const profile: Record<string, unknown> = {};
        if (state.memoryLimit) profile.memory_limit = state.memoryLimit;
        if (state.cpuCount) profile.cpu_count = parseFloat(state.cpuCount);
        if (state.gpuDevice) profile.gpu_device = state.gpuDevice;
        if (state.gpuCount) profile.gpu_count = parseInt(state.gpuCount, 10);
        if (Object.keys(profile).length > 0) {
            body.resource_profile = profile;
        }

        const res = await fetch(`${config.apiBase}/api/v1/containers`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const err = await res
                .json()
                .catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || "Failed to start container");
        }
        state.startSheetOpen = false;
        resetForm();
        await loadContainers();
    } catch (e) {
        state.startError =
            e instanceof Error ? e.message : "Failed to start container";
    } finally {
        state.startLoading = false;
    }
}

export async function stopContainer(id: string) {
    state.actionLoading = id;
    try {
        await fetch(`${config.apiBase}/api/v1/containers/${id}`, {
            method: "DELETE",
        });
        await loadContainers();
    } catch {
        // Silently fail — next refresh will show correct state
    } finally {
        state.actionLoading = null;
    }
}

export async function restartContainer(id: string) {
    state.actionLoading = id;
    try {
        await fetch(`${config.apiBase}/api/v1/containers/${id}/restart`, {
            method: "POST",
        });
        await loadContainers();
    } catch {
        // Silently fail
    } finally {
        state.actionLoading = null;
    }
}

export async function viewLogs(container: ContainerInfo) {
    state.logsContainerId = container.id;
    state.logsContainerName = container.model_name;
    state.logsSheetOpen = true;
    state.logsLoading = true;
    state.logsContent = "";
    try {
        const res = await fetch(
            `${config.apiBase}/api/v1/containers/${container.id}/logs?tail=100`,
        );
        if (!res.ok) throw new Error("Failed to fetch logs");
        const data = await res.json();
        state.logsContent = data.logs || "(no logs)";
    } catch (e) {
        state.logsContent =
            e instanceof Error
                ? `Error: ${e.message}`
                : "Failed to load logs";
    } finally {
        state.logsLoading = false;
    }
}

export function resetForm() {
    state.selectedModelId = "";
    state.selectedCapability = "chat";
    state.memoryLimit = "";
    state.cpuCount = "";
    state.gpuDevice = "";
    state.gpuCount = "";
    state.startError = null;
}

export function openStartSheet() {
    resetForm();
    loadModels();
    state.startSheetOpen = true;
}
