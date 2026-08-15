import { api, type SearchKind } from '$lib/api';
import type { PageLoad } from './$types';

const PER_PAGE = 25;
const KINDS: SearchKind[] = ['works', 'entries', 'poets'];

export const load: PageLoad = async ({ url, fetch }) => {
	const q = url.searchParams.get('q')?.trim() ?? '';
	const kindParam = url.searchParams.get('kind') as SearchKind | null;
	// There is no cross-kind search on the api, so the default is named rather than absent:
	// an "everything" tab that quietly returned works only would be a lie.
	const kind = kindParam && KINDS.includes(kindParam) ? kindParam : 'works';
	const site = url.searchParams.get('site');
	const offset = Number(url.searchParams.get('offset') ?? 0);

	const results = q
		? await api.search({ q, kind, site: site ?? undefined, limit: PER_PAGE, offset }, fetch)
		: null;

	return { q, kind, site, results, offset, perPage: PER_PAGE };
};
