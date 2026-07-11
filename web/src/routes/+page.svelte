<script lang="ts">
	import { onMount } from "svelte";
	import { config } from "$lib/config";
	import { goto } from "$app/navigation";

	import * as Card from "$lib/components/ui/card";
	import { Button } from "$lib/components/ui/button";
	import { Badge } from "$lib/components/ui/badge";
	import * as Table from "$lib/components/ui/table";
	import { Skeleton } from "$lib/components/ui/skeleton";
	import { Input } from "$lib/components/ui/input";
	import * as Alert from "$lib/components/ui/alert";
	import { Separator } from "$lib/components/ui/separator";
	import { Spinner } from "$lib/components/ui/spinner";

	import CuboidIcon from "@lucide/svelte/icons/cuboid";
	import DatabaseIcon from "@lucide/svelte/icons/database";
	import CpuIcon from "@lucide/svelte/icons/cpu";
	import SearchIcon from "@lucide/svelte/icons/search";
	import Trash2Icon from "@lucide/svelte/icons/trash-2";
	import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
	import AlertCircleIcon from "@lucide/svelte/icons/alert-circle";
	import ActivityIcon from "@lucide/svelte/icons/activity";

	// ── State ────────────────────────────────────────────────────────

	let loading = $state(true);
	let error = $state<string | null>(null);
	let healthStatus = $state<string | null>(null);
	let systemInfo = $state<{
		version: string;
		storage_used: string;
		storage_free: string;
		models_count: number;
		active_models: string[];
	} | null>(null);
	let models = $state<
		{
			id: string;
			name: string;
			type: string;
			status: string;
			size: string;
		}[]
	>([]);
	let searchQuery = $state("");

	// ── Derived ──────────────────────────────────────────────────────

	let installedCount = $derived(
		models.filter((m) => m.status === "installed" || m.status === "active")
			.length,
	);

	// ── Helpers ──────────────────────────────────────────────────────

	function sizeStr(bytes: number): string {
		const units = ["B", "KB", "MB", "GB", "TB"];
		let n = bytes;
		for (const unit of units) {
			if (n < 1024) return `${n.toFixed(1)} ${unit}`;
			n /= 1024;
		}
		return `${n.toFixed(1)} PB`;
	}

	function typeColor(type: string): string {
		const colors: Record<string, string> = {
			chat: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
			embedding: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
			deranker: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
			vision: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
			experimental: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
			"tool-calling":
				"bg-orange-500/15 text-orange-600 dark:text-orange-400",
		};
		return colors[type] ?? "bg-muted text-muted-foreground";
	}

	async function fetchJson<T>(path: string): Promise<T> {
		const res = await fetch(`${config.apiBase}${path}`);
		if (!res.ok) {
			const body = await res
				.json()
				.catch(() => ({ detail: res.statusText }));
			throw new Error(body.detail || `HTTP ${res.status}`);
		}
		return res.json();
	}

	// ── Load ─────────────────────────────────────────────────────────

	async function loadData() {
		loading = true;
		error = null;
		try {
			const [health, info, modelList] = await Promise.all([
				fetchJson<{ status: string; version: string }>("/health"),
				fetchJson<{
					version: string;
					storage_used: string;
					storage_free: string;
					models_count: number;
					active_models: string[];
				}>("/api/v1/system/info"),
				fetchJson<{
					models: {
						id: string;
						name: string;
						type: string;
						status: string;
						artifacts: { size: number }[];
					}[];
				}>("/api/v1/models"),
			]);

			healthStatus = health.status;
			systemInfo = info;
			models = modelList.models.map((m) => ({
				id: m.id,
				name: m.name,
				type: m.type,
				status: m.status,
				size: sizeStr(m.artifacts.reduce((acc, a) => acc + a.size, 0)),
			}));
		} catch (e) {
			error = e instanceof Error ? e.message : "Failed to load data";
			healthStatus = "error";
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>Dashboard — modelctl</title>
	<meta
		name="description"
		content="Model management dashboard — monitor installed models, storage usage, and API status at a glance."
	/>
	<meta
		name="keywords"
		content="modelctl, llama.cpp, GGUF, model management, dashboard, HuggingFace"
	/>
	<meta property="og:title" content="Dashboard — modelctl" />
	<meta
		property="og:description"
		content="Model management dashboard — monitor installed models, storage usage, and API status."
	/>
	<meta property="og:type" content="website" />
	<meta name="twitter:card" content="summary" />
	<meta name="twitter:title" content="Dashboard — modelctl" />
	<meta
		name="twitter:description"
		content="Model management dashboard — monitor installed models, storage usage, and API status."
	/>
</svelte:head>

<div class="mx-auto flex w-full flex-col gap-6 p-6">
	<!-- ── Header ─────────────────────────────────────────────── -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-semibold">Dashboard</h1>
			<p class="text-sm text-muted-foreground">
				Model Management Dashboard
			</p>
		</div>
		<div class="flex items-center gap-2">
			{#if healthStatus === "ok"}
				<Badge variant="outline" class="gap-1.5">
					<span class="relative flex size-2">
						<span
							class="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75"
						></span>
						<span
							class="relative inline-flex size-2 rounded-full bg-emerald-500"
						></span>
					</span>
					Online
				</Badge>
			{:else if loading}
				<Badge variant="outline" class="gap-1.5">
					<Spinner class="size-3" />
					Connecting…
				</Badge>
			{:else}
				<Badge variant="destructive" class="gap-1.5">
					<AlertCircleIcon class="size-3.5" />
					Offline
				</Badge>
			{/if}
			<Button variant="outline" size="icon" onclick={loadData}>
				<RefreshCwIcon class="size-4" />
			</Button>
		</div>
	</div>

	<!-- ── Error Banner ──────────────────────────────────────────── -->
	{#if error}
		<Alert.Root variant="destructive">
			<AlertCircleIcon />
			<Alert.Title>Connection Error</Alert.Title>
			<Alert.Description>
				{error}
			</Alert.Description>
		</Alert.Root>
	{/if}

	<!-- ── Stats Cards ──────────────────────────────────────────── -->
	{#if loading}
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
			{#each Array(3) as _}
				<Card.Root size="sm">
					<Card.Header>
						<Skeleton class="mb-2 h-4 w-20" />
						<Skeleton class="h-8 w-16" />
					</Card.Header>
				</Card.Root>
			{/each}
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
			<Card.Root size="sm">
				<Card.Header
					class="flex-row items-center justify-between gap-3"
				>
					<div>
						<Card.Description>Installed Models</Card.Description>
						<Card.Title class="mt-1 text-2xl tabular-nums">
							{installedCount}
						</Card.Title>
					</div>
					<div
						class="flex size-10 items-center justify-center rounded-lg bg-primary/10"
					>
						<CuboidIcon class="size-5 text-primary" />
					</div>
				</Card.Header>
			</Card.Root>

			<Card.Root size="sm">
				<Card.Header
					class="flex-row items-center justify-between gap-3"
				>
					<div>
						<Card.Description>Storage Used</Card.Description>
						<Card.Title class="mt-1 text-2xl tabular-nums">
							{systemInfo?.storage_used ?? "—"}
						</Card.Title>
					</div>
					<div
						class="flex size-10 items-center justify-center rounded-lg bg-primary/10"
					>
						<DatabaseIcon class="size-5 text-primary" />
					</div>
				</Card.Header>
			</Card.Root>

			<Card.Root size="sm">
				<Card.Header
					class="flex-row items-center justify-between gap-3"
				>
					<div>
						<Card.Description>API Status</Card.Description>
						<Card.Title
							class="mt-1 flex items-center gap-2 text-lg"
						>
							{#if healthStatus === "ok"}
								<span class="relative flex size-2">
									<span
										class="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75"
									></span>
									<span
										class="relative inline-flex size-2 rounded-full bg-emerald-500"
									></span>
								</span>
								Running
							{:else}
								<span class="size-2 rounded-full bg-destructive"
								></span>
								Offline
							{/if}
						</Card.Title>
					</div>
					<div
						class="flex size-10 items-center justify-center rounded-lg bg-primary/10"
					>
						<ActivityIcon class="size-5 text-primary" />
					</div>
				</Card.Header>
			</Card.Root>
		</div>
	{/if}

	<!-- ── Search Bar ────────────────────────────────────────────── -->
	<Card.Root size="sm">
		<Card.Content>
			<form
				class="flex gap-3"
				onsubmit={(e) => {
					e.preventDefault();
					if (searchQuery.trim()) {
						goto(
							`/search?q=${encodeURIComponent(searchQuery.trim())}`,
						);
					}
				}}
			>
				<div class="relative flex-1">
					<SearchIcon
						class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground/50"
					/>
					<Input
						bind:value={searchQuery}
						placeholder="Search HuggingFace for GGUF models…"
						class="pl-9"
					/>
				</div>
				<Button type="submit" disabled={!searchQuery.trim()}>
					<SearchIcon class="size-4" />
					Search
				</Button>
			</form>
		</Card.Content>
	</Card.Root>

	<!-- ── Installed Models ──────────────────────────────────────── -->
	<Card.Root>
		<Card.Header>
			<Card.Title>Installed Models</Card.Title>
			<Card.Description>
				{models.length} model{models.length !== 1 ? "s" : ""} in registry
			</Card.Description>
		</Card.Header>
		<Card.Content>
			{#if loading}
				<div class="flex flex-col gap-3">
					{#each Array(3) as _}
						<Skeleton class="h-12 w-full" />
					{/each}
				</div>
			{:else if models.length === 0}
				<div class="flex flex-col items-center gap-2 py-10 text-center">
					<CuboidIcon class="size-10 text-muted-foreground/50" />
					<p class="text-sm text-muted-foreground">
						No models installed yet.
					</p>
					<p class="text-xs text-muted-foreground">
						Use the search bar above to find and install models from
						HuggingFace.
					</p>
				</div>
			{:else}
				<Table.Root>
					<Table.Header>
						<Table.Row>
							<Table.Head>Name</Table.Head>
							<Table.Head>Type</Table.Head>
							<Table.Head>Size</Table.Head>
							<Table.Head>Status</Table.Head>
							<Table.Head class="text-right">Actions</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each models as m (m.id)}
							<Table.Row>
								<Table.Cell class="font-medium">
									{m.name}
								</Table.Cell>
								<Table.Cell>
									<span
										class="inline-block rounded-md px-2.5 py-1 text-xs font-medium capitalize {typeColor(
											m.type,
										)}"
									>
										{m.type}
									</span>
								</Table.Cell>
								<Table.Cell
									class="tabular-nums text-muted-foreground"
								>
									{m.size}
								</Table.Cell>
								<Table.Cell>
									{#if m.status === "installed" || m.status === "active"}
										<span
											class="inline-flex items-center gap-1.5"
										>
											<span class="relative flex size-2">
												<span
													class="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75"
												></span>
												<span
													class="relative inline-flex size-2 rounded-full bg-emerald-500"
												></span>
											</span>
											<span
												class="text-sm font-medium text-emerald-500"
											>
												{m.status === "active"
													? "Active"
													: "Installed"}
											</span>
										</span>
									{:else if m.status === "downloading"}
										<span
											class="inline-flex items-center gap-1 text-sm text-muted-foreground"
										>
											<Spinner class="size-3" />
											Downloading
										</span>
									{:else if m.status === "error"}
										<Badge variant="destructive"
											>Error</Badge
										>
									{:else}
										<Badge variant="outline"
											>{m.status}</Badge
										>
									{/if}
								</Table.Cell>
								<Table.Cell class="text-right">
									<div class="flex justify-end gap-1">
										<Button
											variant="ghost"
											size="sm"
											class="text-destructive/70 hover:text-destructive"
											onclick={() => {
												if (
													confirm(
														`Remove model "${m.name}"?`,
													)
												) {
													fetch(
														`${config.apiBase}/api/v1/models/${m.id}`,
														{
															method: "DELETE",
														},
													).then(() => loadData());
												}
											}}
										>
											<Trash2Icon class="size-3.5" />
										</Button>
									</div>
								</Table.Cell>
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			{/if}
		</Card.Content>
	</Card.Root>

	<!-- ── Footer ────────────────────────────────────────────────── -->
	<footer class="flex items-center gap-3 text-xs text-muted-foreground">
		<span>modelctl {systemInfo?.version ?? "—"}</span>
		<span class="text-muted-foreground/30">&middot;</span>
		<span>
			{new Date().toLocaleDateString("en-US", {
				year: "numeric",
				month: "short",
				day: "numeric",
				hour: "2-digit",
				minute: "2-digit",
			})}
		</span>
	</footer>
</div>
