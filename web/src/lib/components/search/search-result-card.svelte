<script lang="ts">
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import * as Card from "$lib/components/ui/card";
    import DownloadIcon from "@lucide/svelte/icons/download";
    import ThumbsUpIcon from "@lucide/svelte/icons/thumbs-up";
    import SearchIcon from "@lucide/svelte/icons/search";

    interface SearchResult {
        repo_id: string;
        type: string;
        downloads: number;
        likes: number;
        tags: string[];
        license: string;
    }

    let {
        result,
        onInspect,
    }: {
        result: SearchResult;
        onInspect: (repoId: string) => void;
    } = $props();

    let displayName = $derived(result.repo_id.split("/").pop() ?? result.repo_id);

    function typeBadgeVariant(
        type: string,
    ): "default" | "secondary" | "outline" | "destructive" {
        switch (type) {
            case "chat":
                return "default";
            case "embedding":
                return "secondary";
            case "vision":
                return "outline";
            case "reranker":
                return "destructive";
            default:
                return "outline";
        }
    }
</script>

<Card.Root class="group transition-shadow hover:shadow-md">
    <Card.Header>
        <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
                <Card.Title class="truncate text-base">
                    {displayName}
                </Card.Title>
                <Card.Description class="truncate text-xs">
                    {result.repo_id}
                </Card.Description>
            </div>
            <Badge
                variant={typeBadgeVariant(result.type)}
                class="shrink-0 capitalize"
            >
                {result.type || "unknown"}
            </Badge>
        </div>
    </Card.Header>
    <Card.Content class="flex flex-col gap-3">
        <!-- Stats -->
        <div class="flex flex-wrap gap-4 text-xs text-muted-foreground">
            {#if result.downloads > 0}
                <span class="flex items-center gap-1">
                    <DownloadIcon class="size-3" />
                    {result.downloads.toLocaleString()}
                </span>
            {/if}
            {#if result.likes > 0}
                <span class="flex items-center gap-1">
                    <ThumbsUpIcon class="size-3" />
                    {result.likes.toLocaleString()}
                </span>
            {/if}
        </div>
    </Card.Content>
    <Card.Footer>
        <Button
            variant="outline"
            class="w-full"
            onclick={() => onInspect(result.repo_id)}
        >
            <SearchIcon class="size-3.5" />
            Inspect &amp; Install
        </Button>
    </Card.Footer>
</Card.Root>
