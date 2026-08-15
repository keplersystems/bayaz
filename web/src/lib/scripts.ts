export type Script = 'roman' | 'hindi' | 'urdu';

const URDU_RE = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFC]/;
const HINDI_RE = /[\u0900-\u097F]/;

export function detectScript(text: string): Script {
	if (URDU_RE.test(text)) return 'urdu';
	if (HINDI_RE.test(text)) return 'hindi';
	return 'roman';
}

/** BCP-47 tag for a passage in a given script; roman stays under the page's `en`. */
export function scriptLang(script: Script): string | null {
	if (script === 'urdu') return 'ur';
	if (script === 'hindi') return 'hi';
	return null;
}

export function scriptDir(script: Script): 'rtl' | null {
	return script === 'urdu' ? 'rtl' : null;
}

type Titled = {
	title?: string | null;
	title_hindi?: string | null;
	title_urdu?: string | null;
};

/** Roman reads best next to an English interface, so prefer it and fall back through the scripts. */
export function preferredScript(work: Titled): Script {
	if (work.title) return 'roman';
	if (work.title_hindi) return 'hindi';
	if (work.title_urdu) return 'urdu';
	return 'roman';
}

export function titleIn(work: Titled, script: Script): string | null {
	if (script === 'roman') return work.title ?? null;
	if (script === 'hindi') return work.title_hindi ?? null;
	return work.title_urdu ?? null;
}

export function workTitle(work: Titled): string {
	return titleIn(work, preferredScript(work)) ?? 'Untitled';
}

/** The same title in a script other than the preferred one, for a quiet second line. */
export function altTitle(work: Titled): { script: Script; text: string } | null {
	const preferred = preferredScript(work);
	for (const script of ['urdu', 'hindi', 'roman'] as Script[]) {
		if (script === preferred) continue;
		const text = titleIn(work, script);
		if (text) return { script, text };
	}
	return null;
}

type Named = {
	name?: string | null;
	name_hindi?: string | null;
	name_urdu?: string | null;
};

/** A poet's name in the script being read. Only 62% of entities carry all three, so the
 *  caller's fallback (usually the work's own `author_name`) still has to be there. */
export function nameIn(entity: Named | null | undefined, script: Script): string | null {
	if (!entity) return null;
	if (script === 'urdu') return entity.name_urdu ?? null;
	if (script === 'hindi') return entity.name_hindi ?? null;
	return entity.name ?? null;
}

type Bodied = {
	body?: string | null;
	body_hindi?: string | null;
	body_urdu?: string | null;
};

/** `body` is usually Roman, but some sources keep Urdu or Hindi prose there with the other
 *  fields empty, so its script is detected rather than assumed. */
export function workBodies(work: Bodied): Partial<Record<Script, string>> {
	const map: Partial<Record<Script, string>> = {};
	if (work.body_urdu) map.urdu = work.body_urdu;
	if (work.body_hindi) map.hindi = work.body_hindi;
	if (work.body?.trim()) {
		map[detectScript(work.body.slice(0, 500))] ??= work.body;
	}
	return map;
}

const CONNECTIVES = new Set(['o', 'e', 'a', 'aur', 'and']);

export function humanizeSlug(slug: string): string {
	return slug
		.split('-')
		.map((word, i) => {
			if (word === 's' && i > 0) return '’s';
			if (i > 0 && CONNECTIVES.has(word)) return word;
			return word.charAt(0).toUpperCase() + word.slice(1);
		})
		.join(' ');
}

/** Work types whose bodies are paragraphs rather than verse lines. */
const PROSE_TYPES = new Set([
	'stories',
	'story',
	'articles',
	'essay',
	'essays',
	'children-s-stories',
	'latiife',
	'hikayaat',
	'sufi-proverbs',
	'sufi-terminology',
	'profile',
	'trivia'
]);

export function isProseType(workType: string): boolean {
	return PROSE_TYPES.has(workType);
}

/** Verse is read in couplets: pair lines, letting a lone trailing line stand alone. */
export function couplets<T>(lines: T[]): T[][] {
	const out: T[][] = [];
	for (let i = 0; i < lines.length; i += 2) out.push(lines.slice(i, i + 2));
	return out;
}

export function formatCount(n: number): string {
	return n.toLocaleString('en');
}
