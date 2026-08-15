<script lang="ts">
	import Gloss from './Gloss.svelte';
</script>

<footer class="mt-20 border-t border-outline-variant text-on-surface-variant">
	<div class="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm sm:flex-row sm:items-center">
		<p class="mr-auto">
			<Gloss
				term="the notebook a reader fills by hand with the verse they want to keep"
				script={{ text: 'بیاض', lang: 'ur' }}
			>
				<span class="font-serif text-base text-on-surface italic">bayaz</span>
			</Gloss>, a personal archive of the Rekhta Foundation's literary web.
		</p>
		<p class="text-on-surface-faint">
			All content belongs to rekhta, hindwi, sufinama and rekhtadictionary.
		</p>
	</div>
</footer>
