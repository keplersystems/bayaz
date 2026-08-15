<script lang="ts">
	import { detectScript, scriptDir, scriptLang } from '$lib/scripts';

	let { text, class: klass = '' }: { text: string; class?: string } = $props();

	const script = $derived(detectScript(text));
	const lang = $derived(scriptLang(script));
	const dir = $derived(scriptDir(script));
</script>

<span {lang} {dir} class={klass}>{text}</span>
