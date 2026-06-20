<script lang="ts">
    import { onMount } from "svelte";
    import { config } from "$lib/config";
    import * as Card from "$lib/components/ui/card";
    import { Badge } from "$lib/components/ui/badge";
    import { Button } from "$lib/components/ui/button";
    import { Skeleton } from "$lib/components/ui/skeleton";
    import { Separator } from "$lib/components/ui/separator";
    import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
    import ActivityIcon from "@lucide/svelte/icons/activity";
    import DatabaseIcon from "@lucide/svelte/icons/database";
    import CpuIcon from "@lucide/svelte/icons/cpu";
    import CuboidIcon from "@lucide/svelte/icons/cuboid";
    import TagIcon from "@lucide/svelte/icons/tag";

    let loading = $state(true);
    let error = $state<string | null>(null);
    let health = $state<{ status: string; version: string } | null>(null);
    let info = $state<{
        version: string;
        storage_used: string;
        storage_free: string;
        models_count: number;
        active_models: string[];
    } | null>(null);

    async function loadData() {
        loading = true;
        error = null;
        try {
            const [healthRes, infoRes] = await Promise.all([
                fetch(`${config.apiBase}/health`),
                fetch(`${config.apiBase}/api/v1/system/info`),
            ]);
            if (!healthRes.ok || !infoRes.ok)
                throw new Error("Failed to fetch system info");
            health = await healthRes.json();
            info = await infoRes.json();
        } catch (e) {
            error =
                e instanceof Error ? e.message : "Failed to load system info";
        } finally {
            loading = false;
        }
    }

    onMount(loadData);
</script>

<svelte:head>
    <title>System — modelctl</title>
</svelte:head>

<div class="mx-auto flex max-w-3xl flex-col gap-6 p-6">
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-2xl font-semibold">System</h1>
            <p class="text-sm text-muted-foreground">
                System information and health status.
            </p>
        </div>
        <Button variant="outline" size="icon" onclick={loadData}>
            <RefreshCwIcon class="size-4" />
        </Button>
    </div>

    {#if loading}
        <div class="grid grid-cols-2 gap-4">
            {#each Array(4) as _}
                <Skeleton class="h-24 w-full" />
            {/each}
        </div>
    {:else if error}
        <Card.Root class="border-destructive/50 bg-destructive/10">
            <Card.Content class="text-sm">{error}</Card.Content>
        </Card.Root>
    {:else}
        <div class="grid grid-cols-2 gap-4">
            <Card.Root>
                <Card.Header>
                    <Card.Description class="flex items-center gap-2 text-sm">
                        <ActivityIcon class="size-4" />
                        API Status
                    </Card.Description>
                    <Card.Title class="flex items-center gap-2 text-lg">
                        {#if health?.status === "ok"}
                            <span class="relative flex size-2">
                                <span
                                    class="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75"
                                ></span>
                                <span
                                    class="relative inline-flex size-2 rounded-full bg-emerald-500"
                                ></span>
                            </span>
                            Online
                        {:else}
                            <span class="size-2 rounded-full bg-destructive"
                            ></span>
                            Offline
                        {/if}
                    </Card.Title>
                </Card.Header>
            </Card.Root>

            <Card.Root>
                <Card.Header>
                    <Card.Description class="flex items-center gap-2 text-sm">
                        <TagIcon class="size-4" />
                        Version
                    </Card.Description>
                    <Card.Title class="text-lg tabular-nums">
                        {health?.version ?? "—"}
                    </Card.Title>
                </Card.Header>
            </Card.Root>

            <Card.Root>
                <Card.Header>
                    <Card.Description class="flex items-center gap-2 text-sm">
                        <DatabaseIcon class="size-4" />
                        Storage
                    </Card.Description>
                    <Card.Title class="text-lg tabular-nums">
                        {info?.storage_used ?? "?"}
                        <span class="text-sm font-normal text-muted-foreground">
                            / {info?.storage_free ?? "?"}
                        </span>
                    </Card.Title>
                </Card.Header>
            </Card.Root>

            <Card.Root>
                <Card.Header>
                    <Card.Description class="flex items-center gap-2 text-sm">
                        <CuboidIcon class="size-4" />
                        Models
                    </Card.Description>
                    <Card.Title class="text-lg tabular-nums">
                        {info?.models_count ?? "?"}
                    </Card.Title>
                </Card.Header>
            </Card.Root>
        </div>

        <Card.Root>
            <Card.Header>
                <Card.Title class="text-base">Active Model</Card.Title>
            </Card.Header>
            <Card.Content>
                {#if info?.active_models?.length}
                    <div class="flex items-center gap-2">
                        <CpuIcon class="size-4 text-muted-foreground" />
                        <code
                            class="rounded border bg-muted px-2 py-0.5 text-sm"
                        >
                            {info.active_models[0]}
                        </code>
                    </div>
                {:else}
                    <p class="text-sm text-muted-foreground">No active model</p>
                {/if}
            </Card.Content>
        </Card.Root>
    {/if}
</div>
