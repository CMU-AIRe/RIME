<script lang="ts">
  import Seo from "$lib/components/Seo.svelte";
  import Markdown from "$lib/components/Markdown.svelte";
  import ScrollMeter from "$lib/components/ScrollMeter.svelte";
  import { meta } from "$lib/meta";
  // The whole post is this one Markdown file.
  import text from "../maintext/post.md?raw";
</script>

<Seo title={meta.title} description={meta.description || meta.subtitle || meta.title} />

<div>
  <ScrollMeter containerSelector=".md-output" />

  <div class="layout-xl text-base space-y-12">
    <Markdown source={text} />
  </div>
</div>
