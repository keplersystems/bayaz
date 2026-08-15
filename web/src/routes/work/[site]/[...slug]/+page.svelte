<script lang="ts">
	import type { PageData } from './$types';
	import ScriptSwitcher from '$lib/components/ScriptSwitcher.svelte';
	import ScriptText from '$lib/components/ScriptText.svelte';
	import Verse from '$lib/components/Verse.svelte';
	import {
		detectScript,
		humanizeSlug,
		nameIn,
		titleIn,
		workBodies,
		workTitle,
		type Script
	} from '$lib/scripts';

	let { data }: { data: PageData } = $props();

	const bodies = $derived(workBodies(data.work));
	const available = $derived({
		roman: 'roman' in bodies,
		hindi: 'hindi' in bodies,
		urdu: 'urdu' in bodies
	});

	// Urdu first where it exists: it is the script most of this corpus was written in.
	const preferred = $derived(
		(['urdu', 'roman', 'hindi'] as Script[]).find((s) => available[s]) ?? 'roman'
	);

	let override = $state<Script | null>(null);
	const script = $derived(override && available[override] ? override : preferred);

	const options = $derived([
		{ value: 'roman' as Script, label: 'Roman', available: available.roman },
		{ value: 'hindi' as Script, label: 'देवनागरी', available: available.hindi },
		{ value: 'urdu' as Script, label: 'اردو', available: available.urdu }
	]);

	const title = $derived(titleIn(data.work, script) ?? workTitle(data.work));
	const titleScript = $derived(detectScript(title));
	const titleLang = $derived(
		titleScript === 'urdu' ? 'ur' : titleScript === 'hindi' ? 'hi' : undefined
	);
	const titleSize = $derived(
		{
			urdu: 'text-2xl sm:text-3xl',
			hindi: 'text-2xl sm:text-3xl',
			roman: 'font-serif text-2xl sm:text-3xl'
		}[titleScript]
	);

	const translit = $derived(
		titleScript !== 'roman' && data.work.title_translit !== title ? data.work.title_translit : null
	);

	// The work stores its poet's name in one script; the entity has all three, so the name
	// follows the script being read wherever the poet page was captured.
	const poetName = $derived(nameIn(data.poet, script) ?? data.work.author_name);

	const poetHref = $derived(
		data.work.author_slug
			? `/poet/${data.work.site}/${encodeURIComponent(data.work.author_slug)}`
			: null
	);
</script>

<svelte:head><title>{title} · bayaz</title></svelte:head>

<article class="mx-auto max-w-3xl px-4 pt-8 pb-24 sm:px-6">
	<p class="mb-10 text-sm text-on-surface-faint">
		<a href="/browse/{data.work.site}/{data.work.work_type}" class="hover:text-on-surface-variant">
			{humanizeSlug(data.work.work_type)}
		</a>
	</p>

	<!-- An Urdu title sets right; leaving the transliteration and the poet on the left would
	     split the header down the middle, so the whole block follows the title's script. -->
	<header class="mb-10 {titleScript === 'urdu' ? 'text-right' : ''}">
		<h1 lang={titleLang} class="text-balance text-on-surface {titleSize}">
			<ScriptText text={title} />
		</h1>
		{#if translit}
			<p class="mt-1.5 font-serif text-base text-on-surface-faint italic">{translit}</p>
		{/if}
		{#if poetName}
			<p class="mt-4 text-base text-on-surface-variant">
				{#if poetHref}
					<a
						href={poetHref}
						class="underline decoration-outline underline-offset-[0.35em] transition-colors hover:text-primary"
					>
						<ScriptText text={poetName} />
					</a>
				{:else}
					<ScriptText text={poetName} />
				{/if}
			</p>
		{/if}
	</header>

	{#if options.filter((o) => o.available).length > 1 || data.words.length > 0}
		<!-- Wraps rather than hiding the hint on narrow screens: tapping is the gesture a phone
		     reader has, so that is where the affordance is most worth stating. -->
		<div
			class="mb-12 flex flex-wrap items-center justify-between gap-x-6 gap-y-1.5
				border-y border-outline-variant/70 py-2.5"
		>
			<ScriptSwitcher {options} value={script} onselect={(s) => (override = s)} />
			{#if data.words.length > 0}
				<p class="text-xs text-on-surface-faint">Tap any word for its meaning</p>
			{/if}
		</div>
	{/if}

	<Verse work={data.work} words={data.words} {script} />

	{#if data.work.translation || data.work.explanation}
		<!-- The source's own gloss, kept visibly apart from the verse it describes. -->
		<section class="mt-16 space-y-6 border-t border-outline-variant/70 pt-8">
			{#if data.work.translation}
				<div>
					<h2 class="mb-1.5 label">Translation</h2>
					<p class="font-serif text-lg leading-relaxed text-on-surface-variant">
						{data.work.translation}
					</p>
				</div>
			{/if}
			{#if data.work.explanation}
				<div>
					<h2 class="mb-1.5 label">Explanation</h2>
					<p class="font-serif text-lg leading-relaxed text-on-surface-variant">
						<ScriptText text={data.work.explanation} />
					</p>
				</div>
			{/if}
		</section>
	{/if}

	{#if data.work.tags.length > 0}
		<ul class="mt-12 flex flex-wrap gap-x-4 gap-y-2 text-sm" aria-label="Tags">
			{#each data.work.tags as tag (tag)}
				<li>
					<a
						href="/tag/{encodeURIComponent(tag)}"
						class="text-on-surface-faint transition-colors hover:text-primary"
					>
						<ScriptText text={tag} />
					</a>
				</li>
			{/each}
		</ul>
	{/if}

	{#if data.more.length > 0 && poetHref}
		<!-- Somewhere to go next, so a poem is a stop on a path rather than a dead end. -->
		<section class="mt-16 border-t border-outline-variant/70 pt-8">
			<h2 class="mb-4 text-sm text-on-surface-variant">
				More by <ScriptText text={poetName ?? 'this poet'} />
			</h2>
			<ul class="space-y-2.5">
				{#each data.more as work (work.slug)}
					<li>
						<a
							href="/work/{work.site}/{work.slug}"
							class="text-balance text-on-surface transition-colors hover:text-primary"
						>
							<ScriptText text={workTitle(work)} />
						</a>
					</li>
				{/each}
			</ul>
			<a href={poetHref} class="mt-5 inline-block text-sm text-primary hover:underline">
				All work by this poet
			</a>
		</section>
	{/if}
</article>
