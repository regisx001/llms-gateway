import { config } from "$lib/config";
import { page } from "$app/state";

// ── State ──────────────────────────────────────────────────────────

export const ui = $state({
    query: page.url.searchParams.get("q") || "",
    results: null as any[] | null,
    loading: false,
    error: null as string | null,
});

// ── Utilities ──────────────────────────────────────────────────────

export function typeColor(type: string): string {
    const colors: Record<string, string> = {
        chat: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
        embedding: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
        reranker: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
        vision: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
    };
    return colors[type] ?? "bg-muted text-muted-foreground";
}

// ── Actions ────────────────────────────────────────────────────────

export async function doSearch() {
    if (!ui.query.trim()) return;
    ui.loading = true;
    ui.error = null;
    try {
        const res = await fetch(
            `${config.apiBase}/api/v1/search?q=${encodeURIComponent(ui.query.trim())}&limit=20`,
        );
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        ui.results = data.results ?? [];
    } catch (e) {
        ui.error = e instanceof Error ? e.message : "Search failed";
        ui.results = null;
    } finally {
        ui.loading = false;
    }
}
