<script lang="ts">
	import type { PageData } from './$types';
	import { formatCount, humanizeSlug } from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const ordered = $derived([...data.workTypes].sort((a, b) => b.works - a.works));
	const head = $derived(ordered.slice(0, 4));
	const rest = $derived(ordered.slice(4));
</script>

<svelte:head><title>{data.site.site} · bayaz</title></svelte:head>

<section class="mx-auto max-w-4xl px-4 py-10">
	<nav class="mb-4 text-sm text-on-surface-variant" aria-label="Breadcrumb">
		<a href="/browse" class="hover:text-primary">Browse</a>
		<span aria-hidden="true">/</span>
		<span class="text-on-surface">{data.site.site}</span>
	</nav>

	<header class="flex flex-wrap items-end justify-between gap-4">
		<div>
			<h1 class="font-serif text-4xl text-on-surface capitalize">{data.site.site}</h1>
			<p class="mt-1 text-on-surface-variant">
				{formatCount(data.site.works)} works · {formatCount(data.site.entities)} poets
				{#if data.site.entries > 0}· {formatCount(data.site.entries)} entries{/if}
			</p>
		</div>
	</header>

	<div class="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
		{#each head as type (type.work_type)}
			<a
				href="/browse/{data.site.site}/{type.work_type}"
				class="flex flex-col justify-between
					gap-6 rounded-m3-lg bg-primary-container p-5 text-on-primary-container transition-colors hover:bg-primary/12"
			>
				<h2 class="font-serif text-2xl">{humanizeSlug(type.work_type)}</h2>
				<span class="text-sm text-on-surface-variant tabular-nums">
					{formatCount(type.works)} works
				</span>
			</a>
		{/each}
	</div>

	{#if rest.length > 0}
		<h2 class="mt-10 mb-3 label">Everything else</h2>
		<ul class="grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
			{#each rest as type (type.work_type)}
				<li>
					<a
						href="/browse/{data.site.site}/{type.work_type}"
						class="group flex items-baseline justify-between gap-3 rounded-m3-sm
							px-3 py-2 transition-colors hover:bg-surface-container"
					>
						<span class="text-on-surface transition-colors group-hover:text-primary">
							{humanizeSlug(type.work_type)}
						</span>
						<span class="text-sm text-on-surface-faint tabular-nums">
							{formatCount(type.works)}
						</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</section>
