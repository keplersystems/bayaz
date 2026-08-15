<script lang="ts">
	import {
		ApiError,
		api,
		type EntrySummary,
		type Word,
		type WorkDetail,
		type WorkWords
	} from '$lib/api';
	import { couplets, detectScript, isProseType, workBodies, type Script } from '$lib/scripts';
	import ScriptText from './ScriptText.svelte';
	import WordPopover from './WordPopover.svelte';

	let {
		work,
		words,
		script
	}: {
		work: WorkDetail;
		words: WorkWords[];
		script: Script;
	} = $props();

	const prose = $derived(isProseType(work.work_type));

	// Word variants arrive under the source's own ids, so the script is sniffed from the text.
	const variant = $derived(
		prose
			? undefined
			: words.find((v) => {
					const sample = v.lines.flat().find((w) => w.word.trim())?.word ?? '';
					return sample && detectScript(sample) === script;
				})
	);

	const bodyText = $derived(workBodies(work)[script] ?? '');

	const bodyLines = $derived(bodyText.split('\n').filter((line) => line.trim() !== ''));
	const lines = $derived<(Word[] | string)[]>(variant ? variant.lines : bodyLines);
	const groups = $derived(couplets(lines));

	const paragraphs = $derived(
		bodyText
			.split(/\n\s*\n/)
			.map((p) => p.replace(/\n/g, ' ').trim())
			.filter(Boolean)
	);

	let active = $state<{ word: string; code: string; rect: DOMRect } | null>(null);
	let status = $state<'loading' | 'found' | 'none' | 'error'>('loading');
	let entry = $state<EntrySummary | null>(null);
	let requestId = 0;

	$effect(() => {
		script;
		active = null;
	});

	async function lookup(word: Word, el: HTMLElement) {
		if (!word.code) return;
		if (active?.code === word.code) {
			active = null;
			return;
		}
		active = { word: word.word, code: word.code, rect: el.getBoundingClientRect() };
		status = 'loading';
		entry = null;
		const id = ++requestId;
		try {
			const found = await api.lookup(word.code);
			if (id !== requestId) return;
			entry = found;
			status = 'found';
		} catch (e) {
			if (id !== requestId) return;
			// A 404 is the normal outcome for codes that were never in the dictionary.
			status = e instanceof ApiError && e.status === 404 ? 'none' : 'error';
		}
	}

	const typography = $derived(
		{
			roman: 'font-serif text-xl leading-relaxed sm:text-2xl sm:leading-loose',
			hindi: 'text-xl leading-loose sm:text-2xl',
			urdu: 'text-nastaliq sm:text-nastaliq-lg'
		}[script]
	);

	const containerLang = $derived(script === 'urdu' ? 'ur' : script === 'hindi' ? 'hi' : undefined);
</script>

{#if bodyLines.length > 0}
	{#if prose}
		<div class="mx-auto max-w-2xl">
			{#each paragraphs as paragraph, i (i)}
				<p class="mb-6 text-on-surface last:mb-0 {typography}">
					<ScriptText text={paragraph} />
				</p>
			{/each}
		</div>
	{:else}
		<div
			lang={containerLang}
			class="mx-auto max-w-xl space-y-8 text-center text-on-surface {typography}
				{script === 'urdu' ? 'sm:space-y-10' : ''}"
		>
			{#each groups as group, gi (gi)}
				<div class="space-y-1">
					{#each group as line, li (gi + '-' + li)}
						<p>
							{#if typeof line === 'string'}
								<ScriptText text={line} />
							{:else}
								{#each line as word (word.line + '-' + word.ord)}
									{#if word.code}
										<button
											type="button"
											class="-mx-0.5 rounded-m3-sm px-0.5 transition-colors
												hover:bg-surface-container-high {active?.code === word.code ? 'bg-secondary-container' : ''}"
											aria-expanded={active?.code === word.code}
											onclick={(e) => lookup(word, e.currentTarget)}>{word.word}</button
										>
									{:else}
										<span>{word.word}</span>
									{/if}
								{/each}
							{/if}
						</p>
					{/each}
				</div>
			{/each}
		</div>
	{/if}
{:else}
	<p class="mx-auto max-w-xl py-8 text-center text-on-surface-variant">
		This work is catalogued by title only.
	</p>
{/if}

<WordPopover {active} {status} {entry} onclose={() => (active = null)} />
