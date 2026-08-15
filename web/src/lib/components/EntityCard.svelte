<script lang="ts">
	import type { EntitySummary } from '$lib/api';
	import { detectScript } from '$lib/scripts';
	import ScriptText from './ScriptText.svelte';

	let {
		entities,
		/** Off while filtered to one site, where repeating it on every row says nothing. */
		showSite = false
	}: { entities: EntitySummary[]; showSite?: boolean } = $props();
</script>

<ul class="grid grid-cols-1 gap-x-10 sm:grid-cols-2">
	{#each entities as entity (entity.site + entity.slug)}
		{@const primary = entity.name ?? entity.name_hindi ?? entity.name_urdu ?? 'Unnamed'}
		{@const others = [entity.name_hindi, entity.name_urdu].filter(
			(n): n is string => !!n && n !== primary && detectScript(n) !== detectScript(primary)
		)}
		<li class="border-b border-outline-variant/70">
			<a href="/poet/{entity.site}/{encodeURIComponent(entity.slug)}" class="group block py-3.5">
				<p
					class="font-serif text-lg leading-snug text-on-surface transition-colors group-hover:text-primary"
				>
					<ScriptText text={primary} />
				</p>
				{#if others.length > 0}
					<!-- Each script on its own line: Devanagari and Nastaliq side by side on one
					     baseline read as a collision rather than as two renderings of one name. -->
					<p class="mt-0.5 flex flex-col gap-0.5 text-sm text-on-surface-faint">
						{#each others as name (name)}
							<span><ScriptText text={name} /></span>
						{/each}
					</p>
				{/if}
				{#if entity.born || entity.died || showSite}
					<p class="mt-1 text-sm text-on-surface-variant tabular-nums">
						{#if entity.born || entity.died}
							{entity.born ?? '?'}–{entity.died ?? ''}
						{/if}
						{#if showSite}
							<span class="text-on-surface-faint">{entity.site}</span>
						{/if}
					</p>
				{/if}
			</a>
		</li>
	{/each}
</ul>
