<script lang="ts">
	import BookX from 'lucide-svelte/icons/book-x';
	import CloudOff from 'lucide-svelte/icons/cloud-off';
	import Feather from 'lucide-svelte/icons/feather';
	import SearchX from 'lucide-svelte/icons/search-x';

	let {
		kind = 'empty',
		title,
		hint,
		tone = 'empty'
	}: {
		kind?: 'empty' | 'search' | 'error' | 'feather';
		title: string;
		hint?: string;
		tone?: 'empty' | 'error';
	} = $props();

	const icons = { empty: BookX, search: SearchX, error: CloudOff, feather: Feather };
	const Icon = $derived(icons[kind]);
</script>

<div
	class="mx-auto flex max-w-md flex-col items-center gap-3 rounded-m3-lg border
		border-dashed border-outline-variant px-6 py-12 text-center {tone === 'error'
		? 'bg-error-container text-on-error-container'
		: 'text-on-surface-variant'}"
>
	<Icon class="size-8 opacity-70" aria-hidden="true" />
	<p class="text-lg font-medium text-on-surface">{title}</p>
	{#if hint}<p class="text-sm">{hint}</p>{/if}
</div>
