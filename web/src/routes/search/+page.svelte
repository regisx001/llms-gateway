<script lang="ts">
    import { page } from "$app/state";
    import { config } from "$lib/config";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import * as Card from "$lib/components/ui/card";
    import * as Table from "$lib/components/ui/table";
    import { Spinner } from "$lib/components/ui/spinner";
    import { Skeleton } from "$lib/components/ui/skeleton";
    import SearchIcon from "@lucide/svelte/icons/search";
    import DownloadIcon from "@lucide/svelte/icons/download";
    import ThumbsUpIcon from "@lucide/svelte/icons/thumbs-up";

    import InspectSheet from "$lib/components/search/inspect-sheet.svelte";

    let query = $state(page.url.searchParams.get("q") || "");
    let results = $state<any[] | null>(null);
    let loading = $state(false);
    let error = $state<string | null>(null);

    // Inspect sheet state
    let sheetOpen = $state(false);
    let inspectRepoId = $state("");

    function typeColor(type: string): string {
        const colors: Record<string, string> = {
            chat: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
            embedding: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
            reranker: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
            vision: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
        };
        return colors[type] ?? "bg-muted text-muted-foreground";
    }

    function handleInspect(repoId: string) {
        inspectRepoId = repoId;
        sheetOpen = true;
    }

    async function doSearch() {
        if (!query.trim()) return;
        loading = true;
        error = null;
        try {
            const res = await fetch(
                `${config.apiBase}/api/v1/search?q=${encodeURIComponent(query.trim())}&limit=20`,
            );
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();
            results = data.results ?? [];
        } catch (e) {
            error = e instanceof Error ? e.message : "Search failed";
            results = null;
        } finally {
            loading = false;
        }
    }
</script>

<svelte:head>
    <title>Search — modelctl</title>
</svelte:head>

<div class="mx-auto flex w-full flex-col gap-6 p-6">
    <!-- ── Header ─────────────────────────────────────── -->
    <div>
        <h1 class="text-2xl font-semibold">Search HuggingFace</h1>
        <p class="text-sm text-muted-foreground">
            Find and install GGUF models from the HuggingFace Hub.
        </p>
    </div>

    <!-- ── Search Form ────────────────────────────────── -->
    <Card.Root size="sm">
        <Card.Content>
            <form
                class="flex gap-3"
                onsubmit={(e) => {
                    e.preventDefault();
                    doSearch();
                }}
            >
                <div class="relative flex-1">
                    <SearchIcon
                        class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground/50"
                    />
                    <Input
                        bind:value={query}
                        placeholder="e.g. gemma, llama, nomic-embed…"
                        class="pl-9"
                    />
                </div>
                <Button type="submit" disabled={loading || !query.trim()}>
                    {#if loading}
                        <Spinner class="size-4" />
                    {:else}
                        <SearchIcon class="size-4" />
                    {/if}
                    Search
                </Button>
            </form>
        </Card.Content>
    </Card.Root>

    {#if error}
        <Card.Root class="border-destructive/50 bg-destructive/10">
            <Card.Content class="text-sm">{error}</Card.Content>
        </Card.Root>
    {/if}

    {#if loading}
        <div class="flex flex-col gap-3">
            {#each Array(3) as _}
                <Skeleton class="h-32 w-full" />
            {/each}
        </div>
    {:else if results}
        {#if results.length === 0}
            <Card.Root>
                <Card.Content
                    class="flex flex-col items-center gap-2 py-10 text-center"
                >
                    <SearchIcon class="size-10 text-muted-foreground/50" />
                    <p class="text-sm text-muted-foreground">
                        No results found for "{query}".
                    </p>
                    <p class="text-xs text-muted-foreground">
                        Try a different search term or browse popular models on
                        HuggingFace.
                    </p>
                </Card.Content>
            </Card.Root>
        {:else}
            <!-- ── Results Table ───────────────────────── -->
            <Card.Root class="flex flex-col overflow-hidden">
                <div class="flex items-center justify-between px-6 pt-4 pb-2">
                    <p class="text-sm text-muted-foreground">
                        {results.length} result{results.length !== 1 ? "s" : ""}
                        &mdash; click <strong>Inspect</strong> to view available
                        files
                    </p>
                </div>
                <div class="max-h-[calc(100dvh-20rem)] overflow-y-auto">
                    <Card.Content class="p-0">
                        <Table.Root>
                            <Table.Header>
                                <Table.Row>
                                    <Table.Head class="w-[45%]">Name</Table.Head
                                    >
                                    <Table.Head class="w-[15%]">Type</Table.Head
                                    >
                                    <Table.Head class="w-[15%]"
                                        >Downloads</Table.Head
                                    >
                                    <Table.Head class="w-[10%]"
                                        >Likes</Table.Head
                                    >
                                </Table.Row>
                            </Table.Header>
                            <Table.Body>
                                {#each results as r (r.repo_id)}
                                    {@const displayName =
                                        r.repo_id.split("/").pop() ?? r.repo_id}
                                    <Table.Row
                                        class="cursor-pointer transition-colors hover:bg-muted/50"
                                        onclick={() => handleInspect(r.repo_id)}
                                        role="button"
                                        tabindex={0}
                                        onkeydown={(e) => {
                                            if (
                                                e.key === "Enter" ||
                                                e.key === " "
                                            ) {
                                                e.preventDefault();
                                                handleInspect(r.repo_id);
                                            }
                                        }}
                                    >
                                        <Table.Cell class="font-medium">
                                            <div class="flex flex-col">
                                                <span class="truncate"
                                                    >{displayName}</span
                                                >
                                                <span
                                                    class="truncate text-[11px] text-muted-foreground"
                                                >
                                                    {r.repo_id}
                                                </span>
                                            </div>
                                        </Table.Cell>
                                        <Table.Cell>
                                            <span
                                                class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium capitalize leading-none {typeColor(
                                                    r.type,
                                                )}"
                                            >
                                                {r.type || "unknown"}
                                            </span>
                                        </Table.Cell>
                                        <Table.Cell
                                            class="tabular-nums text-muted-foreground"
                                        >
                                            {#if r.downloads > 0}
                                                <span
                                                    class="inline-flex items-center gap-1"
                                                >
                                                    <DownloadIcon
                                                        class="size-3 text-muted-foreground/50"
                                                    />
                                                    {r.downloads.toLocaleString()}
                                                </span>
                                            {:else}
                                                —
                                            {/if}
                                        </Table.Cell>
                                        <Table.Cell
                                            class="tabular-nums text-muted-foreground"
                                        >
                                            {#if r.likes > 0}
                                                <span
                                                    class="inline-flex items-center gap-1"
                                                >
                                                    <ThumbsUpIcon
                                                        class="size-3 text-muted-foreground/50"
                                                    />
                                                    {r.likes.toLocaleString()}
                                                </span>
                                            {:else}
                                                —
                                            {/if}
                                        </Table.Cell>
                                    </Table.Row>
                                {/each}
                            </Table.Body>
                        </Table.Root>
                    </Card.Content>
                </div>
            </Card.Root>
        {/if}
    {/if}
</div>

<InspectSheet bind:open={sheetOpen} bind:repoId={inspectRepoId} />
