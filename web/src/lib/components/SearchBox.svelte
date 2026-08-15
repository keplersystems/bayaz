<script lang="ts">
	import { goto } from '$app/navigation';
	import Search from 'lucide-svelte/icons/search';

	let {
		initial = '',
		size = 'md',
		autofocus = false,
		placeholder = 'Search works and words…',
		ariaLabel = 'Search the archive',
		kind
	}: {
		initial?: string;
		size?: 'md' | 'lg';
		autofocus?: boolean;
		placeholder?: string;
		ariaLabel?: string;
		kind?: 'works' | 'entries';
	} = $props();

	let input: HTMLInputElement | undefined = $state();

	$effect(() => {
		if (autofocus) input?.focus();
	});

	function submit(e: SubmitEvent) {
		e.preventDefault();
		const q = new FormData(e.currentTarget as HTMLFormElement).get('q');
		const query = String(q ?? '').trim();
		if (query) goto(`/search?q=${encodeURIComponent(query)}${kind ? `&kind=${kind}` : ''}`);
	}
</script>

<form
	role="search"
	onsubmit={submit}
	class="rounded-m3-full flex items-center gap-2 border border-transparent
		bg-surface-container px-4 transition-colors focus-within:border-primary {size === 'lg'
		? 'h-14 text-lg'
		: 'h-10 text-sm'}"
>
	<Search class="size-5 shrink-0 text-on-surface-variant" aria-hidden="true" />
	<input
		type="search"
		name="q"
		value={initial}
		bind:this={input}
		{placeholder}
		aria-label={ariaLabel}
		class="min-w-0 flex-1 bg-transparent text-on-surface outline-none
			placeholder:text-on-surface-variant"
	/>
	<button
		type="submit"
		class="rounded-m3-full hidden shrink-0 bg-primary px-4 py-1.5 text-sm font-medium
			text-on-primary sm:block">Search</button
	>
</form>
