<script lang="ts">
	import ScriptText from './ScriptText.svelte';

	let {
		href,
		text,
		plain = false
	}: {
		href?: string;
		text: string;
		plain?: boolean;
	} = $props();

	const classes =
		'inline-flex items-center rounded-m3-full border-outline-variant bg-surface-container text-on-surface-variant px-3 py-0.5 text-sm';
</script>

{#if href}
	<a {href} class="hover:border-primary hover:text-primary {classes} transition-colors">
		{#if plain}{text}{:else}<ScriptText {text} />{/if}
	</a>
{:else}
	<span class={classes}
		>{#if plain}{text}{:else}<ScriptText {text} />{/if}</span
	>
{/if}
