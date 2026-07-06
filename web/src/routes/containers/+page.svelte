<script lang="ts">
    import { onMount, onDestroy } from "svelte";
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
    import ActivityIcon from "@lucide/svelte/icons/activity";
    import {
        ui,
        capabilities,
        loadContainers,
        startContainer,
        stopContainer,
        restartContainer,
        viewLogs,
        openStartSheet,
        shortId,
        formatUptime,
        statusVariant,
        capabilityColor,
    } from "./containers.svelte";

    // ── Derived ──────────────────────────────────────────────────────

    let runningCount = $derived(
        ui.containers.filter((c) => c.status === "running").length,
    );
    let stoppedCount = $derived(
        ui.containers.filter(
            (c) => c.status === "stopped" || c.status === "failed",
        ).length,
    );
    let totalCount = $derived(ui.containers.length);

    let isPolling = $derived(
        ui.containers.some(
            (c) =>
                c.status === "starting" ||
                c.status === "stopping" ||
                c.status === "running",
        ),
    );

    let pollingInterval = $state<ReturnType<typeof setInterval> | null>(null);

    onMount(() => {
        loadContainers();
    });

    // Auto-poll while there are non-terminal containers
    $effect(() => {
        if (isPolling && !pollingInterval) {
            pollingInterval = setInterval(loadContainers, 3000);
        } else if (!isPolling && pollingInterval) {
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
    <meta
        name="description"
        content="Manage llama.cpp inference containers — start, stop, restart, and view container logs."
    />
    <meta
        name="keywords"
        content="modelctl, containers, llama.cpp, inference, Docker, model serving"
    />
    <meta property="og:title" content="Containers — modelctl" />
    <meta
        property="og:description"
        content="Manage llama.cpp inference containers — start, stop, restart, and view container logs."
    />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="Containers — modelctl" />
    <meta
        name="twitter:description"
        content="Manage llama.cpp inference containers — start, stop, restart, and view container logs."
    />
</svelte:head>

<div class="mx-auto flex w-full flex-col gap-6 p-6">
    <!-- ── Header ──────────────────────────────────────────── -->
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-2xl font-semibold">Containers</h1>
            <p class="text-sm text-muted-foreground">
                Manage inference containers running with llama.cpp.
            </p>
        </div>
        <div class="flex items-center gap-2">
            {#if isPolling}
                <Badge variant="outline" class="gap-1">
                    <Spinner class="size-3" />
                    Live
                </Badge>
            {/if}
            <Button variant="outline" size="icon" onclick={loadContainers}>
                <RefreshCwIcon class="size-4" />
            </Button>
            <Button onclick={openStartSheet}>
                <PlayIcon class="size-4" />
                Start Container
            </Button>
        </div>
    </div>

    <!-- ── Loading ─────────────────────────────────────────── -->
    {#if ui.loading}
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {#each Array(3) as _}
                <Card.Root size="sm">
                    <Card.Header>
                        <Skeleton class="mb-2 h-4 w-20" />
                        <Skeleton class="h-8 w-16" />
                    </Card.Header>
                </Card.Root>
            {/each}
        </div>
        <div class="flex flex-col gap-3">
            {#each Array(3) as _}
                <Skeleton class="h-14 w-full" />
            {/each}
        </div>

        <!-- ── Error ───────────────────────────────────────────── -->
    {:else if ui.error}
        <Card.Root class="border-destructive/50 bg-destructive/10">
            <Card.Content class="text-sm">{ui.error}</Card.Content>
        </Card.Root>

        <!-- ── Empty ───────────────────────────────────────────── -->
    {:else if ui.containers.length === 0}
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
        <!-- ── Stat Cards ──────────────────────────────────── -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card.Root size="sm">
                <Card.Header
                    class="flex-row items-center justify-between gap-3"
                >
                    <div>
                        <Card.Description>Running</Card.Description>
                        <Card.Title class="mt-1 text-2xl tabular-nums">
                            {runningCount}
                        </Card.Title>
                    </div>
                    <div
                        class="flex size-10 items-center justify-center rounded-lg bg-emerald-500/15"
                    >
                        <ActivityIcon
                            class="size-5 text-emerald-600 dark:text-emerald-400"
                        />
                    </div>
                </Card.Header>
            </Card.Root>

            <Card.Root size="sm">
                <Card.Header
                    class="flex-row items-center justify-between gap-3"
                >
                    <div>
                        <Card.Description>Stopped</Card.Description>
                        <Card.Title class="mt-1 text-2xl tabular-nums">
                            {stoppedCount}
                        </Card.Title>
                    </div>
                    <div
                        class="flex size-10 items-center justify-center rounded-lg bg-muted"
                    >
                        <SquareIcon class="size-5 text-muted-foreground" />
                    </div>
                </Card.Header>
            </Card.Root>

            <Card.Root size="sm">
                <Card.Header
                    class="flex-row items-center justify-between gap-3"
                >
                    <div>
                        <Card.Description>Total</Card.Description>
                        <Card.Title class="mt-1 text-2xl tabular-nums">
                            {totalCount}
                        </Card.Title>
                    </div>
                    <div
                        class="flex size-10 items-center justify-center rounded-lg bg-primary/10"
                    >
                        <BoxIcon class="size-5 text-primary" />
                    </div>
                </Card.Header>
            </Card.Root>
        </div>

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
                        {#each ui.containers as c (c.id)}
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
                                        class="inline-block rounded-md px-2.5 py-1 text-xs font-medium {capabilityColor(
                                            c.capability,
                                        )}"
                                    >
                                        {c.capability}
                                    </span>
                                </Table.Cell>
                                <Table.Cell
                                    class="font-medium max-w-50 truncate"
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
                                            disabled={ui.actionLoading === c.id}
                                        >
                                            <TerminalIcon class="size-3.5" />
                                        </Button>
                                        {#if c.status === "running"}
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onclick={() =>
                                                    restartContainer(c.id)}
                                                disabled={ui.actionLoading ===
                                                    c.id}
                                            >
                                                {#if ui.actionLoading === c.id}
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
                                                disabled={ui.actionLoading ===
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
                                                disabled={ui.actionLoading ===
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
<Sheet.Root
    open={ui.startSheetOpen}
    onOpenChange={(o) => (ui.startSheetOpen = o)}
>
    <Sheet.Portal>
        <Sheet.Overlay />
        <Sheet.Content side="right" class="w-full sm:max-w-2xl! p-0">
            <div class="flex h-full flex-col">
                <div
                    class="flex items-start justify-between gap-3 border-b px-6 py-4"
                >
                    <div>
                        <Sheet.Title class="text-lg font-semibold">
                            Start Container
                        </Sheet.Title>
                        <Sheet.Description class="text-xs">
                            Launch a new inference container for an installed
                            model.
                        </Sheet.Description>
                    </div>
                </div>

                <div class="flex-1 overflow-y-auto px-6 py-4">
                    <div class="flex flex-col gap-5">
                        {#if ui.startError}
                            <Card.Root
                                class="border-destructive/50 bg-destructive/10"
                            >
                                <Card.Content
                                    class="flex items-start gap-2 py-3 text-sm"
                                >
                                    <AlertCircleIcon
                                        class="mt-0.5 size-4 shrink-0 text-destructive"
                                    />
                                    <span>{ui.startError}</span>
                                </Card.Content>
                            </Card.Root>
                        {/if}

                        <!-- Model -->
                        <div class="flex flex-col gap-1.5">
                            <label for="model" class="text-sm font-medium">
                                Model
                                <span class="text-destructive">*</span>
                            </label>
                            {#if ui.modelsLoading}
                                <div
                                    class="flex items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2 text-sm text-muted-foreground"
                                >
                                    <Spinner class="size-3" />
                                    Loading models…
                                </div>
                            {:else if ui.availableModels.length === 0}
                                <div
                                    class="rounded-lg border border-dashed bg-muted/20 px-3 py-3 text-sm text-muted-foreground"
                                >
                                    No installed models available.
                                    <a href="/search" class="underline"
                                        >Search &amp; install</a
                                    >
                                    one first.
                                </div>
                            {:else}
                                <select
                                    id="model"
                                    bind:value={ui.selectedModelId}
                                    class="border-input bg-background text-foreground focus-visible:border-ring focus-visible:ring-ring/50 h-9 w-full rounded-md border px-3 py-1 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:ring-3"
                                >
                                    <option value="" disabled
                                        >Select a model…</option
                                    >
                                    {#each ui.availableModels as m (m.id)}
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
                            <div class="flex gap-2">
                                {#each capabilities as cap}
                                    <button
                                        type="button"
                                        onclick={() =>
                                            (ui.selectedCapability = cap)}
                                        class="cursor-pointer rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-all {ui.selectedCapability ===
                                        cap
                                            ? capabilityColor(cap) +
                                              ' ring-1 ring-sidebar-ring'
                                            : 'bg-muted/50 text-muted-foreground hover:bg-muted'}"
                                    >
                                        {cap}
                                    </button>
                                {/each}
                            </div>
                        </div>

                        <Separator />

                        <!-- Resource Profile (optional) -->
                        <div>
                            <p
                                class="mb-3 text-xs font-medium text-muted-foreground"
                            >
                                Resource overrides
                                <span
                                    class="font-normal text-muted-foreground/60"
                                    >(leave blank for defaults)</span
                                >
                            </p>

                            <div class="grid grid-cols-2 gap-3">
                                <div class="flex flex-col gap-1.5">
                                    <label
                                        for="memory"
                                        class="text-xs font-medium"
                                    >
                                        Memory
                                    </label>
                                    <Input
                                        id="memory"
                                        bind:value={ui.memoryLimit}
                                        placeholder="e.g. 8g"
                                        class="h-9"
                                    />
                                </div>
                                <div class="flex flex-col gap-1.5">
                                    <label
                                        for="cpu"
                                        class="text-xs font-medium"
                                    >
                                        CPU count
                                    </label>
                                    <Input
                                        id="cpu"
                                        type="number"
                                        bind:value={ui.cpuCount}
                                        placeholder="e.g. 4"
                                        class="h-9"
                                    />
                                </div>
                                <div class="flex flex-col gap-1.5">
                                    <label
                                        for="gpu-device"
                                        class="text-xs font-medium"
                                    >
                                        GPU device
                                    </label>
                                    <Input
                                        id="gpu-device"
                                        bind:value={ui.gpuDevice}
                                        placeholder="e.g. 0"
                                        class="h-9"
                                    />
                                </div>
                                <div class="flex flex-col gap-1.5">
                                    <label
                                        for="gpu-count"
                                        class="text-xs font-medium"
                                    >
                                        GPU count
                                    </label>
                                    <Input
                                        id="gpu-count"
                                        type="number"
                                        bind:value={ui.gpuCount}
                                        placeholder="e.g. 1"
                                        class="h-9"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <Sheet.Footer class="border-t px-6 py-4">
                    <Button
                        class="w-full"
                        onclick={startContainer}
                        disabled={!ui.selectedModelId ||
                            ui.startLoading ||
                            ui.availableModels.length === 0}
                    >
                        {#if ui.startLoading}
                            <Spinner class="size-4" />
                        {:else}
                            <PlayIcon class="size-4" />
                        {/if}
                        Start Container
                    </Button>
                </Sheet.Footer>
            </div>
        </Sheet.Content>
    </Sheet.Portal>
</Sheet.Root>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- Logs Sheet                                                    -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<Sheet.Root
    open={ui.logsSheetOpen}
    onOpenChange={(o) => (ui.logsSheetOpen = o)}
>
    <Sheet.Portal>
        <Sheet.Overlay />
        <Sheet.Content side="right" class="w-full sm:max-w-2xl! p-0">
            <div class="flex h-full flex-col">
                <div
                    class="flex items-start justify-between gap-3 border-b px-6 py-4"
                >
                    <div class="min-w-0 flex-1">
                        <Sheet.Title class="truncate text-lg font-semibold">
                            Logs — {ui.logsContainerName}
                        </Sheet.Title>
                        <Sheet.Description
                            class="flex items-center gap-1.5 text-xs"
                        >
                            Container
                            <code
                                class="rounded border bg-muted px-1.5 py-0.5 text-[10px] font-mono"
                            >
                                {shortId(ui.logsContainerId)}
                            </code>
                            {#if ui.logsContent}
                                <span class="text-muted-foreground/50"
                                    >&middot;</span
                                >
                                <span class="tabular-nums">
                                    {ui.logsContent.split("\n").length} lines
                                </span>
                            {/if}
                        </Sheet.Description>
                    </div>
                </div>

                <div class="flex-1 overflow-y-auto px-6 py-4">
                    {#if ui.logsLoading}
                        <div class="flex flex-col gap-3">
                            <Skeleton class="h-4 w-full" />
                            <Skeleton class="h-4 w-11/12" />
                            <Skeleton class="h-4 w-4/5" />
                            <Skeleton class="h-4 w-3/4" />
                            <Skeleton class="h-4 w-5/6" />
                        </div>
                    {:else if !ui.logsContent}
                        <div
                            class="flex flex-col items-center gap-2 py-10 text-center"
                        >
                            <TerminalIcon
                                class="size-8 text-muted-foreground/40"
                            />
                            <p class="text-sm text-muted-foreground">
                                No logs available.
                            </p>
                        </div>
                    {:else}
                        <div
                            class="max-h-[65vh] overflow-auto rounded-lg border bg-muted/30 p-0"
                        >
                            {#each ui.logsContent.split("\n") as line, i}
                                <div
                                    class="flex border-b border-muted/50 last:border-b-0 hover:bg-muted/40"
                                >
                                    <span
                                        class="min-w-12 select-none border-r border-muted/50 px-2 py-0.5 text-[10px] leading-relaxed text-muted-foreground/40 tabular-nums text-right"
                                    >
                                        {i + 1}
                                    </span>
                                    <span
                                        class="flex-1 px-2 py-0.5 text-xs leading-relaxed font-mono whitespace-pre-wrap break-all text-foreground/80"
                                    >
                                        {line || String.fromCharCode(160)}
                                    </span>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>

                <Sheet.Footer class="border-t px-6 py-4">
                    <Button
                        variant="outline"
                        class="w-full"
                        onclick={() => (ui.logsSheetOpen = false)}
                    >
                        Close
                    </Button>
                </Sheet.Footer>
            </div>
        </Sheet.Content>
    </Sheet.Portal>
</Sheet.Root>
