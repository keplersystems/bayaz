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

	const active = (href: string) =>
		page.url.pathname === href || page.url.pathname.startsWith(href + '/');
</script>

<header class="sticky top-0 z-40 border-b border-outline-variant bg-surface/90 backdrop-blur">
	<div class="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4">
		<a
			href="/"
			class="mr-2 font-serif text-2xl text-on-surface italic transition-colors hover:text-primary"
		>
			bayaz
		</a>
		<nav class="hidden gap-1 sm:flex" aria-label="Primary">
			{#each links as link (link.href)}
				<a
					href={link.href}
					aria-current={active(link.href) ? 'page' : undefined}
					class="rounded-m3-full px-3 py-1.5
						text-sm font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high
						aria-current:bg-secondary-container aria-current:text-on-secondary-container"
				>
					{link.label}
				</a>
			{/each}
		</nav>
		<div class="ml-auto flex items-center gap-1">
			<div class="hidden w-64 md:block">
				<SearchBox />
			</div>
			<a
				href="/search"
				aria-label="Search"
				class="rounded-m3-full grid size-10 place-items-center
					text-on-surface-variant transition-colors hover:bg-surface-container-high md:hidden"
			>
				<Search class="size-5" />
			</a>
			<ThemeToggle />
		</div>
	</div>
	<nav
		class="flex gap-1 overflow-x-auto border-t border-outline-variant px-4 py-2 sm:hidden"
		aria-label="Primary"
	>
		{#each links as link (link.href)}
			<a
				href={link.href}
				aria-current={active(link.href) ? 'page' : undefined}
				class="rounded-m3-full shrink-0
					px-3 py-1 text-sm font-medium text-on-surface-variant aria-current:bg-secondary-container aria-current:text-on-secondary-container"
			>
				{link.label}
			</a>
		{/each}
	</nav>
	{#if navigating}
		<div
			class="absolute inset-x-0 bottom-0 h-0.5 origin-left animate-pulse bg-primary"
			aria-hidden="true"
		></div>
	{/if}
</header>
