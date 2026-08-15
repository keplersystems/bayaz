<script lang="ts">
	import type { PageData } from './$types';
	import Pagination from '$lib/components/Pagination.svelte';
	import ScriptText from '$lib/components/ScriptText.svelte';
	import StateMessage from '$lib/components/StateMessage.svelte';
	import WorkList from '$lib/components/WorkList.svelte';
	import { formatCount } from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const primary = $derived(
		data.poet.name ?? data.poet.name_hindi ?? data.poet.name_urdu ?? 'Unnamed'
	);
	const others = $derived(
		[data.poet.name_hindi, data.poet.name_urdu].filter((n): n is string => !!n && n !== primary)
	);
	const life = $derived(
		data.poet.born || data.poet.died ? `${data.poet.born ?? '?'}–${data.poet.died ?? ''}` : null
	);
</script>

<svelte:head><title>{primary} · bayaz</title></svelte:head>

<section class="mx-auto max-w-3xl px-4 py-10">
	<nav class="mb-8 text-sm text-on-surface-variant" aria-label="Breadcrumb">
		<a href="/poets" class="hover:text-primary">Poets</a>
		<span aria-hidden="true">/</span>
		<a
			href="/poets?site={data.poet.site}&type={data.poet.entity_type}"
			class="capitalize hover:text-primary"
		>
			{data.poet.site}
		</a>
	</nav>

	<header class="mb-8 border-b border-outline-variant/60 pb-8 text-center">
		<p class="mb-2 label">
			{data.poet.entity_type} · {data.poet.site}
		</p>
		<h1 class="font-serif text-4xl text-on-surface">
			<ScriptText text={primary} />
		</h1>
		{#if others.length > 0}
			<p class="mt-3 flex flex-wrap justify-center gap-x-6 gap-y-1 text-xl text-on-surface-variant">
				{#each others as name (name)}
					<ScriptText text={name} />
				{/each}
			</p>
		{/if}
		{#if life}
			<p class="mt-3 text-sm text-on-surface-variant tabular-nums">{life}</p>
		{/if}
		{#if data.poet.description}
			<p class="mx-auto mt-4 max-w-xl font-serif text-lg leading-relaxed text-on-surface-variant">
				<ScriptText text={data.poet.description} />
			</p>
		{/if}
	</header>

	<h2 class="mb-2 label">
		{formatCount(data.poet.works)} works
	</h2>

	{#if data.poet.works === 0}
		<StateMessage
			kind="empty"
			title="No works archived"
			hint="This name appears only as an attribution."
		/>
	{:else}
		<WorkList works={data.works.items} showType />
		<Pagination
			total={data.works.total}
			offset={data.offset}
			perPage={data.perPage}
			makeHref={(offset) => `?offset=${offset}`}
		/>
	{/if}
</section>
