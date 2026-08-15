<script lang="ts">
	import type { PageData } from './$types';
	import ScriptText from '$lib/components/ScriptText.svelte';
	import SearchBox from '$lib/components/SearchBox.svelte';
	import SiteCards from '$lib/components/SiteCards.svelte';
	import { formatCount, workTitle } from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const works = $derived(data.sites.reduce((n, s) => n + s.works, 0));
	const entries = $derived(data.sites.reduce((n, s) => n + s.entries, 0));

	const couplet = $derived.by(() => {
		const f = data.featured;
		if (!f) return null;
		const urdu = (f.body_urdu ?? '').split('\n').filter(Boolean).slice(0, 2);
		if (urdu.length === 2) return { script: 'urdu' as const, lines: urdu };
		const roman = (f.body ?? '').split('\n').filter(Boolean).slice(0, 2);
		return roman.length ? { script: 'roman' as const, lines: roman } : null;
	});

	const ways = $derived([
		{ href: '/browse', title: 'Browse by form', note: `${formatCount(works)} works` },
		{ href: '/poets', title: 'Poets and people', note: `${formatCount(data.totalPoets)} names` },
		{ href: '/dictionary', title: 'The dictionary', note: `${formatCount(entries)} entries` }
	]);
</script>

<svelte:head>
	<title>bayaz · a reading archive of Urdu and Hindi literature</title>
	<meta
		name="description"
		content="258,232 works of Urdu and Hindi literature from rekhta, hindwi, sufinama and the rekhtadictionary, readable in Urdu, Hindi and Roman, with a 962,724-entry dictionary behind every word of the poetry."
	/>
</svelte:head>

<!-- The word is the identity, so it is the image: Nastaliq set large is the one piece of
     visual art this archive already owns. `pb` carries the descenders, which fall far below
     the baseline at this size and would otherwise be clipped. -->
<section class="mx-auto max-w-2xl px-4 pt-16 pb-16 text-center sm:px-6 sm:pt-24">
	<h1>
		<span
			lang="ur"
			class="block pb-4 text-[5rem] leading-[1.1] text-on-surface sm:text-[7rem] sm:leading-[1.05]"
		>
			بیاض
		</span>
		<span class="mt-2 block font-serif text-2xl text-on-surface italic sm:text-3xl">bayaz</span>
	</h1>
	<p class="mx-auto mt-6 max-w-md text-lg leading-relaxed text-pretty text-on-surface-variant">
		The notebook a reader fills by hand with the verse they mean to keep.
	</p>
	<p class="mt-3 text-sm text-on-surface-faint">
		{formatCount(works)} of them, in Urdu, Hindi and Roman
	</p>
	<div class="mx-auto mt-10 max-w-md">
		<SearchBox size="lg" placeholder="A poet, a ghazal, a word" />
	</div>
</section>

{#if couplet && data.featured}
	<!-- A real couplet before any navigation: the archive should introduce itself in its own
	     voice rather than as a set of counts. -->
	<section class="border-y border-outline-variant/70" aria-label="A couplet from the archive">
		<a
			href="/work/{data.featured.site}/{encodeURIComponent(data.featured.slug)}"
			class="group mx-auto block max-w-3xl px-4 py-14 sm:px-6 sm:py-20"
		>
			<div
				lang={couplet.script === 'urdu' ? 'ur' : undefined}
				class="text-on-surface {couplet.script === 'urdu'
					? 'text-verse-urdu sm:text-verse-urdu-lg'
					: 'font-serif text-verse-roman sm:text-verse-roman-lg'}"
			>
				{#each couplet.lines as line (line)}
					<p class="text-balance"><ScriptText text={line} /></p>
				{/each}
			</div>
			<p class="mt-6 text-sm text-on-surface-faint">
				{#if data.featured.author_name}<ScriptText text={data.featured.author_name} />,{/if}
				<span class="transition-colors group-hover:text-primary">
					{workTitle(data.featured)}
				</span>
			</p>
		</a>
	</section>
{/if}

<section class="mx-auto max-w-3xl px-4 py-16 sm:px-6" aria-label="Ways in">
	<ul class="divide-y divide-outline-variant/70">
		{#each ways as way (way.href)}
			<li>
				<a href={way.href} class="group flex items-baseline justify-between gap-4 py-4">
					<span
						class="font-serif text-xl text-on-surface transition-colors group-hover:text-primary"
						>{way.title}</span
					>
					<span class="text-sm text-on-surface-faint tabular-nums">{way.note}</span>
				</a>
			</li>
		{/each}
	</ul>
</section>

<section class="mx-auto max-w-3xl px-4 pb-24 sm:px-6" aria-label="The collections">
	<h2 class="mb-5 text-sm text-on-surface-variant">The collections</h2>
	<SiteCards sites={data.sites} />
</section>
