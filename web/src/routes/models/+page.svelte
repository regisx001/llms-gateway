<script lang="ts">
    import { onMount } from "svelte";
    import { config } from "$lib/config";
    import * as Card from "$lib/components/ui/card";
    import * as Table from "$lib/components/ui/table";
    import { Badge } from "$lib/components/ui/badge";
    import { Button } from "$lib/components/ui/button";
    import { Skeleton } from "$lib/components/ui/skeleton";
    import { Spinner } from "$lib/components/ui/spinner";
    import CuboidIcon from "@lucide/svelte/icons/cuboid";
    import PlayIcon from "@lucide/svelte/icons/play";
    import SquareIcon from "@lucide/svelte/icons/square";
    import Trash2Icon from "@lucide/svelte/icons/trash-2";

    let models = $state<any[]>([]);
    let activeModelId = $state<string | null>(null);
    let loading = $state(true);
    let error = $state<string | null>(null);

    function sizeStr(bytes: number): string {
        const units = ["B", "KB", "MB", "GB", "TB"];
        let n = bytes;
        for (const u of units) {
            if (n < 1024) return `${n.toFixed(1)} ${u}`;
            n /= 1024;
        }
        return `${n.toFixed(1)} PB`;
    }

    async function loadModels() {
        loading = true;
        error = null;
        try {
            const [modelRes, infoRes] = await Promise.all([
                fetch(`${config.apiBase}/api/v1/models`),
                fetch(`${config.apiBase}/api/v1/system/info`),
            ]);
            if (!modelRes.ok) throw new Error("Failed to load models");
            const modelData = await modelRes.json();
            if (infoRes.ok) {
                const info = await infoRes.json();
                activeModelId = info.active_models?.[0] ?? null;
            }
            models = modelData.models.map((m: any) => ({
                ...m,
                size: sizeStr(
                    m.artifacts?.reduce(
                        (a: number, art: any) => a + (art.size ?? 0),
                        0,
                    ) ?? 0,
                ),
            }));
        } catch (e) {
            error = e instanceof Error ? e.message : "Failed to load models";
        } finally {
            loading = false;
        }
    }

    async function postAction(path: string) {
        await fetch(`${config.apiBase}${path}`, { method: "POST" });
        await loadModels();
    }

    onMount(loadModels);
</script>

<svelte:head>
    <title>Models — modelctl</title>
</svelte:head>

<div class="mx-auto flex max-w-5xl flex-col gap-6 p-6">
    <div class="flex items-center justify-between">
        <div>
            <h1 class="text-2xl font-semibold">Models</h1>
            <p class="text-sm text-muted-foreground">
                Manage installed models in the registry.
            </p>
        </div>
        <Button variant="outline" onclick={loadModels}>Refresh</Button>
    </div>

    {#if loading}
        <div class="flex flex-col gap-3">
            {#each Array(3) as _}
                <Skeleton class="h-12 w-full" />
            {/each}
        </div>
    {:else if error}
        <Card.Root class="border-destructive/50 bg-destructive/10">
            <Card.Content class="text-sm">{error}</Card.Content>
        </Card.Root>
    {:else if models.length === 0}
        <Card.Root>
            <Card.Content
                class="flex flex-col items-center gap-2 py-10 text-center"
            >
                <CuboidIcon class="size-10 text-muted-foreground/50" />
                <p class="text-sm text-muted-foreground">
                    No models installed yet.
                </p>
                <p class="text-xs text-muted-foreground">
                    Go to the Search page to find and install models from
                    HuggingFace.
                </p>
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
                            <Table.Head>Status</Table.Head>
                            <Table.Head class="text-right">Actions</Table.Head>
                        </Table.Row>
                    </Table.Header>
                    <Table.Body>
                        {#each models as m (m.id)}
                            <Table.Row>
                                <Table.Cell class="font-medium"
                                    >{m.name}</Table.Cell
                                >
                                <Table.Cell
                                    class="capitalize text-muted-foreground"
                                    >{m.type}</Table.Cell
                                >
                                <Table.Cell
                                    class="tabular-nums text-muted-foreground"
                                    >{m.size}</Table.Cell
                                >
                                <Table.Cell>
                                    {#if m.status === "installed"}
                                        <Badge variant="secondary"
                                            >Installed</Badge
                                        >
                                    {:else if m.status === "active"}
                                        <Badge>Active</Badge>
                                    {:else if m.status === "downloading"}
                                        <Badge variant="outline" class="gap-1">
                                            <Spinner class="size-3" />
                                            Downloading
                                        </Badge>
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
                                        {#if m.status === "installed"}
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onclick={() =>
                                                    postAction(
                                                        `/api/v1/models/${m.id}/activate`,
                                                    )}
                                            >
                                                <PlayIcon class="size-3.5" />
                                                Activate
                                            </Button>
                                        {/if}
                                        {#if activeModelId === m.id}
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onclick={() =>
                                                    postAction(
                                                        `/api/v1/models/${m.id}/deactivate`,
                                                    )}
                                            >
                                                <SquareIcon class="size-3.5" />
                                                Stop
                                            </Button>
                                        {/if}
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onclick={() =>
                                                postAction(
                                                    `/api/v1/models/${m.id}/remove`,
                                                )}
                                        >
                                            <Trash2Icon class="size-3.5" />
                                        </Button>
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
