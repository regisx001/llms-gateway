<script lang="ts">
	import { onMount } from "svelte";
	import { config } from "$lib/config";
	import logo from "$lib/assets/favicon.svg";

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
	import ActivityIcon from "@lucide/svelte/icons/activity";
	import DatabaseIcon from "@lucide/svelte/icons/database";
	import CpuIcon from "@lucide/svelte/icons/cpu";
	import SearchIcon from "@lucide/svelte/icons/search";
	import PlayIcon from "@lucide/svelte/icons/play";
	import SquareIcon from "@lucide/svelte/icons/square";
	import Trash2Icon from "@lucide/svelte/icons/trash-2";
	import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
	import AlertCircleIcon from "@lucide/svelte/icons/alert-circle";

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

	// Derived: active model name for display
	let activeModelName = $derived(systemInfo?.active_models?.[0] ?? null);

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

	async function postAction(path: string) {
		await fetch(`${config.apiBase}${path}`, { method: "POST" });
		await loadData();
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

<div class="mx-auto flex max-w-6xl flex-col gap-6 p-6">
	<!-- ── Header ─────────────────────────────────────────────── -->
	<header class="flex items-center justify-between">
		<div class="flex items-center gap-3">
			<img src={logo} alt="modelctl" class="size-10" />
			<div>
				<h1 class="text-xl font-semibold">modelctl</h1>
				<p class="text-sm text-muted-foreground">
					Model Management Dashboard
				</p>
			</div>
		</div>
		<div class="flex items-center gap-3">
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
					API Online
				</Badge>
			{:else if loading}
				<Badge variant="outline" class="gap-1.5">
					<Spinner />
					Connecting…
				</Badge>
			{:else}
				<Badge variant="destructive" class="gap-1.5">
					<AlertCircleIcon
						data-icon="inline-start"
						class="size-3.5"
					/>
					Offline
				</Badge>
			{/if}
			<Button variant="outline" size="icon" onclick={() => loadData()}>
				<RefreshCwIcon class="size-4" />
			</Button>
		</div>
	</header>

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
	<div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
		{#if loading}
			{#each Array(4) as _}
				<Card.Root>
					<Card.Header>
						<Skeleton class="mb-2 h-4 w-20" />
						<Skeleton class="h-8 w-16" />
					</Card.Header>
				</Card.Root>
			{/each}
		{:else}
			<Card.Root>
				<Card.Header>
					<Card.Description class="flex items-center gap-2 text-sm">
						<CuboidIcon class="size-4" />
						Models
					</Card.Description>
					<Card.Title class="text-3xl font-bold tabular-nums">
						{systemInfo?.models_count ?? "?"}
					</Card.Title>
				</Card.Header>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Description class="flex items-center gap-2 text-sm">
						<ActivityIcon class="size-4" />
						Active
					</Card.Description>
					<Card.Title class="truncate text-xl font-bold">
						{activeModelName || "—"}
					</Card.Title>
				</Card.Header>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Description class="flex items-center gap-2 text-sm">
						<DatabaseIcon class="size-4" />
						Storage
					</Card.Description>
					<Card.Title class="text-xl font-bold tabular-nums">
						{systemInfo?.storage_used ?? "?"}
						<span
							class="text-base font-normal text-muted-foreground"
						>
							/ {systemInfo?.storage_free ?? "?"}
						</span>
					</Card.Title>
				</Card.Header>
			</Card.Root>

			<Card.Root>
				<Card.Header>
					<Card.Description class="flex items-center gap-2 text-sm">
						<CpuIcon class="size-4" />
						llama.cpp
					</Card.Description>
					<Card.Title
						class="flex items-center gap-2 text-base font-bold"
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
				</Card.Header>
			</Card.Root>
		{/if}
	</div>

	<!-- ── Search Bar ────────────────────────────────────────────── -->
	<Card.Root>
		<Card.Header>
			<Card.Title>Search HuggingFace</Card.Title>
			<Card.Description>
				Find and install GGUF models from the HuggingFace Hub.
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<form
				class="flex gap-2"
				onsubmit={(e) => {
					e.preventDefault();
					if (searchQuery.trim()) {
						window.location.href = `/search?q=${encodeURIComponent(searchQuery.trim())}`;
					}
				}}
			>
				<div class="relative flex-1">
					<SearchIcon
						class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
					/>
					<Input
						bind:value={searchQuery}
						placeholder="e.g. gemma, llama, nomic-embed…"
						class="pl-9"
					/>
				</div>
				<Button type="submit" disabled={!searchQuery.trim()}>
					<SearchIcon data-icon="inline-start" class="size-4" />
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
								<Table.Cell
									class="capitalize text-muted-foreground"
								>
									{m.type}
								</Table.Cell>
								<Table.Cell
									class="tabular-nums text-muted-foreground"
								>
									{m.size}
								</Table.Cell>
								<Table.Cell>
									{#if m.status === "installed"}
										<Badge variant="secondary"
											>Installed</Badge
										>
									{:else if m.status === "active"}
										<Badge>Active</Badge>
									{:else if m.status === "downloading"}
										<Badge variant="outline" class="gap-1">
											<Spinner class="size-3" />
											Downloading
										</Badge>
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
										{#if m.status === "installed"}
											<Button
												variant="outline"
												size="sm"
												onclick={() =>
													postAction(
														`/api/v1/models/${m.id}/activate`,
													)}
											>
												<PlayIcon class="size-3.5" />
												Activate
											</Button>
										{/if}
										{#if activeModelName === m.id}
											<Button
												variant="outline"
												size="sm"
												onclick={() =>
													postAction(
														`/api/v1/models/${m.id}/deactivate`,
													)}
											>
												<SquareIcon class="size-3.5" />
												Deactivate
											</Button>
										{/if}
										<Button
											variant="outline"
											size="sm"
											class="text-destructive hover:text-destructive"
											onclick={() => {
												if (
													confirm(
														`Remove model "${m.name}"?`,
													)
												) {
													postAction(
														`/api/v1/models/${m.id}/deactivate`,
													);
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
	<footer
		class="flex items-center justify-between text-xs text-muted-foreground"
	>
		<p>modelctl {systemInfo?.version ?? "—"}</p>
		<Separator class="mx-3 h-4" decorative orientation="vertical" />
		<p>
			{new Date().toLocaleDateString("en-US", {
				year: "numeric",
				month: "short",
				day: "numeric",
				hour: "2-digit",
				minute: "2-digit",
			})}
		</p>
	</footer>
</div>
