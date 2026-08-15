<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import Footer from '$lib/components/Footer.svelte';
	import Header from '$lib/components/Header.svelte';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<a
	href="#main"
	class="sr-only rounded-m3-sm bg-primary px-3 py-1.5 text-sm text-on-primary focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50"
>
	Skip to content
</a>

<div class="flex min-h-screen flex-col bg-surface font-sans text-on-surface">
	<Header />
	<main id="main" class="flex-1">
		{@render children()}
	</main>
	<Footer />
</div>
