<script lang="ts">
  import { meta } from "$lib/meta";
</script>

{#if meta.github_url}
  <footer class="layout-md text-sm mt-20 flex justify-center text-neutral-500">
    <a class="link" href={meta.github_url} target="_blank" rel="noopener noreferrer">Source on GitHub</a>
  </footer>
{/if}
