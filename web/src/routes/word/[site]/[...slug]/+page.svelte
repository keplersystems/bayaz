<script lang="ts">
	import type { PageData } from './$types';
	import ScriptText from '$lib/components/ScriptText.svelte';
	import StateMessage from '$lib/components/StateMessage.svelte';
	import Pause from 'lucide-svelte/icons/pause';
	import Play from 'lucide-svelte/icons/play';

	let { data }: { data: PageData } = $props();

	const entry = $derived(data.entry);

	const senseLangs = $derived.by(() => {
		const order = ['en', 'hi', 'ur'];
		const groups = new Map<string, typeof entry.senses>();
		for (const sense of entry.senses) {
			const list = groups.get(sense.lang) ?? [];
			list.push(sense);
			groups.set(sense.lang, list);
		}
		return [...groups.entries()].sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0]));
	});

	const langMeta: Record<string, { label: string; lang: string | null }> = {
		en: { label: 'English', lang: null },
		hi: { label: 'हिन्दी', lang: 'hi' },
		ur: { label: 'اردو', lang: 'ur' }
	};

	const relations = $derived.by(() => {
		const groups = new Map<string, typeof entry.relations>();
		for (const relation of entry.relations) {
			const list = groups.get(relation.rel_type) ?? [];
			list.push(relation);
			groups.set(relation.rel_type, list);
		}
		return [...groups.entries()];
	});

	const isEmpty = $derived(
		entry.senses.length === 0 &&
			entry.relations.length === 0 &&
			entry.shers.length === 0 &&
			entry.examples.length === 0 &&
			!entry.trivia
	);

	let audio: HTMLAudioElement | undefined = $state();
	let playing = $state(false);

	function toggleAudio() {
		if (!audio) return;
		if (playing) {
			audio.pause();
		} else {
			audio.play().catch(() => {});
		}
	}

	const shers = $derived(
		entry.shers.map((sher) => ({
			lines: sher.lines.split(/\r?\n/).filter(Boolean),
			poet: sher.poet
		}))
	);
</script>

<svelte:head
	><title>{entry.headword ?? entry.headword_urdu ?? 'Entry'} · dictionary · bayaz</title
	></svelte:head
>

<article class="mx-auto max-w-3xl px-4 py-10">
	<nav class="mb-8 text-sm text-on-surface-variant" aria-label="Breadcrumb">
		<a href="/dictionary" class="hover:text-primary">Dictionary</a>
		<span aria-hidden="true">/</span>
		<a href="/dictionary?site={entry.site}">{entry.site}</a>
	</nav>

	<header class="mb-10 border-b border-outline-variant/60 pb-8">
		<div class="flex flex-wrap items-baseline gap-x-8 gap-y-2">
			{#if entry.headword}
				<h1 class="font-serif text-4xl text-on-surface">{entry.headword}</h1>
			{/if}
			{#if entry.headword_urdu}
				<p lang="ur" class="text-verse-urdu text-on-surface">{entry.headword_urdu}</p>
			{/if}
			{#if entry.headword_hindi}
				<p lang="hi" class="text-2xl text-on-surface-variant">{entry.headword_hindi}</p>
			{/if}
		</div>
		<div class="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-on-surface-variant">
			{#if entry.vazn}
				<span class="rounded-m3-full border border-outline-variant px-2.5 py-0.5"
					>vazn {entry.vazn}</span
				>
			{/if}
			{#if entry.audio_url}
				<button
					type="button"
					onclick={toggleAudio}
					class="inline-flex items-center gap-1.5 text-primary hover:underline"
					aria-label={playing
						? `Pause pronunciation of ${entry.headword}`
						: `Play pronunciation of ${entry.headword}`}
				>
					{#if playing}<Pause class="size-4" aria-hidden="true" />{:else}<Play
							class="size-4"
							aria-hidden="true"
						/>{/if}
					{playing ? 'Pause' : 'Listen'}
				</button>
				<audio
					bind:this={audio}
					src={entry.audio_url}
					onplay={() => (playing = true)}
					onpause={() => (playing = false)}
					onended={() => (playing = false)}
					onerror={() => (playing = false)}
					preload="none"
				></audio>
			{/if}
			{#if entry.trivia}
				<span>{entry.trivia}</span>
			{/if}
		</div>
	</header>

	{#if isEmpty}
		<StateMessage
			kind="empty"
			title="This entry has no gloss"
			hint="The headword is archived, but the source gave no senses for it."
		/>
	{:else}
		{#if senseLangs.length > 0}
			<section aria-label="Senses" class="mb-10 space-y-8">
				{#each senseLangs as [lang, senses] (lang)}
					<div>
						<h2 lang={langMeta[lang]?.lang ?? null} class="mb-3 label">
							{langMeta[lang]?.label ?? lang}
						</h2>
						<ol class="space-y-3">
							{#each senses as sense, i (i)}
								<li class="flex gap-3 text-lg leading-relaxed">
									<span class="font-serif text-on-surface-faint tabular-nums">{i + 1}.</span>
									<div>
										{#if sense.pos}
											<span class="text-sm text-on-surface-variant italic">{sense.pos.trim()}</span>
										{/if}
										<p class="font-serif text-on-surface">
											<ScriptText text={sense.definition} />
										</p>
									</div>
								</li>
							{/each}
						</ol>
					</div>
				{/each}
			</section>
		{/if}

		{#if relations.length > 0}
			<section aria-label="Related words" class="mb-10">
				<h2 class="mb-3 label">Related words</h2>
				{#each relations as [type, list] (type)}
					<div class="mb-3 flex flex-wrap items-center gap-2">
						<span class="w-24 text-sm text-on-surface-faint capitalize">{type}</span>
						{#each list as relation, i (type + i)}
							<span
								class="rounded-m3-full border border-outline-variant bg-surface-container px-3
									py-0.5 text-base text-on-surface"
								title={relation.target_meaning ?? undefined}
							>
								<ScriptText text={relation.target_text} />
							</span>
						{/each}
					</div>
				{/each}
			</section>
		{/if}

		{#if entry.examples.length > 0}
			<section aria-label="Examples" class="mb-10">
				<h2 class="mb-3 label">In use</h2>
				<ul class="space-y-2">
					{#each entry.examples as example, i (i)}
						<li class="font-serif text-lg leading-relaxed text-on-surface">
							<ScriptText text={example} />
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		{#if shers.length > 0}
			<section aria-label="Example couplets" class="mb-4">
				<h2 class="mb-6 text-center label">In verse</h2>
				<div class="space-y-10">
					{#each shers as sher, i (i)}
						<blockquote class="text-center">
							{#each sher.lines as line, j (i + '-' + j)}
								<p class="text-2xl leading-loose text-on-surface"><ScriptText text={line} /></p>
							{/each}
							{#if sher.poet}
								<footer class="mt-2 text-sm text-on-surface-variant">
									<ScriptText text={sher.poet} />
								</footer>
							{/if}
						</blockquote>
					{/each}
				</div>
			</section>
		{/if}
	{/if}

	<p class="mt-12 text-center text-xs text-on-surface-faint">{entry.site}</p>
</article>
