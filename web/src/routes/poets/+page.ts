import { api } from '$lib/api';
import type { PageLoad } from './$types';

const PER_PAGE = 24;

export const load: PageLoad = async ({ url, fetch }) => {
	const offset = Number(url.searchParams.get('offset') ?? 0);
	const site = url.searchParams.get('site');
	const entityType = url.searchParams.get('type');
	// The api rejects a one-character query, so a half-typed name is treated as no filter.
	const q = url.searchParams.get('q')?.trim() ?? '';

	const poets = await api.poets(
		{
			site: site || undefined,
			entity_type: entityType || undefined,
			q: q.length >= 2 ? q : undefined,
			limit: PER_PAGE,
			offset
		},
		fetch
	);

	return {
		poets,
		offset,
		perPage: PER_PAGE,
		site: site || null,
		entityType: entityType || null,
		q
	};
};
