// A static bundle with a client-side data layer: there is no node server to render on, and
// the corpus is far too large to prerender. Every page fetches from bayaz-api in the browser.
export const ssr = false;
export const prerender = false;
export const trailingSlash = 'never';
