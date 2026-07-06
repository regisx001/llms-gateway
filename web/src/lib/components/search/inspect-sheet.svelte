<script lang="ts">
    import { config } from "$lib/config";
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import { Spinner } from "$lib/components/ui/spinner";
    import { Skeleton } from "$lib/components/ui/skeleton";
    import { Separator } from "$lib/components/ui/separator";
    import * as Sheet from "$lib/components/ui/sheet";
    import * as Card from "$lib/components/ui/card";
    import XIcon from "@lucide/svelte/icons/x";
    import DownloadIcon from "@lucide/svelte/icons/download";
    import AlertCircleIcon from "@lucide/svelte/icons/alert-circle";
    import CuboidIcon from "@lucide/svelte/icons/cuboid";
    import ThumbsUpIcon from "@lucide/svelte/icons/thumbs-up";
    import ScaleIcon from "@lucide/svelte/icons/scale";
    import StarIcon from "@lucide/svelte/icons/star";
    import { cn } from "$lib/utils";
    import { startDownload } from "$lib/stores/downloads.svelte";

    interface GgufFile {
        filename: string;
        size: number;
    }

    interface InspectData {
        repo_id: string;
        type: string;
        description: string;
        downloads: number;
        likes: number;
        license: string;
        pipeline_tag: string;
        library_name: string;
        gguf_files: GgufFile[];
        total_files: number;
    }

    type Phase = "loading" | "inspect" | "error";

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
    let installingFile = $state<string | null>(null);

    // Derived
    let title = $derived(inspectData?.repo_id ?? repoId);
    let displayName = $derived(title.split("/").pop() ?? title);

    // ── Helpers ─────────────────────────────────────────────────

    function typeColor(type: string): string {
        const colors: Record<string, string> = {
            chat: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
            embedding: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
            reranker: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
            vision: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
        };
        return colors[type] ?? "bg-muted text-muted-foreground";
    }

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
                const body = await res
                    .json()
                    .catch(() => ({ detail: res.statusText }));
                throw new Error(body.detail || `HTTP ${res.status}`);
            }
            inspectData = await res.json();
            phase = "inspect";
        } catch (e) {
            inspectError =
                e instanceof Error ? e.message : "Failed to inspect repository";
            phase = "error";
        }
    }

    // ── Install ─────────────────────────────────────────────────

    async function installFile(filename: string) {
        installError = null;
        installingFile = filename;

        try {
            // Fire async install — returns immediately with 202
            const installRes = await fetch(
                `${config.apiBase}/api/v1/models/install`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        repo_id: repoId,
                        filename,
                        model_type: inspectData?.type ?? undefined,
                    }),
                },
            );

            if (!installRes.ok) {
                const body = await installRes
                    .json()
                    .catch(() => ({ detail: installRes.statusText }));
                throw new Error(
                    body.detail || `Install failed: ${installRes.status}`,
                );
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
        } finally {
            installingFile = null;
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
    <Sheet.Content side="right" class="w-full sm:max-w-4xl! p-0">
        <div class="flex h-full flex-col">
            <!-- ── Header ───────────────────────────────────── -->
            <div
                class="flex items-start justify-between gap-3 border-b px-6 py-4"
            >
                <div class="min-w-0 flex-1">
                    <Sheet.Title class="truncate text-lg font-semibold">
                        {#if phase === "loading"}
                            Loading…
                        {:else if phase === "error" && !inspectData}
                            Error
                        {:else}
                            {displayName}
                        {/if}
                    </Sheet.Title>
                    {#if phase === "inspect" && inspectData}
                        <p class="truncate text-xs text-muted-foreground">
                            {inspectData.repo_id}
                        </p>
                    {/if}
                </div>
                <!-- <Sheet.Close onclick={handleClose}>
                    <XIcon class="size-4" />
                </Sheet.Close> -->
            </div>

            <!-- ── Body ─────────────────────────────────────── -->
            <div class="flex-1 overflow-y-auto px-6 py-4">
                {#if phase === "loading"}
                    <!-- Loading skeleton -->
                    <div class="flex flex-col gap-4">
                        <div class="flex gap-2">
                            <Skeleton class="h-6 w-16" />
                            <Skeleton class="h-6 w-24" />
                            <Skeleton class="h-6 w-20" />
                        </div>
                        <div class="grid grid-cols-4 gap-3">
                            <Skeleton class="h-20 w-full" />
                            <Skeleton class="h-20 w-full" />
                            <Skeleton class="h-20 w-full" />
                            <Skeleton class="h-20 w-full" />
                        </div>
                        <Skeleton class="h-4 w-full" />
                        <Skeleton class="h-4 w-3/4" />
                        <Separator />
                        <Skeleton class="h-5 w-48" />
                        {#each Array(4) as _}
                            <Skeleton class="h-16 w-full" />
                        {/each}
                    </div>
                {:else if phase === "inspect" && inspectData}
                    <!-- Repo info -->
                    <div class="flex flex-col gap-4">
                        <!-- Badges + Stats row: compact card -->
                        <div class="rounded-lg border bg-card p-4">
                            <!-- Badges -->
                            <div class="flex flex-wrap gap-1.5">
                                <span
                                    class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium capitalize {typeColor(
                                        inspectData.type,
                                    )}"
                                >
                                    {inspectData.type}
                                </span>
                                {#if inspectData.pipeline_tag}
                                    <Badge
                                        variant="outline"
                                        class="text-[11px]"
                                    >
                                        {inspectData.pipeline_tag}
                                    </Badge>
                                {/if}
                                {#if inspectData.library_name}
                                    <Badge
                                        variant="outline"
                                        class="text-[11px]"
                                    >
                                        {inspectData.library_name}
                                    </Badge>
                                {/if}
                            </div>

                            <!-- Stats grid -->
                            <div class="mt-4 grid grid-cols-4 gap-3">
                                <div
                                    class="flex flex-col items-center rounded-md bg-muted/50 py-2"
                                >
                                    <span class="text-xs text-muted-foreground"
                                        >Downloads</span
                                    >
                                    <span
                                        class="mt-0.5 text-sm font-semibold tabular-nums"
                                    >
                                        {inspectData.downloads.toLocaleString()}
                                    </span>
                                </div>
                                <div
                                    class="flex flex-col items-center rounded-md bg-muted/50 py-2"
                                >
                                    <span class="text-xs text-muted-foreground"
                                        >Likes</span
                                    >
                                    <span
                                        class="mt-0.5 text-sm font-semibold tabular-nums"
                                    >
                                        {inspectData.likes.toLocaleString()}
                                    </span>
                                </div>
                                <div
                                    class="flex flex-col items-center rounded-md bg-muted/50 py-2"
                                >
                                    <span class="text-xs text-muted-foreground"
                                        >License</span
                                    >
                                    <span
                                        class="mt-0.5 max-w-full truncate text-sm font-semibold"
                                    >
                                        {inspectData.license || "—"}
                                    </span>
                                </div>
                                <div
                                    class="flex flex-col items-center rounded-md bg-muted/50 py-2"
                                >
                                    <span class="text-xs text-muted-foreground"
                                        >Files</span
                                    >
                                    <span
                                        class="mt-0.5 text-sm font-semibold tabular-nums"
                                    >
                                        {inspectData.total_files}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- Description -->
                        {#if inspectData.description}
                            <div class="rounded-lg bg-muted/30 p-3">
                                <p
                                    class="text-sm leading-relaxed text-muted-foreground line-clamp-6"
                                >
                                    {inspectData.description}
                                </p>
                            </div>
                        {/if}

                        <Separator />

                        <!-- Files section -->
                        <div>
                            <div class="mb-3 flex items-center justify-between">
                                <p class="text-sm font-medium">GGUF Files</p>
                                <Badge variant="outline" class="text-[11px]">
                                    {inspectData.gguf_files.length} available
                                </Badge>
                            </div>

                            {#if inspectData.gguf_files.length === 0}
                                <div
                                    class="flex flex-col items-center gap-2 py-8 text-center"
                                >
                                    <CuboidIcon
                                        class="size-8 text-muted-foreground/40"
                                    />
                                    <p class="text-sm text-muted-foreground">
                                        No GGUF files found in this repository.
                                    </p>
                                </div>
                            {:else}
                                <div class="flex flex-col gap-2">
                                    {#each inspectData.gguf_files as file}
                                        {@const isObj =
                                            typeof file === "object"}
                                        {@const fileName = isObj
                                            ? file.filename
                                            : file}
                                        {@const fileSize = isObj
                                            ? file.size
                                            : 0}
                                        {@const quant =
                                            parseSizeFromFilename(fileName)}
                                        {@const recommended =
                                            isRecommended(fileName)}
                                        {@const isInstalling =
                                            installingFile === fileName}
                                        <div
                                            class={cn(
                                                "flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/50",
                                                recommended &&
                                                    "border-primary/40 bg-primary/5",
                                            )}
                                        >
                                            <div class="min-w-0 flex-1">
                                                <p
                                                    class="truncate text-sm font-medium"
                                                >
                                                    {fileName}
                                                </p>
                                                <div
                                                    class="mt-0.5 flex items-center gap-1.5"
                                                >
                                                    {#if quant}
                                                        <span
                                                            class="inline-flex items-center rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-muted-foreground"
                                                        >
                                                            {quant}
                                                        </span>
                                                    {/if}
                                                    {#if fileSize > 0}
                                                        <span
                                                            class="inline-flex items-center rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-muted-foreground"
                                                        >
                                                            {formatSize(
                                                                fileSize,
                                                            )}
                                                        </span>
                                                    {/if}
                                                    {#if recommended}
                                                        <span
                                                            class="inline-flex items-center gap-0.5 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary"
                                                        >
                                                            <StarIcon
                                                                class="size-2.5"
                                                            />
                                                            Recommended
                                                        </span>
                                                    {/if}
                                                </div>
                                            </div>
                                            <Button
                                                variant={recommended
                                                    ? "default"
                                                    : "outline"}
                                                size="sm"
                                                disabled={isInstalling}
                                                onclick={() =>
                                                    installFile(fileName)}
                                                class="shrink-0"
                                            >
                                                {#if isInstalling}
                                                    <Spinner class="size-3.5" />
                                                    Installing…
                                                {:else}
                                                    <DownloadIcon
                                                        class="size-3.5"
                                                    />
                                                    Install
                                                {/if}
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
                        <div
                            class="flex size-16 items-center justify-center rounded-full bg-destructive/10"
                        >
                            <AlertCircleIcon class="size-8 text-destructive" />
                        </div>
                        <div class="text-center">
                            <p class="font-medium">Something went wrong</p>
                            <p class="mt-1 text-sm text-muted-foreground">
                                {installError ||
                                    inspectError ||
                                    "An unexpected error occurred."}
                            </p>
                        </div>
                        <div class="flex gap-2">
                            <Button variant="outline" onclick={handleClose}>
                                Close
                            </Button>
                            {#if inspectError}
                                <Button onclick={loadInspect}>Retry</Button>
                            {/if}
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    </Sheet.Content>
</Sheet.Root>
