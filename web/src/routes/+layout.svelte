<script lang="ts">
	import "./layout.css";
	import favicon from "$lib/assets/favicon.svg";

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>modelctl — Model Management</title>
</svelte:head>

<div class="min-h-screen bg-background text-foreground antialiased">
	{@render children()}
</div>
