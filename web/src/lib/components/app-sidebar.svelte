<script lang="ts">
    import { onMount } from "svelte";
    import * as Sidebar from "$lib/components/ui/sidebar/index.js";
    import { useSidebar } from "$lib/components/ui/sidebar/context.svelte.js";
    import { page } from "$app/state";
    import { Button } from "$lib/components/ui/button";
    import { Badge } from "$lib/components/ui/badge";
    import { Separator } from "$lib/components/ui/separator";
    import { config } from "$lib/config";

    import HouseIcon from "@lucide/svelte/icons/house";
    import SearchIcon from "@lucide/svelte/icons/search";
    import CuboidIcon from "@lucide/svelte/icons/cuboid";
    import BoxIcon from "@lucide/svelte/icons/box";
    import ActivityIcon from "@lucide/svelte/icons/activity";
    import XIcon from "@lucide/svelte/icons/x";
    import CommandIcon from "@lucide/svelte/icons/command";

    const sidebar = useSidebar();

    const navItems = [
        { title: "Dashboard", url: "/", icon: HouseIcon },
        { title: "Search", url: "/search", icon: SearchIcon },
        { title: "Models", url: "/models", icon: CuboidIcon },
        { title: "Containers", url: "/containers", icon: BoxIcon },
    ];

    let currentPath = $derived(page.url.pathname);

    function isActive(url: string): boolean {
        return currentPath === url;
    }

    function handleNavClick() {
        if (sidebar.isMobile) {
            sidebar.toggle();
        }
    }

    // ── Data fetching ────────────────────────────────────
    let modelCount = $state<number | null>(null);
    let diskUsed = $state<string>("—");
    let diskTotal = $state<string>("—");
    let diskPct = $state<number>(0);

    async function loadSidebarInfo() {
        try {
            const [modelRes, infoRes] = await Promise.all([
                fetch(`${config.apiBase}/api/v1/models`),
                fetch(`${config.apiBase}/api/v1/system/info`),
            ]);
            if (modelRes.ok) {
                const data = await modelRes.json();
                modelCount = data.models?.length ?? null;
            }
            if (infoRes.ok) {
                const info = await infoRes.json();
                const used = parseStorage(info.storage_used);
                const total = parseStorage(info.storage_free) + used;
                diskUsed = info.storage_used || "—";
                diskTotal = formatBytes(total);
                diskPct = total > 0 ? Math.round((used / total) * 100) : 0;
            }
        } catch {
            // Silently fail — sidebar data is non-critical
        }
    }

    function parseStorage(str: string): number {
        const match = str.trim().match(/^([\d.]+)\s*(\w+)$/);
        if (!match) return 0;
        const val = parseFloat(match[1]);
        const unit = match[2].toUpperCase();
        const units: Record<string, number> = {
            B: 1,
            KB: 1024,
            MB: 1024 ** 2,
            GB: 1024 ** 3,
            TB: 1024 ** 4,
        };
        return val * (units[unit] || 1);
    }

    function formatBytes(bytes: number): string {
        const units = ["B", "KB", "MB", "GB", "TB"];
        let n = bytes;
        for (const u of units) {
            if (n < 1024) return `${n.toFixed(1)} ${u}`;
            n /= 1024;
        }
        return `${n.toFixed(1)} PB`;
    }

    onMount(loadSidebarInfo);
</script>

