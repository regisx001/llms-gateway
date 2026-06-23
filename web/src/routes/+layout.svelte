<script lang="ts">
	import "./layout.css";
	import favicon from "$lib/assets/favicon.svg";
	import { ModeWatcher } from "mode-watcher";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import AppSidebar from "$lib/components/app-sidebar.svelte";
	import DownloadNotification from "$lib/components/download-notification.svelte";

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>modelctl — Model Management</title>
</svelte:head>

<ModeWatcher defaultMode="dark" />

<Sidebar.Provider>
	<AppSidebar />
	<main class="min-h-screen w-full bg-background text-foreground antialiased">
		{@render children()}
	</main>
	<DownloadNotification />
</Sidebar.Provider>
