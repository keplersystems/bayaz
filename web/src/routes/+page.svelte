<script lang="ts">
	import type { PageData } from './$types';
	import ScriptText from '$lib/components/ScriptText.svelte';
	import SearchBox from '$lib/components/SearchBox.svelte';
	import SiteCards from '$lib/components/SiteCards.svelte';
	import BookMarked from 'lucide-svelte/icons/book-marked';
	import Library from 'lucide-svelte/icons/library';
	import Users from 'lucide-svelte/icons/users';

	let { data }: { data: PageData } = $props();

	const works = $derived(data.sites.reduce((n, s) => n + s.works, 0));
	const entries = $derived(data.sites.reduce((n, s) => n + s.entries, 0));

	const couplet = $derived.by(() => {
		const f = data.featured;
		if (!f) return null;
		const urdu = (f.body_urdu ?? '').split('\n').filter(Boolean).slice(0, 2);
		if (urdu.length === 2) return { script: 'urdu', lines: urdu };
		const roman = (f.body ?? '').split('\n').filter(Boolean).slice(0, 2);
		return roman.length > 0 ? { script: 'roman', lines: roman } : null;
	});

	const stats = $derived([
		{ label: 'works', value: works },
		{ label: 'poets', value: data.totalPoets },
		{ label: 'dictionary entries', value: entries },
		{ label: 'tags', value: data.totalTags }
	]);
</script>

<svelte:head>
	<title>bayaz · a reading archive of Urdu and Hindi literature</title>
	<meta
		name="description"
		content="A personal archive of the Rekhta Foundation's literary web: 258,232 works of Urdu and Hindi poetry and prose, 22,051 poets, and a 962,724-entry dictionary."
	/>
</svelte:head>

<section class="relative overflow-hidden">
	<div
		class="pointer-events-none absolute inset-0 -z-10 opacity-60"
		style="background: radial-gradient(60% 50% at 50% 0%, var(--color-primary-container), transparent 70%)"
		aria-hidden="true"
	></div>
	<div class="mx-auto max-w-3xl px-4 pt-16 pb-14 text-center sm:pt-24">
		<p class="text-xs font-medium tracking-[0.2em] text-on-surface-variant uppercase">
			A reading archive
		</p>
		<h1 class="mt-4 font-serif text-4xl leading-tight text-balance text-on-surface sm:text-6xl">
			Two centuries of Urdu &amp; Hindi verse, in one quiet place
		</h1>
		<p class="mx-auto mt-5 max-w-xl text-lg text-pretty text-on-surface-variant">
			bayaz gathers the Rekhta Foundation's literary web — rekhta, hindwi, sufinama and the
			rekhtadictionary — into a single library you can read in three scripts, with every word a tap
			away from its meaning.
		</p>
		<div class="mx-auto mt-8 max-w-xl">
			<SearchBox size="lg" placeholder="A poet, a ghazal, a word…" />
		</div>
		<dl
			class="mx-auto mt-10 flex max-w-2xl flex-wrap justify-center gap-x-8 gap-y-2 text-sm text-on-surface-variant"
		>
			{#each stats as stat (stat.label)}
				<div class="flex items-baseline gap-1.5">
					<dt>{stat.label}</dt>
					<dd class="font-serif text-lg text-on-surface tabular-nums">
						{stat.value.toLocaleString()}
					</dd>
				</div>
			{/each}
		</dl>
	</div>
</section>

{#if couplet && data.featured}
	<section class="mx-auto max-w-3xl px-4" aria-label="A ghazal to begin with">
		<a
			href="/work/{data.featured.site}/{encodeURIComponent(data.featured.slug)}"
			class="group block rounded-m3-xl border border-outline-variant
				bg-surface-container p-6 text-center transition-colors hover:border-primary/50 sm:p-8"
		>
			{#each couplet.lines as line (line)}
				<p class="text-nastaliq text-on-surface">
					{#if couplet.script === 'urdu'}
						<ScriptText text={line} />
					{:else}
						<span class="font-serif">{line}</span>
					{/if}
				</p>
			{/each}
			<p class="mt-4 text-sm text-on-surface-variant">
				{data.featured.title}
				{#if data.featured.author_name}· <ScriptText text={data.featured.author_name} />{/if}
				<span class="text-primary group-hover:underline">· read it</span>
			</p>
		</a>
	</section>
{/if}

<section class="mx-auto max-w-4xl px-4 py-16" aria-label="The collections">
	<h2 class="text-center font-serif text-2xl text-on-surface">The collections</h2>
	<p class="mt-1 mb-6 text-center text-sm text-on-surface-variant">Four sites, one shelf.</p>
	<SiteCards sites={data.sites} />
</section>

<section class="mx-auto max-w-4xl px-4 pb-16" aria-label="Ways in">
	<div class="grid gap-4 sm:grid-cols-3">
		<a
			href="/browse"
			class="flex items-center gap-3 rounded-m3-lg
				bg-primary-container p-5 text-on-primary-container transition-colors hover:bg-primary/12"
		>
			<Library class="size-6 shrink-0" aria-hidden="true" />
			<span
				><span class="block font-medium">Browse the collections</span>
				<span class="block text-sm text-on-surface-variant"
					>{works.toLocaleString()} works by form</span
				>
			</span>
		</a>
		<a
			href="/poets"
			class="flex items-center gap-3 rounded-m3-lg
				border border-outline-variant bg-surface-container p-5 transition-colors hover:border-primary/50"
		>
			<Users class="size-6 shrink-0" aria-hidden="true" />
			<span
				><span class="block font-medium text-on-surface">Poets &amp; people</span>
				<span class="block text-sm text-on-surface-variant"
					>{data.totalPoets.toLocaleString()} names, with dates</span
				>
			</span>
		</a>
		<a
			href="/dictionary"
			class="flex items-center gap-3 rounded-m3-lg
				border border-outline-variant bg-surface-container p-5 transition-colors hover:border-primary/50"
		>
			<BookMarked class="size-6 shrink-0" aria-hidden="true" />
			<span
				><span class="block font-medium text-on-surface">The dictionary</span>
				<span class="block text-sm text-on-surface-variant"
					>{entries.toLocaleString()} entries, three scripts</span
				>
			</span>
		</a>
	</div>
</section>
