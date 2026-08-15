<script lang="ts">
	import type { WorkSummary } from '$lib/api';
	import { altTitle, humanizeSlug, workTitle } from '$lib/scripts';
	import ScriptText from './ScriptText.svelte';

	let {
		works,
		showType = false,
		/** Off while browsing one site, where naming it on every row says nothing. */
		showSite = false
	}: { works: WorkSummary[]; showType?: boolean; showSite?: boolean } = $props();
</script>

<ul class="divide-y divide-outline-variant/70">
	{#each works as work (work.site + work.slug)}
		{@const alt = altTitle(work)}
		<li>
			<a href="/work/{work.site}/{encodeURIComponent(work.slug)}" class="group block py-4">
				<p
					class="font-serif text-lg leading-snug text-balance text-on-surface transition-colors group-hover:text-primary"
				>
					<ScriptText text={workTitle(work)} />
				</p>
				{#if alt}
					<!-- The same title in another script, on its own line: an Urdu title set beside a
					     Roman one puts two directions on one baseline and reads as a collision. -->
					<p class="mt-0.5 text-on-surface-faint">
						<ScriptText text={alt.text} />
					</p>
				{/if}
				<p class="mt-1.5 flex flex-wrap items-baseline gap-x-3 text-sm text-on-surface-variant">
					{#if work.author_name}
						<span><ScriptText text={work.author_name} /></span>
					{/if}
					{#if showType}
						<span class="text-on-surface-faint">{humanizeSlug(work.work_type)}</span>
					{/if}
					{#if showSite}
						<span class="text-on-surface-faint">{work.site}</span>
					{/if}
				</p>
			</a>
		</li>
	{/each}
</ul>
