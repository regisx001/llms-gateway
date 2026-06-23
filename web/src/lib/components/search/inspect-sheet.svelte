<script lang="ts">
    import { config } from "$lib/config";
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import { Spinner } from "$lib/components/ui/spinner";
    import { Skeleton } from "$lib/components/ui/skeleton";
    import { Separator } from "$lib/components/ui/separator";
    import * as Sheet from "$lib/components/ui/sheet";
    import XIcon from "@lucide/svelte/icons/x";
    import DownloadIcon from "@lucide/svelte/icons/download";
    import AlertCircleIcon from "@lucide/svelte/icons/alert-circle";
    import CuboidIcon from "@lucide/svelte/icons/cuboid";
    import ThumbsUpIcon from "@lucide/svelte/icons/thumbs-up";
    import ScaleIcon from "@lucide/svelte/icons/scale";
    import { cn } from "$lib/utils";
    import { startDownload } from "$lib/stores/downloads.svelte";

    interface InspectData {
        repo_id: string;
        type: string;
        description: string;
        downloads: number;
        likes: number;
        license: string;
        pipeline_tag: string;
        library_name: string;
        gguf_files: string[];
        total_files: number;
    }

    type Phase =
        | "loading"
        | "inspect"
        | "error";

    let {
        open = $bindable(false),
        repoId = $bindable(""),
    }: {
        open: boolean;
        repoId: string;
    } = $props();

    let phase = $state<Phase>("loading");
    let inspectData = $state<InspectData | null>(null);
    let inspectError = $state<string | null>(null);
    let installError = $state<string | null>(null);

    // Derived
    let title = $derived(inspectData?.repo_id ?? repoId);
    let displayName = $derived(title.split("/").pop() ?? title);

    // ── Helpers ─────────────────────────────────────────────────

    function formatSize(bytes: number): string {
        const units = ["B", "KB", "MB", "GB", "TB"];
        let n = bytes;
        for (const u of units) {
            if (n < 1024) return `${n.toFixed(1)} ${u}`;
            n /= 1024;
        }
        return `${n.toFixed(1)} PB`;
    }

    function parseSizeFromFilename(filename: string): string {
        // Extract Q-notation hint: Q2_K, Q4_K_M, Q8_0, etc.
        const m = filename.match(/Q(\d+[._]\d*[A-Za-z_]*)/i);
        if (m) return m[0];
        return "";
    }

    function isRecommended(filename: string): boolean {
        // Q4_K_M is the best balance of quality/size for most models
        const m = filename.match(/Q4[._]K[._]M/i);
        return m !== null;
    }

    function typeBadgeVariant(type: string): "default" | "secondary" | "outline" | "destructive" {
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

    // ── Inspect ─────────────────────────────────────────────────

    async function loadInspect() {
        phase = "loading";
        inspectError = null;
        installError = null;
        try {
            const res = await fetch(
                `${config.apiBase}/api/v1/search/inspect?repo_id=${encodeURIComponent(repoId)}`,
            );
            if (!res.ok) {
                const body = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(body.detail || `HTTP ${res.status}`);
            }
            inspectData = await res.json();
            phase = "inspect";
        } catch (e) {
            inspectError = e instanceof Error ? e.message : "Failed to inspect repository";
            phase = "error";
        }
    }

    // ── Install ─────────────────────────────────────────────────

    async function installFile(filename: string) {
        installError = null;

        try {
            // Fire async install — returns immediately with 202
            const installRes = await fetch(`${config.apiBase}/api/v1/models/install`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    repo_id: repoId,
                    filename,
                    model_type: inspectData?.type ?? undefined,
                }),
            });

            if (!installRes.ok) {
                const body = await installRes.json().catch(() => ({ detail: installRes.statusText }));
                throw new Error(body.detail || `Install failed: ${installRes.status}`);
            }

            const installResult = await installRes.json();
            const modelId = installResult.id;

            // Start polling via the notification store
            startDownload(modelId, repoId, filename);

            // Close sheet — download continues in background
            handleClose();
        } catch (e) {
            installError = e instanceof Error ? e.message : "Install failed";
            phase = "error";
        }
    }

    function handleClose() {
        open = false;
        // Reset state after animation
        setTimeout(() => {
            phase = "loading";
            inspectData = null;
            inspectError = null;
            installError = null;
        }, 300);
    }

    // ── React to open/repoId changes ────────────────────────────

    $effect(() => {
        if (open && repoId) {
            loadInspect();
        }
    });
</script>

