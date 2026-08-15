import { api } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	return { entry: await api.entry(params.site, params.slug, fetch) };
};
