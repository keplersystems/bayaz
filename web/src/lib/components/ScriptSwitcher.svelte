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
</script>

<div
	class="rounded-m3-full inline-flex items-center gap-1 bg-surface-container p-1"
	role="radiogroup"
	aria-label="Reading script"
>
	{#each options as option (option.value)}
		<button
			type="button"
			role="radio"
			aria-checked={value === option.value}
			disabled={!option.available}
			onclick={() => option.available && onselect(option.value)}
			class="rounded-m3-full px-4 py-1.5 text-sm font-medium transition-colors
				{value === option.value
				? 'bg-primary text-on-primary'
				: option.available
					? 'text-on-surface-variant hover:bg-surface-container-high'
					: 'cursor-not-allowed text-outline'}"
		>
			{option.label}
		</button>
	{/each}
</div>
