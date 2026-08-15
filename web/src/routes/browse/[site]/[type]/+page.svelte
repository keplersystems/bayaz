<script lang="ts">
	import type { PageData } from './$types';
	import Pagination from '$lib/components/Pagination.svelte';
	import StateMessage from '$lib/components/StateMessage.svelte';
	import WorkList from '$lib/components/WorkList.svelte';
	import BookOpen from 'lucide-svelte/icons/book-open';
	import { formatCount, humanizeSlug } from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const label = $derived(humanizeSlug(data.workType));
</script>

<svelte:head><title>{label} · {data.site} · bayaz</title></svelte:head>

<section class="mx-auto max-w-3xl px-4 py-10">
	<nav class="mb-4 text-sm text-on-surface-variant" aria-label="Breadcrumb">
		<a href="/browse" class="hover:text-primary">Browse</a>
		<span aria-hidden="true">/</span>
		<a href="/browse/{data.site}" class="capitalize hover:text-primary">{data.site}</a>
		<span aria-hidden="true">/</span>
		<span class="text-on-surface">{label}</span>
	</nav>

	<header class="mb-6">
		<h1 class="flex items-center gap-3 font-serif text-3xl text-on-surface">
			{label}
		</h1>
		<p class="mt-1 flex items-center gap-1.5 text-sm text-on-surface-variant">
			<BookOpen class="size-4" aria-hidden="true" />
			{formatCount(data.works.total)} works on {data.site}
		</p>
	</header>

	{#if data.works.items.length === 0}
		<StateMessage
			kind="empty"
			title="Nothing here"
			hint="This shelf exists but holds no works, or the page has run past its end."
		/>
	{:else}
		<WorkList works={data.works.items} />
		<Pagination
			total={data.works.total}
			offset={data.offset}
			perPage={data.perPage}
			makeHref={(offset) => `?offset=${offset}`}
		/>
	{/if}
</section>
