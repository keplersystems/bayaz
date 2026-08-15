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
	<div class="mx-auto flex h-14 max-w-5xl items-center gap-3 px-3 sm:gap-5 sm:px-6">
		<a
			href="/"
			class="shrink-0 font-serif text-xl tracking-tight italic transition-colors hover:text-primary"
		>
			bayaz
		</a>

		<!-- The three links, the search affordance and the theme toggle do not fit on one 320px
		     line, so the nav is the part allowed to shrink and scroll rather than push the rest
		     off the screen. -->
		<nav
			class="flex min-w-0 [scrollbar-width:none] items-center gap-3.5 overflow-x-auto
				text-sm sm:gap-5 [&::-webkit-scrollbar]:hidden"
			aria-label="Primary"
		>
			{#each links as link (link.href)}
				<!-- `py` is for the touch target, not for looks: the text alone is a 20px tall tap
				     area, under the 24px minimum. -->
				<a
					href={link.href}
					aria-current={active(link.href) ? 'page' : undefined}
					class="shrink-0 py-2.5 text-on-surface-variant decoration-primary underline-offset-[0.4em]
						transition-colors hover:text-on-surface aria-current:text-on-surface aria-current:underline"
				>
					{link.label}
				</a>
			{/each}
		</nav>

		<div class="ml-auto flex shrink-0 items-center gap-0.5 sm:gap-1">
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
