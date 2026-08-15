import { api } from '$lib/api';
import type { PageLoad } from './$types';

const PER_PAGE = 25;

export const load: PageLoad = async ({ url, fetch }) => {
	const q = url.searchParams.get('q')?.trim() ?? '';
	const kindParam = url.searchParams.get('kind');
	const kind = kindParam === 'works' || kindParam === 'entries' ? kindParam : undefined;
	const offset = Number(url.searchParams.get('offset') ?? 0);

	if (!q) return { q: '', kind: kind ?? null, results: null, offset: 0, perPage: PER_PAGE };

	const results = await api.search({ q, kind, limit: PER_PAGE, offset }, fetch);
	return { q, kind: kind ?? null, results, offset, perPage: PER_PAGE };
};
