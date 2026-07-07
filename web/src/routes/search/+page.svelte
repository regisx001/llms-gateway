<script lang="ts">
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
    import { ui, typeColor, doSearch } from "./search.svelte";

    // Inspect sheet state (local — needs bind: with InspectSheet)
    let sheetOpen = $state(false);
    let inspectRepoId = $state("");

    function handleInspect(repoId: string) {
        inspectRepoId = repoId;
        sheetOpen = true;
    }
</script>

<svelte:head>
    <title>Search — modelctl</title>
    <meta
        name="description"
        content="Search HuggingFace for GGUF models — find and install models for llama.cpp inference."
    />
    <meta
        name="keywords"
        content="modelctl, HuggingFace, GGUF, model search, llama.cpp, AI models"
    />
    <meta property="og:title" content="Search — modelctl" />
    <meta
        property="og:description"
        content="Search HuggingFace for GGUF models — find and install models for llama.cpp inference."
    />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="Search — modelctl" />
    <meta
        name="twitter:description"
        content="Search HuggingFace for GGUF models — find and install models for llama.cpp inference."
    />
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
                        value={ui.query}
                        oninput={(e) =>
                            (ui.query = (
                                e.currentTarget as HTMLInputElement
                            ).value)}
                        placeholder="e.g. gemma, llama, nomic-embed…"
                        class="pl-9"
                    />
                </div>
                <Button type="submit" disabled={ui.loading || !ui.query.trim()}>
                    {#if ui.loading}
                        <Spinner class="size-4" />
                    {:else}
                        <SearchIcon class="size-4" />
                    {/if}
                    Search
                </Button>
            </form>
        </Card.Content>
    </Card.Root>

    {#if ui.error}
        <Card.Root class="border-destructive/50 bg-destructive/10">
            <Card.Content class="text-sm">{ui.error}</Card.Content>
        </Card.Root>
    {/if}

    {#if ui.loading}
        <div class="flex flex-col gap-3">
            {#each Array(3) as _}
                <Skeleton class="h-32 w-full" />
            {/each}
        </div>
    {:else if ui.results}
        {#if ui.results.length === 0}
            <Card.Root>
                <Card.Content
                    class="flex flex-col items-center gap-2 py-10 text-center"
                >
                    <SearchIcon class="size-10 text-muted-foreground/50" />
                    <p class="text-sm text-muted-foreground">
                        No results found for "{ui.query}".
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
                        {ui.results.length} result{ui.results.length !== 1
                            ? "s"
                            : ""}
                        &mdash; click <strong>Inspect</strong> to view available
                        files
                    </p>
                </div>
                <div class="max-h-[calc(100dvh-20rem)] overflow-y-auto">
                    <Card.Content>
                        <Table.Root>
                            <Table.Header>
                                <Table.Row>
                                    <Table.Head>Name</Table.Head>
                                    <Table.Head>Type</Table.Head>
                                    <Table.Head>Downloads</Table.Head>
                                    <Table.Head>Likes</Table.Head>
                                </Table.Row>
                            </Table.Header>
                            <Table.Body>
                                {#each ui.results as r (r.repo_id)}
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
                                                class="inline-block rounded-md px-2.5 py-1 text-xs font-medium capitalize {typeColor(
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
