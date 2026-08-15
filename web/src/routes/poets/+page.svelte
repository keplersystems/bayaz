<script lang="ts">
	import type { PageData } from './$types';
	import EntityCard from '$lib/components/EntityCard.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StateMessage from '$lib/components/StateMessage.svelte';
	import { formatCount } from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const sites = ['rekhta', 'hindwi', 'sufinama'];
	const types = ['poets', 'authors', 'publishers', 'translators', 'artists', 'editors'];

	function href(extra: Record<string, string | null>) {
		const params = new URLSearchParams();
		const merged = { site: data.site, type: data.entityType, ...extra };
		for (const [key, value] of Object.entries(merged)) if (value) params.set(key, value);
		const query = params.toString();
		return `/poets${query ? `?${query}` : ''}`;
	}

	const chip = 'rounded-m3-full px-3 py-1.5 text-sm font-medium capitalize transition-colors';
</script>

<svelte:head><title>Poets · bayaz</title></svelte:head>

<section class="mx-auto max-w-5xl px-4 py-10">
	<header class="mb-6">
		<h1 class="font-serif text-3xl text-on-surface">Poets &amp; people</h1>
		<p class="mt-1 text-sm text-on-surface-variant">
			{formatCount(data.poets.total)} names across the archive: poets, authors, translators, publishers,
			artists and editors.
		</p>
	</header>

	<div class="flex flex-wrap items-center gap-2" role="group" aria-label="Filter by site">
		<a
			href={href({ site: null })}
			class="chip {data.site
				? 'text-on-surface-variant hover:bg-surface-container-high'
				: 'bg-secondary-container text-on-secondary-container'}">All sites</a
		>
		{#each sites as s (s)}
			<a
				href={href({ site: s })}
				class="chip capitalize {data.site === s
					? 'bg-secondary-container text-on-secondary-container'
					: 'text-on-surface-variant hover:bg-surface-container-high'}">{s}</a
			>
		{/each}
	</div>
	<div
		class="mt-3 flex flex-wrap items-center gap-2 border-t border-outline-variant/60 pt-3"
		role="group"
		aria-label="Filter by role"
	>
		<a
			href={href({ type: null })}
			class="chip {data.entityType
				? 'text-on-surface-variant hover:bg-surface-container-high'
				: 'bg-secondary-container text-on-secondary-container'}">All roles</a
		>
		{#each types as t (t)}
			<a
				href={href({ type: t })}
				class="chip {data.entityType === t
					? 'bg-secondary-container text-on-secondary-container'
					: 'text-on-surface-variant hover:bg-surface-container-high'}">{t}</a
			>
		{/each}
	</div>

	{#if data.poets.items.length === 0}
		<div class="mt-10">
			<StateMessage kind="empty" title="No one matches" hint="Try clearing the filters." />
		</div>
	{:else}
		<div class="mt-8">
			<EntityCard entities={data.poets.items} />
		</div>
		<Pagination
			total={data.poets.total}
			offset={data.offset}
			perPage={data.perPage}
			makeHref={(offset) => {
				const params = new URLSearchParams();
				if (data.site) params.set('site', data.site);
				if (data.entityType) params.set('type', data.entityType);
				params.set('offset', String(offset));
				return `?${params}`;
			}}
		/>
	{/if}
</section>
