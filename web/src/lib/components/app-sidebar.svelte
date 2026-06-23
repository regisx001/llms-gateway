<script lang="ts">
    import * as Sidebar from "$lib/components/ui/sidebar/index.js";
    import { useSidebar } from "$lib/components/ui/sidebar/context.svelte.js";
    import { page } from "$app/state";
    import { Button } from "$lib/components/ui/button";

    import HouseIcon from "@lucide/svelte/icons/house";
    import SearchIcon from "@lucide/svelte/icons/search";
    import CuboidIcon from "@lucide/svelte/icons/cuboid";
    import ActivityIcon from "@lucide/svelte/icons/activity";
    import XIcon from "@lucide/svelte/icons/x";

    const sidebar = useSidebar();

    const navItems = [
        { title: "Dashboard", url: "/", icon: HouseIcon },
        { title: "Search", url: "/search", icon: SearchIcon },
        { title: "Models", url: "/models", icon: CuboidIcon },
        { title: "System", url: "/system", icon: ActivityIcon },
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
</script>

<Sidebar.Root>
    <div class="flex h-full flex-col">
        <!-- ── Header ─────────────────────────────────────── -->
        <Sidebar.Header class="gap-4 bg-sidebar/50 p-3 backdrop-blur-lg md:pt-4 md:pb-2">
            <div class="flex items-center justify-between">
                <a href="/" onclick={handleNavClick}>
                    <h1 class="inline-flex items-center gap-1 px-2 text-xl font-semibold">
                        <CuboidIcon class="size-5" />
                        modelctl
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
                            <Sidebar.MenuItem class="mb-1 p-0">
                                <Sidebar.MenuButton isActive={isActive(item.url)}>
                                    {#snippet child({ props })}
                                        <a
                                            href={item.url}
                                            {...props}
                                            onclick={handleNavClick}
                                        >
                                            <item.icon />
                                            <span>{item.title}</span>
                                        </a>
                                    {/snippet}
                                </Sidebar.MenuButton>
                            </Sidebar.MenuItem>
                        {/each}
                    </Sidebar.Menu>
                </Sidebar.GroupContent>
            </Sidebar.Group>
        </Sidebar.Content>

        <!-- ── Footer ─────────────────────────────────────── -->
        <Sidebar.Footer class="border-t p-3">
            <p class="px-2 text-xs text-muted-foreground">
                {import.meta.env.VITE_VERSION || "modelctl v0.2"}
            </p>
        </Sidebar.Footer>
    </div>
</Sidebar.Root>
