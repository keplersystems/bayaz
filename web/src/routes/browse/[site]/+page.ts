import { api } from '$lib/api';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const sites = await api.sites(fetch);
	const site = sites.find((s) => s.site === params.site);
	if (!site) error(404, `No site called ${params.site}`);
	const workTypes = await api.workTypes(params.site, fetch);
	return { site, workTypes };
};
