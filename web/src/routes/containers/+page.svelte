<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { config } from "$lib/config";
    import * as Card from "$lib/components/ui/card";
    import * as Table from "$lib/components/ui/table";
    import * as Sheet from "$lib/components/ui/sheet";
    import { Badge } from "$lib/components/ui/badge";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Skeleton } from "$lib/components/ui/skeleton";
    import { Spinner } from "$lib/components/ui/spinner";
    import { Separator } from "$lib/components/ui/separator";
    import BoxIcon from "@lucide/svelte/icons/box";
    import PlayIcon from "@lucide/svelte/icons/play";
    import SquareIcon from "@lucide/svelte/icons/square";
    import RotateCwIcon from "@lucide/svelte/icons/rotate-cw";
    import TerminalIcon from "@lucide/svelte/icons/terminal";
    import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
    import AlertCircleIcon from "@lucide/svelte/icons/alert-circle";

    // ── Types ────────────────────────────────────────────────────────

    interface ResourceProfile {
        memory_limit: string;
        cpu_count: number;
        gpu_device: string | null;
        gpu_count: number;
    }

    interface ContainerInfo {
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

    interface ModelEntry {
        id: string;
        name: string;
        type: string;
        status: string;
    }

    // ── State ────────────────────────────────────────────────────────

    let containers = $state<ContainerInfo[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let actionLoading = $state<string | null>(null);

    // Start container sheet
    let startSheetOpen = $state(false);
    let startLoading = $state(false);
    let startError = $state<string | null>(null);
    let availableModels = $state<ModelEntry[]>([]);
    let modelsLoading = $state(false);

    // Start form fields
    let selectedModelId = $state("");
    let selectedCapability = $state("chat");
    let memoryLimit = $state("");
    let cpuCount = $state("");
    let gpuDevice = $state("");
    let gpuCount = $state("");

    // Logs sheet
    let logsSheetOpen = $state(false);
    let logsContent = $state("");
    let logsLoading = $state(false);
    let logsContainerId = $state("");
    let logsContainerName = $state("");

    const capabilities = [
        "chat",
        "embedding",
        "reranker",
        "vision",
        "experimental",
    ];

    // ── Helpers ──────────────────────────────────────────────────────

    function shortId(id: string): string {
        return id.length > 12 ? id.slice(0, 12) : id;
    }

    function formatUptime(seconds: number | null): string {
        if (seconds === null || seconds === undefined) return "—";
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        if (h > 0) return `${h}h ${m}m`;
        if (m > 0) return `${m}m ${s}s`;
        return `${s}s`;
    }

    function statusVariant(
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

    function capabilityColor(cap: string): string {
        const colors: Record<string, string> = {
            chat: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
            embedding: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
            reranker: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
            vision: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
            experimental: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
        };
        return colors[cap] ?? "bg-muted text-muted-foreground";
    }

    // ── Data fetching ────────────────────────────────────────────────

    async function loadContainers() {
        error = null;
        try {
            const res = await fetch(`${config.apiBase}/api/v1/containers`);
            if (!res.ok) throw new Error("Failed to load containers");
            const data = await res.json();
            containers = data.containers ?? [];
        } catch (e) {
            error =
                e instanceof Error ? e.message : "Failed to load containers";
        } finally {
            loading = false;
        }
    }

    async function loadModels() {
        modelsLoading = true;
        try {
            const res = await fetch(`${config.apiBase}/api/v1/models`);
            if (!res.ok) throw new Error("Failed to load models");
            const data = await res.json();
            // Only show models that are installed (not downloading/error)
            availableModels = (data.models ?? []).filter(
                (m: ModelEntry) =>
                    m.status === "installed" || m.status === "active",
            );
        } catch {
            availableModels = [];
        } finally {
            modelsLoading = false;
        }
    }

    // ── Actions ──────────────────────────────────────────────────────

    async function startContainer() {
        if (!selectedModelId) return;
        startLoading = true;
        startError = null;
        try {
            const body: Record<string, unknown> = {
                model_id: selectedModelId,
                capability: selectedCapability,
            };
            const profile: Record<string, unknown> = {};
            if (memoryLimit) profile.memory_limit = memoryLimit;
            if (cpuCount) profile.cpu_count = parseFloat(cpuCount);
            if (gpuDevice) profile.gpu_device = gpuDevice;
            if (gpuCount) profile.gpu_count = parseInt(gpuCount, 10);
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
            startSheetOpen = false;
            resetForm();
            await loadContainers();
        } catch (e) {
            startError =
                e instanceof Error ? e.message : "Failed to start container";
        } finally {
            startLoading = false;
        }
    }

    async function stopContainer(id: string) {
        actionLoading = id;
        try {
            await fetch(`${config.apiBase}/api/v1/containers/${id}`, {
                method: "DELETE",
            });
            await loadContainers();
        } catch {
            // Silently fail — next refresh will show correct state
        } finally {
            actionLoading = null;
        }
    }

    async function restartContainer(id: string) {
        actionLoading = id;
        try {
            await fetch(`${config.apiBase}/api/v1/containers/${id}/restart`, {
                method: "POST",
            });
            await loadContainers();
        } catch {
            // Silently fail
        } finally {
            actionLoading = null;
        }
    }

    async function viewLogs(container: ContainerInfo) {
        logsContainerId = container.id;
        logsContainerName = container.model_name;
        logsSheetOpen = true;
        logsLoading = true;
        logsContent = "";
        try {
            const res = await fetch(
                `${config.apiBase}/api/v1/containers/${container.id}/logs?tail=100`,
            );
            if (!res.ok) throw new Error("Failed to fetch logs");
            const data = await res.json();
            logsContent = data.logs || "(no logs)";
        } catch (e) {
            logsContent =
                e instanceof Error
                    ? `Error: ${e.message}`
                    : "Failed to load logs";
        } finally {
            logsLoading = false;
        }
    }

    function resetForm() {
        selectedModelId = "";
        selectedCapability = "chat";
        memoryLimit = "";
        cpuCount = "";
        gpuDevice = "";
        gpuCount = "";
        startError = null;
    }

    function openStartSheet() {
        resetForm();
        loadModels();
        startSheetOpen = true;
    }

    // ── Lifecycle ────────────────────────────────────────────────────

    onMount(() => {
        loadContainers();
    });

    let pollingInterval = $state<ReturnType<typeof setInterval> | null>(null);

    // Auto-poll while there are non-terminal containers
    $effect(() => {
        const hasActive = containers.some(
            (c) =>
                c.status === "starting" ||
                c.status === "stopping" ||
                c.status === "running",
        );
        if (hasActive && !pollingInterval) {
            pollingInterval = setInterval(loadContainers, 3000);
        } else if (!hasActive && pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    });

    onDestroy(() => {
        if (pollingInterval) clearInterval(pollingInterval);
    });
</script>

<svelte:head>
    <title>Containers — modelctl</title>
</svelte:head>

<div class="mx-auto flex max-w-5xl flex-col gap-6 p-6">
    <!-- ── Header ──────────────────────────────────────────── -->
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-2xl font-semibold">Containers</h1>
            <p class="text-sm text-muted-foreground">
                Manage inference containers running with llama.cpp.
            </p>
        </div>
        <div class="flex items-center gap-2">
            {#if pollingInterval}
                <Badge variant="outline" class="gap-1">
                    <Spinner class="size-3" />
                    Live
                </Badge>
            {/if}
            <Button variant="outline" onclick={loadContainers}>
                <RefreshCwIcon class="size-4" />
            </Button>
            <Button onclick={openStartSheet}>
                <PlayIcon class="size-4" />
                Start Container
            </Button>
        </div>
    </div>

    <!-- ── Loading ─────────────────────────────────────────── -->
    {#if loading}
        <div class="flex flex-col gap-3">
            {#each Array(3) as _}
                <Skeleton class="h-14 w-full" />
            {/each}
        </div>

        <!-- ── Error ───────────────────────────────────────────── -->
    {:else if error}
        <Card.Root class="border-destructive/50 bg-destructive/10">
            <Card.Content class="text-sm">{error}</Card.Content>
        </Card.Root>

        <!-- ── Empty ───────────────────────────────────────────── -->
    {:else if containers.length === 0}
        <Card.Root>
            <Card.Content
                class="flex flex-col items-center gap-2 py-10 text-center"
            >
                <BoxIcon class="size-10 text-muted-foreground/50" />
                <p class="text-sm text-muted-foreground">
                    No containers running.
                </p>
                <p class="text-xs text-muted-foreground">
                    Start a container to serve an installed model via llama.cpp.
                </p>
                <Button
                    variant="outline"
                    size="sm"
                    class="mt-2"
                    onclick={openStartSheet}
                >
                    <PlayIcon class="size-3.5" />
                    Start Container
                </Button>
            </Card.Content>
        </Card.Root>

        <!-- ── Container Table ─────────────────────────────────── -->
    {:else}
        <Card.Root>
            <Card.Content class="p-0">
                <Table.Root>
                    <Table.Header>
                        <Table.Row>
                            <Table.Head>Container</Table.Head>
                            <Table.Head>Capability</Table.Head>
                            <Table.Head>Model</Table.Head>
                            <Table.Head>Port</Table.Head>
                            <Table.Head>Status</Table.Head>
                            <Table.Head>Uptime</Table.Head>
                            <Table.Head class="text-right">Actions</Table.Head>
                        </Table.Row>
                    </Table.Header>
                    <Table.Body>
                        {#each containers as c (c.id)}
                            <Table.Row>
                                <Table.Cell>
                                    <code
                                        class="rounded border bg-muted px-1.5 py-0.5 text-xs font-mono"
                                    >
                                        {shortId(c.id)}
                                    </code>
                                </Table.Cell>
                                <Table.Cell>
                                    <span
                                        class="inline-block rounded px-2 py-0.5 text-xs font-medium {capabilityColor(
                                            c.capability,
                                        )}"
                                    >
                                        {c.capability}
                                    </span>
                                </Table.Cell>
                                <Table.Cell
                                    class="font-medium max-w-[200px] truncate"
                                    >{c.model_name}</Table.Cell
                                >
                                <Table.Cell
                                    class="tabular-nums text-muted-foreground"
                                >
                                    {c.port > 0 ? c.port : "—"}
                                </Table.Cell>
                                <Table.Cell>
                                    <Badge variant={statusVariant(c.status)}>
                                        {#if c.status === "starting" || c.status === "stopping"}
                                            <Spinner class="mr-1 size-3" />
                                        {:else if c.status === "running"}
                                            <span
                                                class="mr-1 inline-block size-2 rounded-full bg-emerald-500"
                                            ></span>
                                        {:else if c.status === "failed"}
                                            <AlertCircleIcon
                                                class="mr-1 size-3"
                                            />
                                        {/if}
                                        {c.status}
                                    </Badge>
                                </Table.Cell>
                                <Table.Cell
                                    class="tabular-nums text-muted-foreground text-sm"
                                >
                                    {formatUptime(c.uptime_seconds)}
                                </Table.Cell>
                                <Table.Cell class="text-right">
                                    <div class="flex justify-end gap-1">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onclick={() => viewLogs(c)}
                                            disabled={actionLoading === c.id}
                                        >
                                            <TerminalIcon class="size-3.5" />
                                        </Button>
                                        {#if c.status === "running"}
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onclick={() =>
                                                    restartContainer(c.id)}
                                                disabled={actionLoading ===
                                                    c.id}
                                            >
                                                {#if actionLoading === c.id}
                                                    <Spinner class="size-3.5" />
                                                {:else}
                                                    <RotateCwIcon
                                                        class="size-3.5"
                                                    />
                                                {/if}
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onclick={() =>
                                                    stopContainer(c.id)}
                                                disabled={actionLoading ===
                                                    c.id}
                                            >
                                                <SquareIcon class="size-3.5" />
                                            </Button>
                                        {/if}
                                        {#if c.status === "stopped" || c.status === "failed"}
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onclick={() =>
                                                    stopContainer(c.id)}
                                                disabled={actionLoading ===
                                                    c.id}
                                            >
                                                <SquareIcon
                                                    class="size-3.5 text-destructive"
                                                />
                                            </Button>
                                        {/if}
                                    </div>
                                </Table.Cell>
                            </Table.Row>
                        {/each}
                    </Table.Body>
                </Table.Root>
            </Card.Content>
        </Card.Root>
    {/if}
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- Start Container Sheet                                         -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<Sheet.Root bind:open={startSheetOpen}>
    <Sheet.Portal>
        <Sheet.Overlay />
        <Sheet.Content side="right" class="w-full sm:max-w-md">
            <Sheet.Header>
                <Sheet.Title>Start Container</Sheet.Title>
                <Sheet.Description>
                    Launch a new inference container for an installed model.
                </Sheet.Description>
            </Sheet.Header>

            <div class="flex flex-col gap-4 px-6 py-4">
                {#if startError}
                    <Card.Root class="border-destructive/50 bg-destructive/10">
                        <Card.Content class="flex items-start gap-2 text-sm">
                            <AlertCircleIcon
                                class="mt-0.5 size-4 shrink-0 text-destructive"
                            />
                            <span>{startError}</span>
                        </Card.Content>
                    </Card.Root>
                {/if}

                <!-- Model -->
                <div class="flex flex-col gap-1.5">
                    <label for="model" class="text-sm font-medium">
                        Model <span class="text-destructive">*</span>
                    </label>
                    {#if modelsLoading}
                        <div
                            class="flex items-center gap-2 text-sm text-muted-foreground"
                        >
                            <Spinner class="size-3" />
                            Loading models…
                        </div>
                    {:else if availableModels.length === 0}
                        <Card.Root class="border-muted">
                            <Card.Content
                                class="text-sm text-muted-foreground py-3"
                            >
                                No installed models available.
                                <a href="/search" class="underline"
                                    >Search &amp; install</a
                                > one first.
                            </Card.Content>
                        </Card.Root>
                    {:else}
                        <select
                            id="model"
                            bind:value={selectedModelId}
                            class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            <option value="" disabled>Select a model…</option>
                            {#each availableModels as m (m.id)}
                                <option value={m.id}>
                                    {m.name} ({m.type})
                                </option>
                            {/each}
                        </select>
                    {/if}
                </div>

                <!-- Capability -->
                <div class="flex flex-col gap-1.5">
                    <label for="capability" class="text-sm font-medium">
                        Capability
                    </label>
                    <select
                        id="capability"
                        bind:value={selectedCapability}
                        class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {#each capabilities as cap}
                            <option value={cap}>{cap}</option>
                        {/each}
                    </select>
                </div>

                <Separator />

                <!-- Resource Profile (optional) -->
                <p class="text-xs text-muted-foreground">
                    Resource overrides (leave blank for defaults).
                </p>

                <div class="grid grid-cols-2 gap-3">
                    <div class="flex flex-col gap-1.5">
                        <label for="memory" class="text-xs font-medium">
                            Memory
                        </label>
                        <Input
                            id="memory"
                            bind:value={memoryLimit}
                            placeholder="e.g. 8g"
                        />
                    </div>
                    <div class="flex flex-col gap-1.5">
                        <label for="cpu" class="text-xs font-medium">
                            CPU count
                        </label>
                        <Input
                            id="cpu"
                            type="number"
                            bind:value={cpuCount}
                            placeholder="e.g. 4"
                        />
                    </div>
                    <div class="flex flex-col gap-1.5">
                        <label for="gpu-device" class="text-xs font-medium">
                            GPU device
                        </label>
                        <Input
                            id="gpu-device"
                            bind:value={gpuDevice}
                            placeholder="e.g. 0"
                        />
                    </div>
                    <div class="flex flex-col gap-1.5">
                        <label for="gpu-count" class="text-xs font-medium">
                            GPU count
                        </label>
                        <Input
                            id="gpu-count"
                            type="number"
                            bind:value={gpuCount}
                            placeholder="e.g. 1"
                        />
                    </div>
                </div>
            </div>

            <Sheet.Footer class="px-6 pb-6">
                <Button
                    class="w-full"
                    onclick={startContainer}
                    disabled={!selectedModelId ||
                        startLoading ||
                        availableModels.length === 0}
                >
                    {#if startLoading}
                        <Spinner class="size-4" />
                    {:else}
                        <PlayIcon class="size-4" />
                    {/if}
                    Start Container
                </Button>
            </Sheet.Footer>
        </Sheet.Content>
    </Sheet.Portal>
</Sheet.Root>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- Logs Sheet                                                    -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<Sheet.Root bind:open={logsSheetOpen}>
    <Sheet.Portal>
        <Sheet.Overlay />
        <Sheet.Content side="right" class="w-full sm:max-w-lg">
            <Sheet.Header>
                <Sheet.Title>
                    Logs — {logsContainerName}
                </Sheet.Title>
                <Sheet.Description>
                    Container <code class="rounded border bg-muted px-1 text-xs"
                        >{shortId(logsContainerId)}</code
                    >
                </Sheet.Description>
            </Sheet.Header>

            <div class="px-6 py-4">
                {#if logsLoading}
                    <div class="flex items-center justify-center py-10">
                        <Spinner class="size-6" />
                    </div>
                {:else}
                    <pre
                        class="max-h-[60vh] overflow-auto rounded-lg bg-muted p-4 text-xs leading-relaxed font-mono whitespace-pre-wrap break-all">{logsContent}</pre>
                {/if}
            </div>

            <Sheet.Footer class="px-6 pb-6">
                <Button
                    variant="outline"
                    class="w-full"
                    onclick={() => (logsSheetOpen = false)}
                >
                    Close
                </Button>
            </Sheet.Footer>
        </Sheet.Content>
    </Sheet.Portal>
</Sheet.Root>
