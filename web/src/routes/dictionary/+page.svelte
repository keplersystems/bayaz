<script lang="ts">
	import type { PageData } from './$types';
	import EntryRow from '$lib/components/EntryRow.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import SearchBox from '$lib/components/SearchBox.svelte';
	import FilterRow from '$lib/components/FilterRow.svelte';
	import StateMessage from '$lib/components/StateMessage.svelte';
	import { formatCount } from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const total = $derived(data.sites.reduce((n, s) => n + s.entries, 0));
</script>

<svelte:head><title>Dictionary · bayaz</title></svelte:head>

<section class="mx-auto max-w-3xl px-4 py-10">
	<header class="mb-8 text-center">
		<h1 class="font-serif text-3xl text-on-surface">The dictionary</h1>
		<p class="mx-auto mt-2 max-w-xl text-on-surface-variant">
			{formatCount(total)} headwords from the rekhtadictionary and its mirrors, each given in Roman, Devanagari
			and Nastaliq. In the reader, tap any word of a poem to land here.
		</p>
		<div class="mx-auto mt-6 max-w-xl">
			<SearchBox
				size="lg"
				kind="entries"
				placeholder="Look up a word…"
				ariaLabel="Search dictionary entries"
			/>
		</div>
	</header>

	<div class="border-y border-outline-variant/70 py-3">
		<FilterRow
			label="Site"
			options={[null, ...data.sites.map((s) => s.site)]}
			current={data.site}
			href={(site) => (site ? `/dictionary?site=${site}` : '/dictionary')}
			labels={Object.fromEntries(
				data.sites.map((s) => [s.site, `${s.site} · ${formatCount(s.entries)}`])
			)}
		/>
	</div>

	{#if data.entries.items.length === 0}
		<div class="mt-10">
			<StateMessage kind="empty" title="No entries" hint="The page has run past its end." />
		</div>
	{:else}
		<div class="mt-8">
			<EntryRow entries={data.entries.items} />
		</div>
		<Pagination
			total={data.entries.total}
			offset={data.offset}
			perPage={data.perPage}
			makeHref={(offset) => {
				const params = new URLSearchParams();
				if (data.site) params.set('site', data.site);
				params.set('offset', String(offset));
				return `?${params}`;
			}}
		/>
	{/if}
</section>
