<script lang="ts">
	import BookOpen from 'lucide-svelte/icons/book-open';
	import type { SiteSummary } from '$lib/api';
	import { formatCount } from '$lib/scripts';

	let { sites }: { sites: SiteSummary[] } = $props();

	const blurb: Record<string, string> = {
		rekhta: 'The flagship: Urdu poetry, ghazals, nazms and couplets with word glosses.',
		hindwi: 'Hindi writing: kavita, dohe, folk song and prose, in Devanagari.',
		sufinama: 'Sufi verse across Persian and South Asian traditions.',
		rekhtadictionary: 'The dictionary itself, open at every headword.'
	};
</script>

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
	{#each sites as s (s.site)}
		<a
			href={s.works > 0 ? `/browse/${s.site}` : '/dictionary?site=rekhtadictionary'}
			class="group flex flex-col gap-2
				rounded-m3-lg border border-outline-variant bg-surface-container p-5 transition-colors hover:border-primary/50"
		>
			<div class="flex items-center justify-between">
				<h2 class="font-serif text-xl text-on-surface transition-colors group-hover:text-primary">
					{s.site}
				</h2>
				<BookOpen
					class="size-5 text-on-surface-faint transition-colors group-hover:text-primary"
					aria-hidden="true"
				/>
			</div>
			<p class="text-sm text-on-surface-variant">{blurb[s.site] ?? ''}</p>
			<p class="mt-auto text-sm text-on-surface-faint tabular-nums">
				{formatCount(s.works)} works
				{#if s.entries > 0}· {formatCount(s.entries)} entries{/if}
				{#if s.entities > 0}· {formatCount(s.entities)} poets{/if}
			</p>
		</a>
	{/each}
</div>
