<script lang="ts">
	import { goto } from '$app/navigation';
	import type { PageData } from './$types';
	import EntityCard from '$lib/components/EntityCard.svelte';
	import FilterRow from '$lib/components/FilterRow.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import StateMessage from '$lib/components/StateMessage.svelte';
	import Search from 'lucide-svelte/icons/search';
	import { formatCount } from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const sites = ['rekhta', 'hindwi', 'sufinama'];
	const types = ['poets', 'authors', 'publishers', 'translators', 'artists', 'editors'];

	function href(extra: Record<string, string | null>) {
		const params = new URLSearchParams();
		const merged = { site: data.site, type: data.entityType, q: data.q, ...extra };
		for (const [key, value] of Object.entries(merged)) if (value) params.set(key, value);
		const query = params.toString();
		return `/poets${query ? `?${query}` : ''}`;
	}

	function submit(e: SubmitEvent) {
		e.preventDefault();
		const value = String(new FormData(e.currentTarget as HTMLFormElement).get('q') ?? '').trim();
		// Dropping `offset` is deliberate: page 40 of the old result set means nothing here.
		goto(href({ q: value || null, offset: null }));
	}
</script>

<svelte:head><title>Poets · bayaz</title></svelte:head>

<section class="mx-auto max-w-4xl px-4 py-10 sm:px-6">
	<header class="mb-6">
		<h1 class="font-serif text-3xl text-on-surface">Poets and people</h1>
		<p class="mt-1 text-sm text-on-surface-variant">
			{formatCount(data.poets.total)}
			{data.q ? `matching “${data.q}”` : 'names across the archive'}: poets, authors, translators,
			publishers, artists and editors.
		</p>
	</header>

	<form
		role="search"
		onsubmit={submit}
		class="flex h-11 w-full items-center gap-2.5 rounded-full border border-outline-variant
			bg-surface-container px-4 transition-colors focus-within:border-primary sm:max-w-sm"
	>
		<Search class="size-4 shrink-0 text-on-surface-faint" aria-hidden="true" />
		<input
			type="search"
			name="q"
			value={data.q}
			placeholder="Find a name, in any script"
			aria-label="Search poets by name"
			class="min-w-0 flex-1 bg-transparent text-sm text-on-surface outline-none
				placeholder:text-on-surface-faint [&::-webkit-search-cancel-button]:appearance-none"
		/>
	</form>

	<div class="mt-4 space-y-1.5 border-y border-outline-variant/70 py-3">
		<FilterRow
			label="Site"
			options={[null, ...sites]}
			current={data.site}
			href={(site) => href({ site, offset: null })}
		/>
		<FilterRow
			label="Role"
			options={[null, ...types]}
			current={data.entityType}
			href={(type) => href({ type, offset: null })}
		/>
	</div>

	{#if data.poets.items.length === 0}
		<div class="mt-10">
			<StateMessage
				kind="empty"
				title="No one matches"
				hint={data.q ? 'Try another spelling, or another script.' : 'Try clearing the filters.'}
			/>
		</div>
	{:else}
		<div class="mt-6">
			<EntityCard entities={data.poets.items} showSite={!data.site} />
		</div>
		<Pagination
			total={data.poets.total}
			offset={data.offset}
			perPage={data.perPage}
			makeHref={(offset) => href({ offset: String(offset) })}
		/>
	{/if}
</section>
