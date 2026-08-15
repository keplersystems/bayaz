<script lang="ts">
	import {
		ApiError,
		api,
		type EntryGloss,
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
	let entry = $state<EntryGloss | null>(null);
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

	const verseSize = $derived(
		{
			roman: 'font-serif text-verse-roman sm:text-verse-roman-lg',
			hindi: 'text-verse-hindi sm:text-verse-hindi-lg',
			urdu: 'text-verse-urdu sm:text-verse-urdu-lg'
		}[script]
	);

	const lang = $derived(script === 'urdu' ? 'ur' : script === 'hindi' ? 'hi' : undefined);
</script>

{#if bodyLines.length === 0}
	<p class="py-10 text-center text-sm text-on-surface-variant">
		This work is catalogued by title only.
	</p>
{:else if prose}
	<div class="mx-auto max-w-[38rem]" {lang}>
		{#each paragraphs as paragraph, i (i)}
			<p class="mb-6 text-on-surface last:mb-0 {verseSize}">
				<ScriptText text={paragraph} />
			</p>
		{/each}
	</div>
{:else}
	<!-- Couplets are the unit of a ghazal: each stands alone, so they are separated by more
	     space than the two lines within one. -->
	<div {lang} class="mx-auto w-fit max-w-full text-on-surface {verseSize}">
		{#each groups as group, gi (gi)}
			<div class="mb-9 last:mb-0 sm:mb-11">
				{#each group as line, li (gi + '-' + li)}
					<p class="text-balance">
						{#if typeof line === 'string'}
							<ScriptText text={line} />
						{:else}
							<!-- Words are stored as bare tokens with no whitespace, so the separator is
							     rendered here. Without it every line runs together as one word. -->
							{#each line as word, wi (word.line + '-' + word.ord)}
								<!-- The affordance appears on hover rather than sitting under every word: a
								     poem underlined throughout reads as a form, not as verse. -->
								{#if wi > 0}{' '}{/if}{#if word.code}<button
										type="button"
										class="cursor-pointer decoration-dotted underline-offset-[0.3em]
											transition-colors hover:text-primary hover:underline
											aria-expanded:text-primary aria-expanded:underline"
										aria-expanded={active?.code === word.code}
										onclick={(e) => lookup(word, e.currentTarget)}>{word.word}</button
									>{:else}{word.word}{/if}
							{/each}
						{/if}
					</p>
				{/each}
			</div>
		{/each}
	</div>
{/if}

<WordPopover {active} {status} {entry} onclose={() => (active = null)} />
