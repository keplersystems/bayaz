import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

const API_PROXY = {
	'/api': {
		target: 'http://127.0.0.1:8100',
		rewrite: (path: string) => path.replace(/^\/api/, '')
	}
};

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// The site is a static bundle: every route is a shell, and all data comes from
			// bayaz-api at runtime. `fallback` makes the server hand that shell to any path,
			// which is what lets /work/<site>/<slug> work without prerendering 258,232 pages.
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	// `/api` is proxied rather than called cross-origin so the browser never needs CORS, and
	// the site ships one origin in development exactly as it will in production.
	// `allowedHosts` is required for the tunnelled hostname: vite answers 403 to any Host it
	// was not told about.
	server: { allowedHosts: ['preview.aun.rest'], proxy: API_PROXY },
	preview: { allowedHosts: ['preview.aun.rest'], proxy: API_PROXY }
});
