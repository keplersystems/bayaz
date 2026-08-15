<script lang="ts">
	import type { EntrySummary } from '$lib/api';
	import ArrowRight from 'lucide-svelte/icons/arrow-right';
	import LoaderCircle from 'lucide-svelte/icons/loader-circle';
	import ScriptText from './ScriptText.svelte';

	let {
		active,
		status,
		entry,
		onclose
	}: {
		active: { word: string; code: string; rect: DOMRect } | null;
		status: 'loading' | 'found' | 'none' | 'error';
		entry: EntrySummary | null;
		onclose: () => void;
	} = $props();

	let card: HTMLDivElement | undefined = $state();

	$effect(() => {
		if (!active || !card) return;
		const margin = 8;
		const { innerWidth, innerHeight } = window;
		let top = active.rect.bottom + margin;
		if (top + card.offsetHeight > innerHeight - margin) {
			top = active.rect.top - card.offsetHeight - margin;
		}
		let left = active.rect.left + active.rect.width / 2 - card.offsetWidth / 2;
		left = Math.min(Math.max(left, margin), innerWidth - card.offsetWidth - margin);
		card.style.top = `${top}px`;
		card.style.left = `${left}px`;
		card.style.visibility = 'visible';
	});
</script>

<svelte:window
	onkeydown={(e) => active && e.key === 'Escape' && onclose()}
	onpointerdown={(e) =>
		active && !(e.target instanceof Node && card?.contains(e.target)) && onclose()}
	onscroll={() => active && onclose()}
/>

{#if active}
	<div
		bind:this={card}
		role="dialog"
		aria-label="Word lookup"
		class="invisible fixed z-50 w-80 max-w-[calc(100vw-1rem)] rounded-m3-lg
			border border-outline-variant bg-surface-container-high p-4 text-on-surface shadow-xl"
		style="top: -1000px; left: -1000px"
	>
		<p class="font-serif text-xl leading-snug text-on-surface">
			<ScriptText text={active.word} />
		</p>

		{#if status === 'loading'}
			<p class="mt-2 flex items-center gap-2 text-sm text-on-surface-variant">
				<LoaderCircle class="size-4 animate-spin" aria-hidden="true" />Looking it up…
			</p>
		{:else if status === 'found' && entry}
			<div class="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-0.5">
				{#if entry.headword_urdu}
					<span class="text-nastaliq"><ScriptText text={entry.headword_urdu} /></span>
				{/if}
				{#if entry.headword_hindi}
					<span class="text-on-surface-variant"><ScriptText text={entry.headword_hindi} /></span>
				{/if}
			</div>
			<a
				href="/word/{entry.site}/{encodeURIComponent(entry.slug)}"
				class="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
			>
				Full entry<ArrowRight class="size-4" aria-hidden="true" />
			</a>
		{:else if status === 'none'}
			<p class="mt-2 text-sm text-on-surface-variant/80">No dictionary entry for this word.</p>
		{:else}
			<p class="mt-2 text-sm text-on-surface-variant">Couldn't reach the dictionary.</p>
		{/if}
	</div>
{/if}
