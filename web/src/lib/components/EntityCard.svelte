<script lang="ts">
	import type { EntitySummary } from '$lib/api';
	import { detectScript } from '$lib/scripts';
	import ScriptText from './ScriptText.svelte';

	let { entities }: { entities: EntitySummary[] } = $props();
</script>

<ul class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
	{#each entities as entity (entity.site + entity.slug)}
		{@const primary = entity.name ?? entity.name_hindi ?? entity.name_urdu ?? 'Unnamed'}
		{@const others = [entity.name_hindi, entity.name_urdu].filter(
			(n): n is string => !!n && n !== primary && detectScript(n) !== detectScript(primary)
		)}
		<li>
			<a
				href="/poet/{entity.site}/{encodeURIComponent(entity.slug)}"
				class="flex h-full flex-col gap-1
					rounded-m3-lg border border-outline-variant bg-surface-container p-4 transition-colors hover:border-primary/50"
			>
				<span class="text-xs tracking-wide text-on-surface-variant uppercase">
					{entity.entity_type} · {entity.site}
				</span>
				<span class="font-serif text-lg leading-snug text-on-surface">
					<ScriptText text={primary} />
				</span>
				{#if others.length > 0}
					<span class="flex flex-wrap gap-x-3 text-sm text-on-surface-variant">
						{#each others as name (name)}
							<ScriptText text={name} />
						{/each}
					</span>
				{/if}
				{#if entity.born || entity.died}
					<span class="mt-auto pt-1 text-sm text-on-surface-variant/80 tabular-nums">
						{entity.born ?? '?'}–{entity.died ?? ''}
					</span>
				{/if}
			</a>
		</li>
	{/each}
</ul>
