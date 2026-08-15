<script lang="ts">
	import type { WorkSummary } from '$lib/api';
	import { altTitle, workTitle } from '$lib/scripts';
	import ScriptText from './ScriptText.svelte';

	let { works, showType = false }: { works: WorkSummary[]; showType?: boolean } = $props();
</script>

<ul class="divide-y divide-outline-variant">
	{#each works as work (work.site + work.slug)}
		{@const alt = altTitle(work)}
		<li class="group py-4">
			<div class="flex items-baseline justify-between gap-3">
				<a
					href="/work/{work.site}/{encodeURIComponent(work.slug)}"
					class="min-w-0 font-serif text-lg leading-snug text-on-surface
						transition-colors group-hover:text-primary"
				>
					<ScriptText text={workTitle(work)} />
				</a>
				{#if showType}
					<span class="shrink-0 text-xs tracking-wide text-on-surface-variant uppercase">
						{work.work_type}
					</span>
				{/if}
			</div>
			<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-on-surface-variant">
				{#if work.author_name}
					{#if work.author_slug}
						<a
							href="/poet/{work.site}/{encodeURIComponent(work.author_slug)}"
							class="transition-colors hover:text-primary"
						>
							<ScriptText text={work.author_name} />
						</a>
					{:else}
						<ScriptText text={work.author_name} />
					{/if}
				{/if}
				{#if alt}
					<span class="text-on-surface-variant/70">
						<ScriptText text={alt.text} />
					</span>
				{/if}
				<span class="ml-auto hidden text-xs tracking-wide text-outline uppercase sm:inline">
					{work.site}
				</span>
			</div>
		</li>
	{/each}
</ul>
