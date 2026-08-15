<script lang="ts">
	import type { PageData } from './$types';
	import type { SearchKind } from '$lib/api';
	import FilterRow from '$lib/components/FilterRow.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import ScriptText from '$lib/components/ScriptText.svelte';
	import SearchBox from '$lib/components/SearchBox.svelte';
	import StateMessage from '$lib/components/StateMessage.svelte';
	import { formatCount } from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const KIND_LABEL: Record<SearchKind, string> = {
		works: 'works',
		entries: 'words',
		poets: 'poets'
	};

	const sites = ['rekhta', 'hindwi', 'sufinama', 'rekhtadictionary'];

	function href(extra: Record<string, string | null>) {
		const params = new URLSearchParams({ q: data.q });
		const merged = { kind: data.kind, site: data.site, ...extra };
		for (const [key, value] of Object.entries(merged)) if (value) params.set(key, value);
		return `/search?${params}`;
	}

	function hitHref(kind: string, site: string, slug: string) {
		const path = kind === 'entry' ? 'word' : kind === 'poet' ? 'poet' : 'work';
		return `/${path}/${site}/${encodeURIComponent(slug)}`;
	}
</script>

<svelte:head><title>{data.q ? `${data.q} · search · bayaz` : 'Search · bayaz'}</title></svelte:head>

<section class="mx-auto max-w-3xl px-4 py-10 sm:px-6">
	<h1 class="font-serif text-3xl text-on-surface">Search</h1>
	<div class="mt-5">
		{#key data.q + data.kind}
			<SearchBox
				size="lg"
				initial={data.q}
				autofocus
				kind={data.kind === 'poets' ? undefined : data.kind}
				placeholder="A poet, a ghazal, a word"
			/>
		{/key}
	</div>

	{#if data.q}
		<div class="mt-6 space-y-1.5 border-y border-outline-variant/70 py-3">
			<FilterRow
				label="In"
				options={['works', 'entries', 'poets']}
				current={data.kind}
				href={(kind) => href({ kind, site: null })}
				labels={KIND_LABEL}
			/>
			<FilterRow
				label="Site"
				options={[null, ...sites]}
				current={data.site}
				href={(site) => href({ site })}
			/>
		</div>
	{/if}

	{#if !data.q}
		<div class="mt-10">
			<StateMessage
				kind="search"
				title="Nothing searched for yet"
				hint="Verses, dictionary headwords and poets, in any script."
			/>
		</div>
	{:else if data.results && data.results.items.length === 0}
		<div class="mt-10">
			<StateMessage
				kind="search"
				title={`Nothing found for “${data.q}”`}
				hint="Try another spelling, or another script: Roman, Devanagari or Nastaliq."
			/>
		</div>
	{:else if data.results}
		<p class="mt-4 text-sm text-on-surface-variant tabular-nums">
			{formatCount(data.results.total)}
			{KIND_LABEL[data.kind]}
		</p>

		<ul class="mt-2 divide-y divide-outline-variant/70">
			{#each data.results.items as hit (hit.kind + hit.site + hit.slug)}
				<li>
					<a href={hitHref(hit.kind, hit.site, hit.slug)} class="group block py-4">
						<p
							class="font-serif text-lg leading-snug text-balance text-on-surface transition-colors group-hover:text-primary"
						>
							<ScriptText text={hit.title?.trim() || hit.snippet.slice(0, 60)} />
						</p>
						{#if hit.snippet.trim() && hit.snippet.trim() !== hit.title?.trim()}
							<p class="mt-1 line-clamp-2 text-sm leading-relaxed text-on-surface-variant">
								<ScriptText text={hit.snippet} />
							</p>
						{/if}
						{#if !data.site}
							<p class="mt-1 text-sm text-on-surface-faint">{hit.site}</p>
						{/if}
					</a>
				</li>
			{/each}
		</ul>

		<Pagination
			total={data.results.total}
			offset={data.offset}
			perPage={data.perPage}
			makeHref={(offset) => href({ offset: String(offset) })}
		/>
	{/if}
</section>
