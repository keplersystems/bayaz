/**
 * Typed client for bayaz-api.
 *
 * Every type in `types` is generated from the live `/openapi.json` by `bun run api:types`,
 * so nothing here restates the contract. If a field looks wrong, regenerate rather than
 * hand-edit.
 */

import type { components } from './schema';

type Schemas = components['schemas'];

export type Page<T> = { items: T[]; total: number; limit: number; offset: number };

export type SiteSummary = Schemas['SiteSummary'];
export type WorkTypeSummary = Schemas['WorkTypeSummary'];
export type WorkSummary = Schemas['WorkSummary'];
export type WorkDetail = Schemas['WorkDetail'];
export type WorkWords = Schemas['WorkWords'];
export type Word = Schemas['Word'];
export type EntitySummary = Schemas['EntitySummary'];
export type EntityDetail = Schemas['EntityDetail'];
export type EntrySummary = Schemas['EntrySummary'];
export type EntryDetail = Schemas['EntryDetail'];
export type Sense = Schemas['Sense'];
export type Relation = Schemas['Relation'];
export type Sher = Schemas['Sher'];
export type TagSummary = Schemas['TagSummary'];
export type SearchHit = Schemas['SearchHit'];

/** Thrown for any non-2xx response. `status === 404` is a normal outcome on several routes. */
export class ApiError extends Error {
	constructor(
		readonly status: number,
		message: string
	) {
		super(message);
	}
}

const BASE = import.meta.env.VITE_API_URL ?? '/api';

type Params = Record<string, string | number | boolean | null | undefined>;

async function get<T>(
	path: string,
	params: Params = {},
	fetcher: typeof fetch = fetch
): Promise<T> {
	const query = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== null && value !== undefined && value !== '') query.set(key, String(value));
	}
	const url = `${BASE}${path}${query.size ? `?${query}` : ''}`;
	const response = await fetcher(url);
	if (!response.ok) {
		throw new ApiError(response.status, `${response.status} ${response.statusText}: ${url}`);
	}
	return response.json();
}

/** Path segments may contain slashes and word codes contain backslashes, so encode each part. */
const path = (...segments: (string | number)[]) =>
	segments.map((segment) => encodeURIComponent(segment)).join('/');

export type Paging = { limit?: number; offset?: number };
export type Fetcher = typeof fetch;

export const api = {
	sites: (f?: Fetcher) => get<SiteSummary[]>('/sites', {}, f),

	workTypes: (site: string, f?: Fetcher) =>
		get<WorkTypeSummary[]>(`/sites/${path(site)}/work-types`, {}, f),

	works: (
		params: Paging & { site?: string; work_type?: string; author?: string } = {},
		f?: Fetcher
	) => get<Page<WorkSummary>>('/works', params, f),

	work: (site: string, slug: string, f?: Fetcher) =>
		get<WorkDetail>(`/works/${path(site)}/${path(slug)}`, {}, f),

	workWords: (site: string, slug: string, f?: Fetcher) =>
		get<WorkWords[]>(`/works/${path(site)}/${path(slug)}/words`, {}, f),

	poets: (params: Paging & { site?: string; entity_type?: string } = {}, f?: Fetcher) =>
		get<Page<EntitySummary>>('/poets', params, f),

	poet: (site: string, slug: string, f?: Fetcher) =>
		get<EntityDetail>(`/poets/${path(site)}/${path(slug)}`, {}, f),

	poetWorks: (site: string, slug: string, params: Paging = {}, f?: Fetcher) =>
		get<Page<WorkSummary>>(`/poets/${path(site)}/${path(slug)}/works`, params, f),

	entries: (params: Paging & { site?: string } = {}, f?: Fetcher) =>
		get<Page<EntrySummary>>('/entries', params, f),

	entry: (site: string, slug: string, f?: Fetcher) =>
		get<EntryDetail>(`/entries/${path(site)}/${path(slug)}`, {}, f),

	/** Resolves a word code to its entry. Throws ApiError(404) for codes that do not resolve,
	 *  which is normal: only rekhta's poetry codes are in the dictionary. */
	lookup: (code: string, f?: Fetcher) => get<EntrySummary>('/entries/lookup', { code }, f),

	tags: (params: Paging & { site?: string } = {}, f?: Fetcher) =>
		get<Page<TagSummary>>('/tags', params, f),

	tagWorks: (tag: string, params: Paging = {}, f?: Fetcher) =>
		get<Page<WorkSummary>>(`/tags/${path(tag)}/works`, params, f),

	search: (
		params: Paging & { q: string; kind?: 'works' | 'entries'; site?: string },
		f?: Fetcher
	) => get<Page<SearchHit>>('/search', params, f)
};
