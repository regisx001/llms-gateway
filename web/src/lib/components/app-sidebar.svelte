<script lang="ts">
    import * as Sidebar from "$lib/components/ui/sidebar/index.js";
    import { page } from "$app/stores";

    import HouseIcon from "@lucide/svelte/icons/house";
    import SearchIcon from "@lucide/svelte/icons/search";
    import CuboidIcon from "@lucide/svelte/icons/cuboid";
    import ActivityIcon from "@lucide/svelte/icons/activity";

    const navItems = [
        { title: "Dashboard", url: "/", icon: HouseIcon },
        { title: "Search", url: "/search", icon: SearchIcon },
        { title: "Models", url: "/models", icon: CuboidIcon },
        { title: "System", url: "/system", icon: ActivityIcon },
    ];

    function isActive(url: string): boolean {
        return $page.url.pathname === url;
    }
</script>

<Sidebar.Root>
    <Sidebar.Header>
        <Sidebar.Menu>
            <Sidebar.MenuItem>
                <Sidebar.MenuButton>
                    {#snippet child({ props })}
                        <a href="/" {...props}>
                            <CuboidIcon />
                            <span>modelctl</span>
                        </a>
                    {/snippet}
                </Sidebar.MenuButton>
            </Sidebar.MenuItem>
        </Sidebar.Menu>
    </Sidebar.Header>
    <Sidebar.Content>
        <Sidebar.Group>
            <Sidebar.GroupLabel>Navigation</Sidebar.GroupLabel>
            <Sidebar.GroupContent>
                <Sidebar.Menu>
                    {#each navItems as item (item.title)}
                        <Sidebar.MenuItem>
                            <Sidebar.MenuButton isActive={isActive(item.url)}>
                                {#snippet child({ props })}
                                    <a href={item.url} {...props}>
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
    <Sidebar.Rail />
</Sidebar.Root>
