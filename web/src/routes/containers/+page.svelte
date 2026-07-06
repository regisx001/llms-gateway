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
    import {
        state as ui,
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

    let pollingInterval = $state<ReturnType<typeof setInterval> | null>(null);

    onMount(() => {
        loadContainers();
    });

    // Auto-poll while there are non-terminal containers
    $effect(() => {
        const hasActive = ui.containers.some(
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
    {#if ui.loading}
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
        <Sheet.Content side="right" class="w-full sm:max-w-md">
            <Sheet.Header>
                <Sheet.Title>Start Container</Sheet.Title>
                <Sheet.Description>
                    Launch a new inference container for an installed model.
                </Sheet.Description>
            </Sheet.Header>

            <div class="flex flex-col gap-4 px-6 py-4">
                {#if ui.startError}
                    <Card.Root class="border-destructive/50 bg-destructive/10">
                        <Card.Content class="flex items-start gap-2 text-sm">
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
                        Model <span class="text-destructive">*</span>
                    </label>
                    {#if ui.modelsLoading}
                        <div
                            class="flex items-center gap-2 text-sm text-muted-foreground"
                        >
                            <Spinner class="size-3" />
                            Loading models…
                        </div>
                    {:else if ui.availableModels.length === 0}
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
                            value={ui.selectedModelId}
                            onchange={(e) =>
                                (ui.selectedModelId = (
                                    e.currentTarget as HTMLSelectElement
                                ).value)}
                            class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            <option value="" disabled>Select a model…</option>
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
                    <select
                        id="capability"
                        value={ui.selectedCapability}
                        onchange={(e) =>
                            (ui.selectedCapability = (
                                e.currentTarget as HTMLSelectElement
                            ).value)}
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
                            value={ui.memoryLimit}
                            oninput={(e) =>
                                (ui.memoryLimit = (
                                    e.currentTarget as HTMLInputElement
                                ).value)}
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
                            value={ui.cpuCount}
                            oninput={(e) =>
                                (ui.cpuCount = (
                                    e.currentTarget as HTMLInputElement
                                ).value)}
                            placeholder="e.g. 4"
                        />
                    </div>
                    <div class="flex flex-col gap-1.5">
                        <label for="gpu-device" class="text-xs font-medium">
                            GPU device
                        </label>
                        <Input
                            id="gpu-device"
                            value={ui.gpuDevice}
                            oninput={(e) =>
                                (ui.gpuDevice = (
                                    e.currentTarget as HTMLInputElement
                                ).value)}
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
                            value={ui.gpuCount}
                            oninput={(e) =>
                                (ui.gpuCount = (
                                    e.currentTarget as HTMLInputElement
                                ).value)}
                            placeholder="e.g. 1"
                        />
                    </div>
                </div>
            </div>

            <Sheet.Footer class="px-6 pb-6">
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
        <Sheet.Content side="right" class="w-full sm:max-w-lg">
            <Sheet.Header>
                <Sheet.Title>
                    Logs — {ui.logsContainerName}
                </Sheet.Title>
                <Sheet.Description>
                    Container <code class="rounded border bg-muted px-1 text-xs"
                        >{shortId(ui.logsContainerId)}</code
                    >
                </Sheet.Description>
            </Sheet.Header>

            <div class="px-6 py-4">
                {#if ui.logsLoading}
                    <div class="flex items-center justify-center py-10">
                        <Spinner class="size-6" />
                    </div>
                {:else}
                    <pre
                        class="max-h-[60vh] overflow-auto rounded-lg bg-muted p-4 text-xs leading-relaxed font-mono whitespace-pre-wrap break-all">{ui.logsContent}</pre>
                {/if}
            </div>

            <Sheet.Footer class="px-6 pb-6">
                <Button
                    variant="outline"
                    class="w-full"
                    onclick={() => (ui.logsSheetOpen = false)}
                >
                    Close
                </Button>
            </Sheet.Footer>
        </Sheet.Content>
    </Sheet.Portal>
</Sheet.Root>
