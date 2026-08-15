<script lang="ts">
	import type { PageData } from './$types';
	import SiteCards from '$lib/components/SiteCards.svelte';

	let { data }: { data: PageData } = $props();

	const libraries = $derived(data.sites.filter((s) => s.works > 0));
</script>

<svelte:head><title>Browse · bayaz</title></svelte:head>

<section class="mx-auto max-w-4xl px-4 py-10">
	<h1 class="font-serif text-3xl text-on-surface">Browse</h1>
	<p class="mt-1 text-on-surface-variant">
		{libraries.reduce((n, s) => n + s.works, 0).toLocaleString()} works across {libraries.length} libraries.
		Pick a shelf.
	</p>
	<div class="mt-8">
		<SiteCards sites={libraries} />
	</div>
</section>
