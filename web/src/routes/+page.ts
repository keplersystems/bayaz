import { api } from '$lib/api';
import type { PageLoad } from './$types';

async function featuredGhazal(fetch: typeof globalThis.fetch) {
	const { total } = await api.works({ site: 'rekhta', work_type: 'ghazals', limit: 1 }, fetch);
	const offset = Math.floor(Math.random() * total);
	const { items } = await api.works(
		{ site: 'rekhta', work_type: 'ghazals', limit: 1, offset },
		fetch
	);
	const summary = items[0];
	if (!summary) return null;
	try {
		return await api.work(summary.site, summary.slug, fetch);
	} catch {
		return null;
	}
}

export const load: PageLoad = async ({ fetch }) => {
	const [sites, tags, poets, featured] = await Promise.all([
		api.sites(fetch),
		api.tags({ limit: 1 }, fetch),
		api.poets({ limit: 1 }, fetch),
		featuredGhazal(fetch)
	]);
	return {
		sites,
		totalTags: tags.total,
		totalPoets: poets.total,
		featured
	};
};
