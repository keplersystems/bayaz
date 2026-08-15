import { api } from '$lib/api';
import type { PageLoad } from './$types';

const PER_PAGE = 30;

export const load: PageLoad = async ({ url, fetch }) => {
	const offset = Number(url.searchParams.get('offset') ?? 0);
	const site = url.searchParams.get('site');
	const [sites, entries] = await Promise.all([
		api.sites(fetch),
		api.entries({ site: site || undefined, limit: PER_PAGE, offset }, fetch)
	]);
	return {
		sites: sites.filter((s) => s.entries > 0),
		entries,
		offset,
		perPage: PER_PAGE,
		site: site || null
	};
};
