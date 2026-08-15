import { api, type EntityDetail, type WorkSummary } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const work = await api.work(params.site, params.slug, fetch);

	// The words, the poet and their other work are all optional: a reader should get the poem
	// even if any of them fails, so none is allowed to reject the page. The poet is fetched
	// because `work.author_name` exists in one script only, while the entity carries all three.
	const [words, poet, more] = await Promise.all([
		work.has_words
			? api.workWords(params.site, params.slug, fetch).catch(() => [])
			: Promise.resolve([]),
		work.author_slug
			? api.poet(work.site, work.author_slug, fetch).catch((): EntityDetail | null => null)
			: Promise.resolve<EntityDetail | null>(null),
		work.author_slug
			? api
					.poetWorks(work.site, work.author_slug, { limit: 7 }, fetch)
					.then((page) => page.items.filter((w) => w.slug !== work.slug).slice(0, 6))
					.catch((): WorkSummary[] => [])
			: Promise.resolve<WorkSummary[]>([])
	]);

	return { work, words, poet, more };
};
