<script lang="ts">
    import {
        downloads,
        dismiss,
        downloadFormatSize,
    } from "$lib/stores/downloads.svelte";
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import { Spinner } from "$lib/components/ui/spinner";
    import { cn } from "$lib/utils";
    import XIcon from "@lucide/svelte/icons/x";
    import DownloadIcon from "@lucide/svelte/icons/download";
    import CheckCircle2Icon from "@lucide/svelte/icons/check-circle-2";
    import AlertCircleIcon from "@lucide/svelte/icons/alert-circle";

    let all = $derived(downloads.all);
</script>

{#if all.length > 0}
    <div class="fixed right-4 top-4 z-50 flex w-80 flex-col gap-2">
        {#each all as d (d.modelId)}
            <div
                class={cn(
                    "rounded-lg border bg-card p-3 shadow-lg transition-all",
                    (d.status === "installed" || d.status === "active") && "border-emerald-500/30",
                    d.status === "error" && "border-destructive/30",
                )}
            >
                <div class="mb-1 flex items-start justify-between gap-2">
                    <div class="min-w-0 flex-1">
                        <p class="truncate text-sm font-medium">
                            {#if d.status === "downloading"}
                                <Spinner class="mr-1 inline size-3" />
                            {:else if d.status === "installed" || d.status === "active"}
                                <CheckCircle2Icon class="mr-1 inline size-3.5 text-emerald-500" />
                            {:else if d.status === "error"}
                                <AlertCircleIcon class="mr-1 inline size-3.5 text-destructive" />
                            {:else}
                                <DownloadIcon class="mr-1 inline size-3.5 text-primary" />
                            {/if}
                            {d.filename || d.repoId}
                        </p>
                        <p class="truncate text-xs text-muted-foreground">
                            {d.repoId}
                        </p>
                    </div>
                    <button
                        class="shrink-0 rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                        onclick={() => dismiss(d.modelId)}
                    >
                        <XIcon class="size-3.5" />
                    </button>
                </div>

                <!-- Progress bar -->
                {#if d.status === "downloading"}
                    <div class="mt-2">
                        <div class="mb-1 flex justify-between text-xs text-muted-foreground">
                            <span>{d.progressPct}%</span>
                            <span>
                                {downloadFormatSize(d.downloadedBytes)}
                                {#if d.totalBytes > 0}
                                    / {downloadFormatSize(d.totalBytes)}
                                {/if}
                            </span>
                        </div>
                        <div class="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                            <div
                                class="h-full rounded-full bg-primary transition-all duration-500"
                                style="width: {d.progressPct}%"
                            ></div>
                        </div>
                    </div>
                {:else if d.status === "error"}
                    <p class="mt-1 text-xs text-destructive">
                        {d.error || "Install failed"}
                    </p>
                {:else if d.status === "installed" || d.status === "active"}
                    <div class="mt-2 flex items-center gap-1.5">
                        <CheckCircle2Icon
                            data-icon="inline-start"
                            class="size-3 text-emerald-500"
                        />
                        <span class="text-xs text-emerald-600">
                            Install complete
                        </span>
                        <span class="text-xs text-muted-foreground">
                            {downloadFormatSize(d.totalBytes)}
                        </span>
                    </div>
                {/if}
            </div>
        {/each}
    </div>
{/if}