<Sidebar.Root>
    <div class="flex h-full flex-col">
        <!-- ── Header ─────────────────────────────────────── -->
        <Sidebar.Header
            class="bg-sidebar/50 p-3 backdrop-blur-lg md:pt-4 md:pb-2"
        >
            <div class="flex items-center justify-between">
                <a href="/" onclick={handleNavClick} class="flex-1">
                    <h1
                        class="inline-flex items-center gap-2 px-2 text-lg font-semibold tracking-tight"
                    >
                        <CuboidIcon class="size-5" />
                        <span>modelctl</span>
                        <span
                            class="rounded-md border border-sidebar-border bg-sidebar-accent/50 px-1.5 py-0.5 text-[10px] font-medium text-sidebar-foreground/70 leading-none"
                        >
                            {import.meta.env.VITE_VERSION || "v0.2"}
                        </span>
                    </h1>
                </a>

                <Button
                    class="rounded-full md:hidden"
                    variant="ghost"
                    size="icon"
                    onclick={() => sidebar.toggle()}
                >
                    <XIcon class="size-4" />
                    <span class="sr-only">Close sidebar</span>
                </Button>
            </div>
        </Sidebar.Header>

        <!-- ── Navigation ─────────────────────────────────── -->
        <Sidebar.Content class="flex-1 overflow-y-auto">
            <Sidebar.Group class="p-0 px-3">
                <Sidebar.GroupLabel>Navigation</Sidebar.GroupLabel>
                <Sidebar.GroupContent>
                    <Sidebar.Menu>
                        {#each navItems as item (item.title)}
                            {@const active = isActive(item.url)}
                            <Sidebar.MenuItem
                                class="group/menu-item mb-1 p-0"
                                data-active={active || undefined}
                            >
                                <Sidebar.MenuButton isActive={active}>
                                    {#snippet child({ props })}
                                        <a
                                            href={item.url}
                                            {...props}
                                            onclick={handleNavClick}
                                            class="relative flex w-full items-center gap-3 px-3 py-2"
                                        >
                                            {#if active}
                                                <span
                                                    class="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-sidebar-foreground"
                                                ></span>
                                            {/if}
                                            <item.icon
                                                class="size-4 shrink-0 text-sidebar-foreground"
                                                style="opacity: {active
                                                    ? 1
                                                    : 0.6};"
                                            />
                                            <span
                                                class="text-sm text-sidebar-foreground"
                                                class:font-medium={active}
                                                class:opacity-60={!active}
                                            >
                                                {item.title}
                                            </span>
                                            {#if item.title === "Models" && modelCount !== null}
                                                <Badge
                                                    variant="secondary"
                                                    class="ml-auto h-5 min-w-5 rounded-md px-1.5 text-[11px] font-medium tabular-nums"
                                                >
                                                    {modelCount}
                                                </Badge>
                                            {/if}
                                        </a>
                                    {/snippet}
                                </Sidebar.MenuButton>
                            </Sidebar.MenuItem>
                        {/each}
                    </Sidebar.Menu>
                </Sidebar.GroupContent>
            </Sidebar.Group>

            <!-- ── Spacer ──────────────────────────────────── -->
            <div class="px-3 py-1">
                <Separator class="bg-sidebar-border/50" />
            </div>

            <!-- ── System ──────────────────────────────────── -->
            <Sidebar.Group class="p-0 px-3">
                <Sidebar.GroupLabel>System</Sidebar.GroupLabel>
                <Sidebar.GroupContent>
                    <Sidebar.Menu>
                        {@const active = isActive("/system")}
                        <Sidebar.MenuItem
                            class="group/menu-item mb-1 p-0"
                            data-active={active || undefined}
                        >
                            <Sidebar.MenuButton isActive={active}>
                                {#snippet child({ props })}
                                    <a
                                        href="/system"
                                        {...props}
                                        onclick={handleNavClick}
                                        class="relative flex w-full items-center gap-3 px-3 py-2"
                                    >
                                        {#if active}
                                            <span
                                                class="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-sidebar-foreground"
                                            ></span>
                                        {/if}
                                        <ActivityIcon
                                            class="size-4 shrink-0 text-sidebar-foreground"
                                            style="opacity: {active ? 1 : 0.6};"
                                        />
                                        <span
                                            class="text-sm text-sidebar-foreground"
                                            class:font-medium={active}
                                            class:opacity-60={!active}
                                        >
                                            System
                                        </span>
                                    </a>
                                {/snippet}
                            </Sidebar.MenuButton>
                        </Sidebar.MenuItem>
                    </Sidebar.Menu>

                    <!-- ── Disk Usage ─────────────────────────── -->
                    <div class="px-3 pb-2 pt-1">
                        <div
                            class="flex items-center justify-between text-[11px] text-sidebar-foreground/60"
                        >
                            <span>Disk Usage</span>
                            <span>{diskPct}%</span>
                        </div>
                        <div
                            class="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-sidebar-accent/60"
                        >
                            <div
                                class="h-full rounded-full transition-all duration-500 ease-out"
                                style="width: {diskPct}%; background-color: {diskPct >
                                80
                                    ? 'var(--destructive)'
                                    : diskPct > 60
                                      ? 'var(--sidebar-ring)'
                                      : 'var(--sidebar-primary)'};"
                            ></div>
                        </div>
                        <p class="mt-1 text-[11px] text-sidebar-foreground/40">
                            {diskUsed} / {diskTotal} used
                        </p>
                    </div>
                </Sidebar.GroupContent>
            </Sidebar.Group>
        </Sidebar.Content>

        <!-- ── Footer ─────────────────────────────────────── -->
        <Sidebar.Footer class="border-t border-sidebar-border/50 p-3">
            <p class="px-2 text-[11px] text-sidebar-foreground/40">
                &copy; modelctl
            </p>
        </Sidebar.Footer>
    </div>
</Sidebar.Root>
