import { api } from '$lib/api';
import type { PageLoad } from './$types';

const PER_PAGE = 24;

export const load: PageLoad = async ({ params, url, fetch }) => {
	const offset = Number(url.searchParams.get('offset') ?? 0);
	const [poet, works] = await Promise.all([
		api.poet(params.site, params.slug, fetch),
		api.poetWorks(params.site, params.slug, { limit: PER_PAGE, offset }, fetch)
	]);
	return { poet, works, offset, perPage: PER_PAGE };
};
