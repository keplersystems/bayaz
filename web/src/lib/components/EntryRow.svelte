<script lang="ts">
	import type { EntrySummary } from '$lib/api';
	import ScriptText from './ScriptText.svelte';

	let { entries }: { entries: EntrySummary[] } = $props();
</script>

<ul class="divide-y divide-outline-variant">
	{#each entries as entry (entry.site + entry.slug)}
		<li class="py-3.5">
			<a
				href="/word/{entry.site}/{encodeURIComponent(entry.slug)}"
				class="group flex flex-wrap items-baseline gap-x-4 gap-y-0.5"
			>
				{#if entry.headword}
					<span
						class="font-serif text-lg text-on-surface transition-colors group-hover:text-primary"
					>
						{entry.headword}
					</span>
				{/if}
				{#if entry.headword_urdu}
					<span class="text-on-surface-variant transition-colors group-hover:text-primary">
						<ScriptText text={entry.headword_urdu} />
					</span>
				{/if}
				{#if entry.headword_hindi}
					<span class="text-on-surface-variant transition-colors group-hover:text-primary">
						<ScriptText text={entry.headword_hindi} />
					</span>
				{/if}
				<span class="ml-auto text-xs tracking-wide text-outline uppercase">{entry.site}</span>
			</a>
		</li>
	{/each}
</ul>
