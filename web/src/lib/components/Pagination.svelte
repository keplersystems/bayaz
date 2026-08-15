<script lang="ts">
	import ChevronLeft from 'lucide-svelte/icons/chevron-left';
	import ChevronRight from 'lucide-svelte/icons/chevron-right';

	let {
		total,
		offset,
		perPage,
		makeHref
	}: {
		total: number;
		offset: number;
		perPage: number;
		makeHref: (offset: number) => string;
	} = $props();

	const first = $derived(total === 0 ? 0 : offset + 1);
	const last = $derived(Math.min(offset + perPage, total));
	const previous = $derived(Math.max(0, offset - perPage));
	const next = $derived(offset + perPage);
</script>

{#if total > 0}
	<nav
		class="mt-10 flex items-center justify-between border-t border-outline-variant/60 pt-4"
		aria-label="Pagination"
	>
		{#if offset > 0}
			<a
				href={makeHref(previous)}
				class="flex items-center gap-1 rounded-m3-sm px-2 py-1 text-sm font-medium
					text-primary transition-colors hover:bg-primary/8"
			>
				<ChevronLeft class="size-4" aria-hidden="true" />Previous
			</a>
		{:else}
			<span class="flex items-center gap-1 px-2 py-1 text-sm text-outline" aria-hidden="true">
				<ChevronLeft class="size-4" />Previous
			</span>
		{/if}
		<span class="text-sm text-on-surface-variant tabular-nums"
			>{first}–{last} of {total.toLocaleString()}</span
		>
		{#if next < total}
			<a
				href={makeHref(next)}
				class="flex items-center gap-1 rounded-m3-sm px-2 py-1 text-sm font-medium
					text-primary transition-colors hover:bg-primary/8"
			>
				Next<ChevronRight class="size-4" aria-hidden="true" />
			</a>
		{:else}
			<span class="flex items-center gap-1 px-2 py-1 text-sm text-outline" aria-hidden="true">
				Next<ChevronRight class="size-4" />
			</span>
		{/if}
	</nav>
{/if}
