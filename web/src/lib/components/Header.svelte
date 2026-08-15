<script lang="ts">
	import { navigating, page } from '$app/state';
	import Search from 'lucide-svelte/icons/search';
	import SearchBox from './SearchBox.svelte';
	import ThemeToggle from './ThemeToggle.svelte';

	const links = [
		{ href: '/browse', label: 'Browse' },
		{ href: '/poets', label: 'Poets' },
		{ href: '/dictionary', label: 'Dictionary' }
	];

	const active = (href: string) => page.url.pathname.startsWith(href);
</script>

<header class="sticky top-0 z-40 border-b border-outline-variant/60 bg-surface/85 backdrop-blur-md">
	<div class="mx-auto flex h-14 max-w-5xl items-center gap-5 px-4 sm:px-6">
		<a
			href="/"
			class="font-serif text-xl tracking-tight italic transition-colors hover:text-primary"
		>
			bayaz
		</a>

		<nav class="flex items-center gap-4 text-sm sm:gap-5" aria-label="Primary">
			{#each links as link (link.href)}
				<a
					href={link.href}
					aria-current={active(link.href) ? 'page' : undefined}
					class="text-on-surface-variant decoration-primary underline-offset-[0.4em]
						transition-colors hover:text-on-surface aria-current:text-on-surface aria-current:underline"
				>
					{link.label}
				</a>
			{/each}
		</nav>

		<div class="ml-auto flex items-center gap-1">
			<div class="hidden w-56 lg:block">
				<SearchBox />
			</div>
			<a
				href="/search"
				aria-label="Search"
				class="grid size-9 place-items-center rounded-full
					text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface lg:hidden"
			>
				<Search class="size-4.5" />
			</a>
			<ThemeToggle />
		</div>
	</div>

	{#if navigating}
		<div
			class="absolute inset-x-0 bottom-0 h-px animate-pulse bg-primary/70"
			aria-hidden="true"
		></div>
	{/if}
</header>
