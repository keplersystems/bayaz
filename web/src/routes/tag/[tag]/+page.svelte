<script lang="ts">
	import type { PageData } from './$types';
	import Pagination from '$lib/components/Pagination.svelte';
	import ScriptText from '$lib/components/ScriptText.svelte';
	import StateMessage from '$lib/components/StateMessage.svelte';
	import WorkList from '$lib/components/WorkList.svelte';
	import Tag from 'lucide-svelte/icons/tag';
	import { formatCount } from '$lib/scripts';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head><title>{data.tag} · tag · bayaz</title></svelte:head>

<section class="mx-auto max-w-3xl px-4 py-10">
	<nav class="mb-8 text-sm text-on-surface-variant" aria-label="Breadcrumb">
		<a href="/" class="hover:text-primary">bayaz</a>
		<span aria-hidden="true">/</span>
		<span>tags</span>
	</nav>

	<header class="mb-8 text-center">
		<p class="mb-2 flex items-center justify-center gap-1.5 label">
			<Tag class="size-3.5" aria-hidden="true" />Tag
		</p>
		<h1 class="font-serif text-3xl text-on-surface">
			<ScriptText text={data.tag} />
		</h1>
		<p class="mt-1 text-sm text-on-surface-variant">
			{formatCount(data.works.total)} works carry this tag
		</p>
	</header>

	{#if data.works.items.length === 0}
		<StateMessage kind="empty" title="No works under this tag" />
	{:else}
		<WorkList works={data.works.items} showType showSite />
		<Pagination
			total={data.works.total}
			offset={data.offset}
			perPage={data.perPage}
			makeHref={(offset) => `?offset=${offset}`}
		/>
	{/if}
</section>
