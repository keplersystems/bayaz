<script lang="ts">
	import { page } from '$app/state';
	import StateMessage from '$lib/components/StateMessage.svelte';

	const message = $derived.by(() => {
		if (page.status === 404) return 'This page is not in the archive.';
		if (page.status >= 500) return 'The archive stumbled. Try again in a moment.';
		return page.error?.message ?? 'Something went wrong.';
	});
</script>

<svelte:head><title>{page.status} · bayaz</title></svelte:head>

<section class="mx-auto max-w-3xl px-4 py-16">
	<StateMessage
		kind="feather"
		title={page.status === 404 ? '404' : String(page.status)}
		hint={message}
	/>
	<p class="mt-6 text-center">
		<a href="/" class="text-primary hover:underline">Back to the reading room</a>
	</p>
</section>
