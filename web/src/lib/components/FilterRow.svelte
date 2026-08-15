<script lang="ts">
	let {
		label,
		options,
		current,
		href,
		labels
	}: {
		label: string;
		/** `null` is the unfiltered option, rendered as "all". */
		options: (string | null)[];
		current: string | null;
		href: (value: string | null) => string;
		/** Display text per option, where the value is not what a reader should see. */
		labels?: Record<string, string>;
	} = $props();
</script>

<!-- Wraps rather than scrolls: four sites and six roles do not fit one phone line, and a
     filter a reader cannot see is a filter they will not use. -->
<div class="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
	<span class="w-10 shrink-0 text-on-surface-faint">{label}</span>
	{#each options as option (option ?? 'all')}
		<a
			href={href(option)}
			aria-current={current === option ? 'true' : undefined}
			class="py-1 text-on-surface-variant decoration-primary underline-offset-[0.4em]
				transition-colors hover:text-on-surface aria-current:text-on-surface aria-current:underline"
		>
			{option === null ? 'all' : (labels?.[option] ?? option)}
		</a>
	{/each}
</div>
