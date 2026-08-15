<script lang="ts">
	import Moon from 'lucide-svelte/icons/moon';
	import Sun from 'lucide-svelte/icons/sun';

	let explicit = $state(readStoredTheme());

	function readStoredTheme(): 'light' | 'dark' | null {
		try {
			const t = localStorage.getItem('bayaz-theme');
			return t === 'light' || t === 'dark' ? t : null;
		} catch {
			return null;
		}
	}

	let systemDark = $state(matchMedia('(prefers-color-scheme: dark)').matches);
	const resolved = $derived(explicit ?? (systemDark ? 'dark' : 'light'));

	$effect(() => {
		const mq = matchMedia('(prefers-color-scheme: dark)');
		const onChange = (e: MediaQueryListEvent) => (systemDark = e.matches);
		mq.addEventListener('change', onChange);
		return () => mq.removeEventListener('change', onChange);
	});

	function toggle() {
		explicit = resolved === 'dark' ? 'light' : 'dark';
		document.documentElement.dataset.theme = explicit;
		try {
			localStorage.setItem('bayaz-theme', explicit);
		} catch {
			/* private mode: the toggle still works for this visit */
		}
	}
</script>

<button
	type="button"
	onclick={toggle}
	aria-label={resolved === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
	class="rounded-m3-full grid size-10 place-items-center text-on-surface-variant
		transition-colors hover:bg-surface-container-high"
>
	{#if resolved === 'dark'}<Sun class="size-5" />{:else}<Moon class="size-5" />{/if}
</button>
