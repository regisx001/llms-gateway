<script lang="ts">
    import { page } from "$app/stores";
    import { config } from "$lib/config";
    import { Button } from "$lib/components/ui/button";
    import { Input } from "$lib/components/ui/input";
    import * as Card from "$lib/components/ui/card";
    import { Spinner } from "$lib/components/ui/spinner";
    import SearchIcon from "@lucide/svelte/icons/search";
    import InspectSheet from "$lib/components/search/inspect-sheet.svelte";
    import SearchResultCard from "$lib/components/search/search-result-card.svelte";

    let query = $state($page.url.searchParams.get("q") || "");
    let results = $state<any[] | null>(null);
    let loading = $state(false);
    let error = $state<string | null>(null);

    // Inspect sheet state
    let sheetOpen = $state(false);
    let inspectRepoId = $state("");

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

<div class="mx-auto flex max-w-4xl flex-col gap-6 p-6">
    <div>
        <h1 class="text-2xl font-semibold">Search HuggingFace</h1>
        <p class="text-sm text-muted-foreground">
            Find and install GGUF models from the HuggingFace Hub.
        </p>
    </div>

    <form
        class="flex gap-2"
        onsubmit={(e) => {
            e.preventDefault();
            doSearch();
        }}
    >
        <div class="relative flex-1">
            <SearchIcon
                class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <Input
                bind:value={query}
                placeholder="e.g. gemma, llama…"
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

    {#if error}
        <Card.Root class="border-destructive/50 bg-destructive/10">
            <Card.Content class="text-sm">{error}</Card.Content>
        </Card.Root>
    {/if}

    {#if results}
        {#if results.length === 0}
            <Card.Root>
                <Card.Content
                    class="py-10 text-center text-sm text-muted-foreground"
                >
                    No results found for "{query}".
                </Card.Content>
            </Card.Root>
        {:else}
            <div class="flex flex-col gap-3">
                <p class="text-sm text-muted-foreground">
                    {results.length} result{results.length !== 1 ? "s" : ""}
                    &mdash; click <strong>Inspect &amp; Install</strong> to view
                    available files
                </p>
                {#each results as r (r.repo_id)}
                    <SearchResultCard result={r} onInspect={handleInspect} />
                {/each}
            </div>
        {/if}
    {/if}
</div>

<InspectSheet bind:open={sheetOpen} bind:repoId={inspectRepoId} />
