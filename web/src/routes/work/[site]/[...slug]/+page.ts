import { api } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const work = await api.work(params.site, params.slug, fetch);
	const words = work.has_words
		? await api.workWords(params.site, params.slug, fetch).catch(() => [])
		: [];
	return { work, words };
};
