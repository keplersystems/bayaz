<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		term,
		script,
		children
	}: {
		/** The gloss shown on hover or focus. */
		term: string;
		/** Optional original-script form, shown beside the gloss. */
		script?: { text: string; lang: string };
		children: Snippet;
	} = $props();

	let open = $state(false);
</script>

<!-- Carries the same dotted underline the verse uses for a word with a dictionary entry, so
     the gesture a reader learns on the front page is the one the poems answer to. -->
<span class="relative inline-block">
	<button
		type="button"
		class="cursor-help underline decoration-outline
			decoration-dotted underline-offset-[0.3em] transition-colors hover:decoration-primary aria-expanded:decoration-primary"
		aria-expanded={open}
		onclick={() => (open = !open)}
		onmouseenter={() => (open = true)}
		onmouseleave={() => (open = false)}
		onfocus={() => (open = true)}
		onblur={() => (open = false)}
	>
		{@render children()}
	</button>
	{#if open}
		<span
			role="tooltip"
			class="absolute top-full left-1/2 z-30
				mt-2 w-max max-w-[min(20rem,80vw)] -translate-x-1/2 rounded-lg border border-outline-variant bg-surface-container
				px-3.5 py-2.5 text-left text-sm leading-relaxed font-normal text-on-surface-variant normal-case shadow-lg"
		>
			{#if script}
				<span lang={script.lang} class="mr-2 text-on-surface not-italic">{script.text}</span>
			{/if}{term}
		</span>
	{/if}
</span>
