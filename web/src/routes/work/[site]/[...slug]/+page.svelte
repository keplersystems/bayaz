<script lang="ts">
	import type { PageData } from './$types';
	import Chip from '$lib/components/Chip.svelte';
	import ScriptSwitcher from '$lib/components/ScriptSwitcher.svelte';
	import ScriptText from '$lib/components/ScriptText.svelte';
	import Verse from '$lib/components/Verse.svelte';
	import { detectScript, humanizeSlug, titleIn, workBodies, type Script } from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const bodies = $derived(workBodies(data.work));

	const available = $derived({
		roman: 'roman' in bodies,
		hindi: 'hindi' in bodies,
		urdu: 'urdu' in bodies
	});

	const preference: Script[] = ['urdu', 'roman', 'hindi'];
	const preferred = $derived(preference.find((s) => available[s]) ?? 'roman');

	let override = $state<Script | null>(null);
	const script = $derived(override && available[override] ? override : preferred);

	const options = $derived([
		{ value: 'roman' as Script, label: 'Roman', available: available.roman },
		{ value: 'hindi' as Script, label: 'देवनागरी', available: available.hindi },
		{ value: 'urdu' as Script, label: 'اردو', available: available.urdu }
	]);

	const displayTitle = $derived(
		titleIn(data.work, script) ??
			data.work.title ??
			data.work.title_hindi ??
			data.work.title_urdu ??
			'Untitled'
	);
	const titleScript = $derived(detectScript(displayTitle));
	const translit = $derived(
		titleScript !== 'roman' && data.work.title_translit && data.work.title_translit !== displayTitle
			? data.work.title_translit
			: null
	);

	const titleClass = $derived(
		titleScript === 'urdu'
			? 'text-nastaliq-lg'
			: titleScript === 'hindi'
				? 'text-3xl leading-snug sm:text-4xl'
				: 'font-serif text-3xl sm:text-4xl'
	);
	const titleLang = $derived(
		titleScript === 'urdu' ? 'ur' : titleScript === 'hindi' ? 'hi' : undefined
	);

	const showWordHint = $derived(data.words.length > 0);
</script>

<svelte:head>
	<title>{displayTitle} · bayaz</title>
</svelte:head>

<article class="mx-auto max-w-3xl px-4 py-10">
	<nav
		class="mb-8 flex flex-wrap items-center gap-2 text-sm text-on-surface-variant"
		aria-label="Breadcrumb"
	>
		<a href="/browse/{data.work.site}" class="capitalize hover:text-primary">{data.work.site}</a>
		<span aria-hidden="true">/</span>
		<a href="/browse/{data.work.site}/{data.work.work_type}" class="hover:text-primary">
			{humanizeSlug(data.work.work_type)}
		</a>
	</nav>

	<header class="mb-8 text-center">
		<h1 lang={titleLang} class="text-on-surface {titleClass}">
			<ScriptText text={displayTitle} />
		</h1>
		{#if translit}
			<p class="mt-2 font-serif text-lg text-on-surface-variant">{translit}</p>
		{/if}
		{#if data.work.author_name}
			<p class="mt-3 text-lg text-on-surface-variant">
				{#if data.work.author_slug}
					<a
						href="/poet/{data.work.site}/{encodeURIComponent(data.work.author_slug)}"
						class="underline-offset-4 hover:text-primary hover:underline"
					>
						<ScriptText text={data.work.author_name} />
					</a>
				{:else}
					<ScriptText text={data.work.author_name} />
				{/if}
			</p>
		{/if}
	</header>

	<div class="mb-8 flex justify-center">
		<ScriptSwitcher {options} value={script} onselect={(s) => (override = s)} />
	</div>

	{#if showWordHint}
		<p class="mb-8 text-center text-xs tracking-wide text-on-surface-variant/70 uppercase">
			Tap a word for its meaning
		</p>
	{/if}

	<Verse work={data.work} words={data.words} {script} />

	{#if data.work.translation || data.work.explanation}
		<section class="mt-14 grid gap-4 sm:grid-cols-2" aria-label="Translation and explanation">
			{#if data.work.translation}
				<div class="rounded-m3-lg bg-surface-container p-5">
					<h2 class="mb-2 text-xs font-medium tracking-[0.15em] text-on-surface-variant uppercase">
						Translation
					</h2>
					<p class="font-serif text-lg leading-relaxed text-on-surface-variant">
						{data.work.translation}
					</p>
				</div>
			{/if}
			{#if data.work.explanation}
				<div class="rounded-m3-lg bg-surface-container p-5">
					<h2 class="mb-2 text-xs font-medium tracking-[0.15em] text-on-surface-variant uppercase">
						Explanation
					</h2>
					<p class="font-serif text-lg leading-relaxed text-on-surface-variant">
						<ScriptText text={data.work.explanation} />
					</p>
				</div>
			{/if}
		</section>
	{/if}

	{#if data.work.tags.length > 0}
		<section class="mt-10" aria-label="Tags">
			<ul class="flex flex-wrap justify-center gap-2">
				{#each data.work.tags as tag (tag)}
					<li><Chip text={tag} href="/tag/{encodeURIComponent(tag)}" /></li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if data.work.source}
		<p class="mt-12 text-center text-xs text-on-surface-variant/60">
			Source · {data.work.source} · {data.work.site}
		</p>
	{/if}
</article>
