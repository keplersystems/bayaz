<script lang="ts">
	import { goto } from '$app/navigation';
	import Search from 'lucide-svelte/icons/search';

	let {
		initial = '',
		size = 'md',
		autofocus = false,
		placeholder = 'Search',
		ariaLabel = 'Search the archive',
		kind
	}: {
		initial?: string;
		/** `lg` is the page-level search; `md` sits in the header, where a submit button would
		 *  crowd the field until the placeholder truncates. Enter submits either way. */
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
	class="flex w-full items-center gap-2.5
		rounded-full border border-outline-variant bg-surface-container transition-colors focus-within:border-primary
		{size === 'lg' ? 'h-13 px-5 text-base' : 'h-9 px-3.5 text-sm'}"
>
	<Search
		class="shrink-0 text-on-surface-faint {size === 'lg' ? 'size-5' : 'size-4'}"
		aria-hidden="true"
	/>
	<input
		type="search"
		name="q"
		value={initial}
		bind:this={input}
		{placeholder}
		aria-label={ariaLabel}
		class="min-w-0 flex-1 bg-transparent text-on-surface outline-none
			placeholder:text-on-surface-faint [&::-webkit-search-cancel-button]:appearance-none"
	/>
</form>
