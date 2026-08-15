<script lang="ts">
	import type { PageData } from './$types';
	import Pagination from '$lib/components/Pagination.svelte';
	import ScriptText from '$lib/components/ScriptText.svelte';
	import SearchBox from '$lib/components/SearchBox.svelte';
	import StateMessage from '$lib/components/StateMessage.svelte';
	import BookMarked from 'lucide-svelte/icons/book-marked';
	import Feather from 'lucide-svelte/icons/feather';
	import { formatCount } from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const tabs = [
		{ value: null, label: 'Everything' },
		{ value: 'works', label: 'Works' },
		{ value: 'entries', label: 'Words' }
	] as const;

	function tabHref(kind: string | null) {
		return `/search?q=${encodeURIComponent(data.q)}${kind ? `&kind=${kind}` : ''}`;
	}
</script>

<svelte:head><title>{data.q ? `${data.q} · search · bayaz` : 'Search · bayaz'}</title></svelte:head>

<section class="mx-auto max-w-3xl px-4 py-10">
	<header class="mb-8">
		<h1 class="font-serif text-3xl text-on-surface">Search</h1>
		<div class="mt-5">
			{#key data.q + (data.kind ?? '')}
				<SearchBox size="lg" initial={data.q} autofocus placeholder="A poet, a ghazal, a word…" />
			{/key}
		</div>
	</header>

	{#if !data.q}
		<StateMessage
			kind="search"
			title="Nothing searched for yet"
			hint="Titles, verses and dictionary headwords, in any script."
		/>
	{:else if data.results && data.results.items.length === 0}
		<StateMessage
			kind="search"
			title={`Nothing found for “${data.q}”`}
			hint="Try another spelling or script — Roman, Devanagari or Nastaliq."
		/>
	{:else if data.results}
		<nav class="mb-6 flex items-center gap-1" role="group" aria-label="Result type">
			{#each tabs as tab (tab.label)}
				<a
					href={tabHref(tab.value)}
					aria-current={data.kind === tab.value ? 'true' : undefined}
					class="rounded-m3-full px-3 py-1.5 text-sm font-medium transition-colors
						{data.kind === tab.value
						? 'bg-secondary-container text-on-secondary-container'
						: 'text-on-surface-variant hover:bg-surface-container-high'}"
				>
					{tab.label}
				</a>
			{/each}
			<span class="ml-auto text-sm text-on-surface-variant tabular-nums">
				{formatCount(data.results.total)} results
			</span>
		</nav>

		<ul class="divide-y divide-outline-variant">
			{#each data.results.items as hit (hit.site + hit.slug)}
				{@const isEntry = hit.kind === 'entry'}
				{@const href = isEntry
					? `/word/${hit.site}/${encodeURIComponent(hit.slug)}`
					: `/work/${hit.site}/${encodeURIComponent(hit.slug)}`}
				<li class="py-4">
					<a {href} class="group block">
						<div class="flex items-baseline justify-between gap-3">
							<span
								class="min-w-0 font-serif text-lg leading-snug text-on-surface
								transition-colors group-hover:text-primary"
							>
								<ScriptText text={hit.title?.trim() || hit.snippet.slice(0, 60)} />
							</span>
							<span
								class="inline-flex shrink-0 items-center gap-1.5 text-xs tracking-wide
								text-on-surface-variant uppercase"
							>
								{#if isEntry}<BookMarked class="size-3.5" aria-hidden="true" />{:else}<Feather
										class="size-3.5"
										aria-hidden="true"
									/>{/if}
								{hit.site}
							</span>
						</div>
						<p class="mt-1 line-clamp-2 text-sm leading-relaxed text-on-surface-variant">
							<ScriptText text={hit.snippet} />
						</p>
					</a>
				</li>
			{/each}
		</ul>

		<Pagination
			total={data.results.total}
			offset={data.offset}
			perPage={data.perPage}
			makeHref={(offset) => {
				const params = new URLSearchParams({ q: data.q });
				if (data.kind) params.set('kind', data.kind);
				params.set('offset', String(offset));
				return `?${params}`;
			}}
		/>
	{/if}
</section>
