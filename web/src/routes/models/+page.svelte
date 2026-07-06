<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { config } from "$lib/config";
    import * as Card from "$lib/components/ui/card";
    import * as Table from "$lib/components/ui/table";
    import { Badge } from "$lib/components/ui/badge";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import { Skeleton } from "$lib/components/ui/skeleton";
    import { Spinner } from "$lib/components/ui/spinner";
    import { Separator } from "$lib/components/ui/separator";
    import CuboidIcon from "@lucide/svelte/icons/cuboid";
    import Trash2Icon from "@lucide/svelte/icons/trash-2";
    import SearchIcon from "@lucide/svelte/icons/search";
    import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
    import LayoutGridIcon from "@lucide/svelte/icons/layout-grid";
    import HardDriveIcon from "@lucide/svelte/icons/hard-drive";
    import TagsIcon from "@lucide/svelte/icons/tags";
    import ClockIcon from "@lucide/svelte/icons/clock";
    import FilterIcon from "@lucide/svelte/icons/filter";
    import { goto } from "$app/navigation";

    // ── State ────────────────────────────────────────────
    let models = $state<any[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let polling = $state(false);
    let pollInterval = $state<ReturnType<typeof setInterval> | null>(null);
    let searchQuery = $state("");
    let selectedType = $state("All Types");
    let downloadProgress = $state<
        Map<
            string,
            { progressPct: number; downloadedBytes: number; totalBytes: number }
        >
    >(new Map());

    // ── Derived stats ────────────────────────────────────
    let installedModels = $derived(
        models.filter((m) => m.status === "installed" || m.status === "active"),
    );

    let installedCount = $derived(installedModels.length);

    let totalSize = $derived.by(() => {
        const bytes = installedModels.reduce(
            (sum: number, m: any) =>
                sum +
                (m.artifacts?.reduce(
                    (a: number, art: any) => a + (art.size ?? 0),
                    0,
                ) ?? 0),
            0,
        );
        return sizeStr(bytes);
    });

    let modelTypesCount = $derived(
        new Set(installedModels.map((m: any) => m.type)).size,
    );

    let lastUpdated = $derived.by(() => {
        const dates = installedModels
            .map((m: any) => m.installed_at && new Date(m.installed_at))
            .filter(Boolean) as Date[];
        if (dates.length === 0) return "—";
        const latest = dates.reduce((a, b) => (a > b ? a : b));
        return latest.toLocaleDateString("en-US", {
            month: "2-digit",
            day: "2-digit",
            year: "numeric",
        });
    });

    let typeOptions = $derived<string[]>([
        "All Types",
        ...new Set(models.map((m: any) => m.type)),
    ]);

    let filteredModels = $derived(
        models.filter((m) => {
            const matchesSearch =
                !searchQuery ||
                m.name.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesType =
                selectedType === "All Types" || m.type === selectedType;
            return matchesSearch && matchesType;
        }),
    );

    // ── Utilities ────────────────────────────────────────
    function sizeStr(bytes: number): string {
        const units = ["B", "KB", "MB", "GB", "TB"];
        let n = bytes;
        for (const u of units) {
            if (n < 1024) return `${n.toFixed(1)} ${u}`;
            n /= 1024;
        }
        return `${n.toFixed(1)} PB`;
    }

    function typeColor(type: string): string {
        const colors: Record<string, string> = {
            chat: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
            embedding: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
            reranker: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
            vision: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
            experimental: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
        };
        return colors[type] ?? "bg-muted text-muted-foreground";
    }

    function formatInstalled(iso: string): string {
        const d = new Date(iso);
        return d.toLocaleDateString("en-US", {
            month: "2-digit",
            day: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    // ── Data fetching ────────────────────────────────────
    async function loadModels() {
        error = null;
        try {
            const modelRes = await fetch(`${config.apiBase}/api/v1/models`);
            if (!modelRes.ok) throw new Error("Failed to load models");
            const modelData = await modelRes.json();

            // Store raw bytes for accurate total size calculation
            models = modelData.models.map((m: any) => ({
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
            const downloadingModels = models.filter(
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
                const newProgress = new Map(downloadProgress);
                for (const r of progressResults) {
                    if (r.status === "fulfilled" && r.value) {
                        newProgress.set(r.value.id, {
                            progressPct: r.value.progress_pct,
                            downloadedBytes: r.value.downloaded_bytes,
                            totalBytes: r.value.total_bytes,
                        });
                    }
                }
                downloadProgress = newProgress;
            }

            // Start polling if any models are downloading
            const hasDownloading = models.some(
                (m: any) => m.status === "downloading",
            );
            if (hasDownloading && !polling) {
                startPolling();
            } else if (!hasDownloading && polling) {
                stopPolling();
            }
        } catch (e) {
            error = e instanceof Error ? e.message : "Failed to load models";
        } finally {
            loading = false;
        }
    }

    function startPolling() {
        polling = true;
        pollInterval = setInterval(loadModels, 2000);
    }

    function stopPolling() {
        polling = false;
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    async function postAction(path: string) {
        await fetch(`${config.apiBase}${path}`, { method: "POST" });
        await loadModels();
    }

    onMount(() => {
        loadModels();
    });

    onDestroy(() => {
        stopPolling();
    });
</script>

<svelte:head>
    <title>Models — modelctl</title>
</svelte:head>

<div class="mx-auto flex w-full flex-col gap-6 p-6">
    <!-- ── Header ─────────────────────────────────────── -->
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-2xl font-semibold">Models</h1>
            <p class="text-sm text-muted-foreground">
                Manage installed models in the registry.
            </p>
        </div>
        <div class="flex items-center gap-2">
            {#if polling}
                <Badge variant="outline" class="gap-1">
                    <Spinner class="size-3" />
                    Updating...
                </Badge>
            {/if}
            <Button variant="outline" size="icon" onclick={loadModels}>
                <RefreshCwIcon class="size-4" />
            </Button>
        </div>
    </div>

    {#if loading}
        <div class="flex flex-col gap-4">
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {#each Array(4) as _}
                    <Skeleton class="h-24 w-full" />
                {/each}
            </div>
            <Skeleton class="h-64 w-full" />
        </div>
    {:else if error}
        <Card.Root class="border-destructive/50 bg-destructive/10">
            <Card.Content class="text-sm">{error}</Card.Content>
        </Card.Root>
    {:else}
        <!-- ── Stat Cards ──────────────────────────────── -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <!-- Installed Models -->
            <Card.Root size="sm">
                <Card.Header
                    class="flex-row items-center justify-between gap-3"
                >
                    <div>
                        <Card.Description>Installed Models</Card.Description>
                        <Card.Title class="mt-1 text-2xl tabular-nums">
                            {installedCount}
                        </Card.Title>
                    </div>
                    <div
                        class="flex size-10 items-center justify-center rounded-lg bg-primary/10"
                    >
                        <CuboidIcon class="size-5 text-primary" />
                    </div>
                </Card.Header>
            </Card.Root>

            <!-- Total Size -->
            <Card.Root size="sm">
                <Card.Header
                    class="flex-row items-center justify-between gap-3"
                >
                    <div>
                        <Card.Description>Total Size</Card.Description>
                        <Card.Title class="mt-1 text-2xl tabular-nums">
                            {totalSize}
                        </Card.Title>
                    </div>
                    <div
                        class="flex size-10 items-center justify-center rounded-lg bg-primary/10"
                    >
                        <HardDriveIcon class="size-5 text-primary" />
                    </div>
                </Card.Header>
            </Card.Root>

            <!-- Model Types -->
            <Card.Root size="sm">
                <Card.Header
                    class="flex-row items-center justify-between gap-3"
                >
                    <div>
                        <Card.Description>Model Types</Card.Description>
                        <Card.Title class="mt-1 text-2xl tabular-nums">
                            {modelTypesCount}
                        </Card.Title>
                    </div>
                    <div
                        class="flex size-10 items-center justify-center rounded-lg bg-primary/10"
                    >
                        <TagsIcon class="size-5 text-primary" />
                    </div>
                </Card.Header>
            </Card.Root>

            <!-- Last Updated -->
            <Card.Root size="sm">
                <Card.Header
                    class="flex-row items-center justify-between gap-3"
                >
                    <div>
                        <Card.Description>Last Updated</Card.Description>
                        <Card.Title class="mt-1 text-2xl tabular-nums">
                            {lastUpdated}
                        </Card.Title>
                    </div>
                    <div
                        class="flex size-10 items-center justify-center rounded-lg bg-primary/10"
                    >
                        <ClockIcon class="size-5 text-primary" />
                    </div>
                </Card.Header>
            </Card.Root>
        </div>

        <!-- ── Search & Filter ─────────────────────────── -->
        <div class="flex items-center gap-3">
            <div class="relative flex-1">
                <SearchIcon
                    class="text-muted-foreground/50 absolute left-3 top-1/2 size-4 -translate-y-1/2"
                />
                <Input
                    type="search"
                    placeholder="Search installed models..."
                    class="pl-9"
                    bind:value={searchQuery}
                />
            </div>
            <div class="relative">
                <FilterIcon
                    class="text-muted-foreground/50 absolute left-3 top-1/2 z-10 size-4 -translate-y-1/2"
                />
                <select
                    bind:value={selectedType}
                    class="border-input bg-background text-foreground focus-visible:border-ring focus-visible:ring-ring/50 h-9 min-w-35 appearance-none rounded-md border pl-9 pr-8 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:ring-3"
                >
                    {#each typeOptions as opt}
                        <option value={opt}>{opt}</option>
                    {/each}
                </select>
                <svg
                    class="text-muted-foreground/50 absolute right-3 top-1/2 size-4 -translate-y-1/2"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                >
                    <path d="m6 9 6 6 6-6" />
                </svg>
            </div>
        </div>

        <!-- ── Models Table ────────────────────────────── -->
        {#if filteredModels.length === 0}
            <Card.Root>
                <Card.Content
                    class="flex flex-col items-center gap-2 py-10 text-center"
                >
                    <CuboidIcon class="size-10 text-muted-foreground/50" />
                    <p class="text-sm text-muted-foreground">
                        {#if searchQuery || selectedType !== "All Types"}
                            No models match your search.
                        {:else}
                            No models installed yet.
                        {/if}
                    </p>
                    <p class="text-xs text-muted-foreground">
                        {#if searchQuery || selectedType !== "All Types"}
                            Try adjusting your search or filter.
                        {:else}
                            Go to the Search page to find and install models
                            from HuggingFace.
                        {/if}
                    </p>
                    {#if !searchQuery && selectedType === "All Types"}
                        <Button
                            variant="outline"
                            size="sm"
                            class="mt-2"
                            onclick={() => goto("/search")}
                        >
                            <SearchIcon class="size-3.5" />
                            Search Models
                        </Button>
                    {/if}
                </Card.Content>
            </Card.Root>
        {:else}
            <Card.Root>
                <Card.Content class="p-0">
                    <Table.Root>
                        <Table.Header>
                            <Table.Row>
                                <Table.Head>Name</Table.Head>
                                <Table.Head>Type</Table.Head>
                                <Table.Head>Size</Table.Head>
                                <Table.Head>Installed On</Table.Head>
                                <Table.Head>Status</Table.Head>
                                <Table.Head class="text-right"
                                    >Actions</Table.Head
                                >
                            </Table.Row>
                        </Table.Header>
                        <Table.Body>
                            {#each filteredModels as m (m.id)}
                                <Table.Row>
                                    <Table.Cell
                                        class="font-medium max-w-70 truncate"
                                        >{m.name}</Table.Cell
                                    >
                                    <Table.Cell>
                                        <span
                                            class="inline-block rounded-md px-2.5 py-1 text-xs font-medium capitalize {typeColor(
                                                m.type,
                                            )}"
                                        >
                                            {m.type}
                                        </span>
                                    </Table.Cell>
                                    <Table.Cell
                                        class="tabular-nums text-muted-foreground"
                                        >{m.size}</Table.Cell
                                    >
                                    <Table.Cell
                                        class="tabular-nums text-muted-foreground"
                                    >
                                        {#if m.installed_at}
                                            {formatInstalled(m.installed_at)}
                                        {:else}
                                            —
                                        {/if}
                                    </Table.Cell>
                                    <Table.Cell>
                                        {#if m.status === "installed" || m.status === "active"}
                                            <span
                                                class="inline-flex items-center gap-1.5"
                                            >
                                                <span
                                                    class="relative flex size-2"
                                                >
                                                    <span
                                                        class="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75"
                                                    ></span>
                                                    <span
                                                        class="relative inline-flex size-2 rounded-full bg-emerald-500"
                                                    ></span>
                                                </span>
                                                <span
                                                    class="text-sm font-medium text-emerald-500"
                                                >
                                                    {m.status === "active"
                                                        ? "Active"
                                                        : "Installed"}
                                                </span>
                                            </span>
                                        {:else if m.status === "downloading"}
                                            {@const prog = downloadProgress.get(
                                                m.id,
                                            )}
                                            <div class="flex flex-col gap-1">
                                                <span
                                                    class="inline-flex items-center gap-1 text-sm text-muted-foreground"
                                                >
                                                    <Spinner class="size-3" />
                                                    Downloading
                                                </span>
                                                {#if prog}
                                                    <div
                                                        class="flex items-center gap-2"
                                                    >
                                                        <div
                                                            class="h-1.5 w-20 overflow-hidden rounded-full bg-muted"
                                                        >
                                                            <div
                                                                class="h-full rounded-full bg-primary transition-all duration-500"
                                                                style="width: {prog.progressPct}%"
                                                            ></div>
                                                        </div>
                                                        <span
                                                            class="text-[11px] tabular-nums text-muted-foreground"
                                                        >
                                                            {prog.progressPct}%
                                                        </span>
                                                    </div>
                                                {/if}
                                            </div>
                                        {:else if m.status === "error"}
                                            <Badge variant="destructive"
                                                >Error</Badge
                                            >
                                        {:else}
                                            <Badge variant="outline"
                                                >{m.status}</Badge
                                            >
                                        {/if}
                                    </Table.Cell>
                                    <Table.Cell class="text-right">
                                        <div class="flex justify-end gap-1">
                                            {#if m.status !== "downloading"}
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onclick={() =>
                                                        postAction(
                                                            `/api/v1/models/${m.id}/remove`,
                                                        )}
                                                >
                                                    <Trash2Icon
                                                        class="size-3.5"
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

            <!-- ── Installation Log ─────────────────────── -->
            {#if models.some((m: any) => m.installed_at)}
                <div
                    class="flex items-center gap-2 text-xs text-muted-foreground"
                >
                    <ClockIcon class="size-3 shrink-0" />
                    <span>
                        {#each models.filter((m: any) => m.installed_at) as m, i}
                            {m.name} installed {new Date(
                                m.installed_at,
                            ).toLocaleDateString("en-US", {
                                month: "2-digit",
                                day: "2-digit",
                                year: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                            })}
                            {#if i < models.filter((mm: any) => mm.installed_at).length - 1}
                                <span class="mx-1 text-muted-foreground/40"
                                    >&middot;</span
                                >
                            {/if}
                        {/each}
                    </span>
                </div>
            {/if}
        {/if}
    {/if}
</div>