<Sheet.Root bind:open>
    <Sheet.Content side="right" class="w-full max-w-lg sm:max-w-xl p-0">
        <div class="flex h-full flex-col">
            <!-- ── Header ───────────────────────────────────── -->
            <div class="flex items-center justify-between border-b px-6 py-4">
                <Sheet.Title class="text-lg font-semibold">
                    {#if phase === "loading"}
                        Loading…
                    {:else if phase === "error" && !inspectData}
                        Error
                    {:else}
                        {displayName}
                    {/if}
                </Sheet.Title>
                <Sheet.Close onclick={handleClose}>
                    <XIcon class="size-4" />
                </Sheet.Close>
            </div>

            <!-- ── Body ─────────────────────────────────────── -->
            <div class="flex-1 overflow-y-auto px-6 py-4">
                {#if phase === "loading"}
                    <!-- Loading skeleton -->
                    <div class="flex flex-col gap-4">
                        <Skeleton class="h-5 w-48" />
                        <Skeleton class="h-4 w-full" />
                        <Skeleton class="h-4 w-3/4" />
                        <div class="mt-4 flex flex-col gap-2">
                            {#each Array(5) as _}
                                <Skeleton class="h-16 w-full" />
                            {/each}
                        </div>
                    </div>

                {:else if phase === "inspect" && inspectData}
                    <!-- Repo info -->
                    <div class="flex flex-col gap-4">
                        <!-- Badges row -->
                        <div class="flex flex-wrap gap-2">
                            <Badge variant={typeBadgeVariant(inspectData.type)}>
                                {inspectData.type}
                            </Badge>
                            {#if inspectData.pipeline_tag}
                                <Badge variant="outline">{inspectData.pipeline_tag}</Badge>
                            {/if}
                            {#if inspectData.library_name}
                                <Badge variant="outline">{inspectData.library_name}</Badge>
                            {/if}
                        </div>

                        <!-- Stats row -->
                        <div class="flex flex-wrap gap-4 text-sm text-muted-foreground">
                            <span class="flex items-center gap-1.5">
                                <DownloadIcon class="size-3.5" />
                                {inspectData.downloads.toLocaleString()}
                            </span>
                            <span class="flex items-center gap-1.5">
                                <ThumbsUpIcon class="size-3.5" />
                                {inspectData.likes.toLocaleString()}
                            </span>
                            {#if inspectData.license}
                                <span class="flex items-center gap-1.5">
                                    <ScaleIcon class="size-3.5" />
                                    {inspectData.license}
                                </span>
                            {/if}
                        </div>

                        <!-- Description -->
                        {#if inspectData.description}
                            <div class="rounded-lg bg-muted/50 p-3">
                                <p class="text-sm text-muted-foreground line-clamp-6">
                                    {inspectData.description}
                                </p>
                            </div>
                        {/if}

                        <Separator />

                        <!-- Files section -->
                        <div>
                            <p class="mb-3 text-sm font-medium">
                                Available GGUF Files
                                <span class="ml-1 text-muted-foreground">
                                    ({inspectData.gguf_files.length})
                                </span>
                            </p>

                            {#if inspectData.gguf_files.length === 0}
                                <div class="flex flex-col items-center gap-2 py-8 text-center">
                                    <CuboidIcon class="size-8 text-muted-foreground/40" />
                                    <p class="text-sm text-muted-foreground">
                                        No GGUF files found in this repository.
                                    </p>
                                </div>
                            {:else}
                                <div class="flex flex-col gap-2">
                                    {#each inspectData.gguf_files as file}
                                        {@const quant = parseSizeFromFilename(file)}
                                        {@const recommended = isRecommended(file)}
                                        <div
                                            class={cn(
                                                "flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/50",
                                                recommended && "border-primary/50 bg-primary/5",
                                            )}
                                        >
                                            <div class="min-w-0 flex-1">
                                                <p class="truncate text-sm font-medium">
                                                    {file}
                                                </p>
                                                <div class="mt-0.5 flex items-center gap-2">
                                                    {#if quant}
                                                        <Badge
                                                            variant="outline"
                                                            class="px-1.5 py-0 text-[10px]"
                                                        >
                                                            {quant}
                                                        </Badge>
                                                    {/if}
                                                    {#if recommended}
                                                        <Badge
                                                            variant="default"
                                                            class="px-1.5 py-0 text-[10px]"
                                                        >
                                                            Recommended
                                                        </Badge>
                                                    {/if}
                                                </div>
                                            </div>
                                            <Button
                                                variant={recommended ? "default" : "outline"}
                                                size="sm"
                                                onclick={() => installFile(file)}
                                                class="shrink-0"
                                            >
                                                Install
                                            </Button>
                                        </div>
                                    {/each}
                                </div>
                            {/if}
                        </div>
                    </div>

                {:else if phase === "error"}
                    <!-- Error -->
                    <div class="flex flex-col items-center gap-4 py-8">
                        <div class="flex size-16 items-center justify-center rounded-full bg-destructive/10">
                            <AlertCircleIcon class="size-8 text-destructive" />
                        </div>
                        <div class="text-center">
                            <p class="font-medium">Something went wrong</p>
                            <p class="mt-1 text-sm text-muted-foreground">
                                {installError || inspectError || "An unexpected error occurred."}
                            </p>
                        </div>
                        <div class="flex gap-2">
                            <Button variant="outline" onclick={handleClose}>
                                Close
                            </Button>
                            {#if inspectError}
                                <Button onclick={loadInspect}>
                                    Retry
                                </Button>
                            {/if}
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    </Sheet.Content>
</Sheet.Root>
