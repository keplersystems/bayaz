import { api } from '$lib/api';
import type { PageLoad } from './$types';

const PER_PAGE = 24;

export const load: PageLoad = async ({ params, url, fetch }) => {
	const offset = Number(url.searchParams.get('offset') ?? 0);
	const works = await api.works(
		{ site: params.site, work_type: params.type, limit: PER_PAGE, offset },
		fetch
	);
	return { works, offset, perPage: PER_PAGE, site: params.site, workType: params.type };
};
