import { api } from '$lib/api';
import type { PageLoad } from './$types';

const PER_PAGE = 24;

export const load: PageLoad = async ({ params, url, fetch }) => {
	const offset = Number(url.searchParams.get('offset') ?? 0);
	const works = await api.tagWorks(params.tag, { limit: PER_PAGE, offset }, fetch);
	return { tag: params.tag, works, offset, perPage: PER_PAGE };
};
