<script lang="ts">
	import type { Script } from '$lib/scripts';

	let {
		value,
		options,
		onselect
	}: {
		value: Script;
		options: { value: Script; label: string; available: boolean }[];
		onselect: (script: Script) => void;
	} = $props();

	const shown = $derived(options.filter((option) => option.available));
</script>

<!-- Only the scripts a work actually has are offered. A control that renders three choices and
     disables two reads as breakage rather than as the archive's shape. -->
{#if shown.length > 1}
	<div class="flex items-center gap-3 text-sm" role="radiogroup" aria-label="Reading script">
		{#each shown as option (option.value)}
			<button
				type="button"
				role="radio"
				aria-checked={value === option.value}
				onclick={() => onselect(option.value)}
				class="cursor-pointer text-on-surface-faint decoration-primary
					underline-offset-[0.45em] transition-colors hover:text-on-surface aria-checked:text-on-surface
					aria-checked:underline"
				lang={option.value === 'urdu' ? 'ur' : option.value === 'hindi' ? 'hi' : undefined}
			>
				{option.label}
			</button>
		{/each}
	</div>
{/if}
