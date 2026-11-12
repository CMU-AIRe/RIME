<script lang="ts">
  // :::jumpbox id="section-id" label="Optional text"::: renders a full-width
  // link box to #section-id. Without a label it shows the raw id.
  export let id: string;
  export let label: string | undefined = undefined;
</script>

<a
  href={'#' + id}
  class="block -mx-4 mb-4 px-4 py-2 bg-gray-100 hover:bg-slate-100 rounded transition"
>
  <span class="text-neutral-500">↪</span> <em>{label || id}</em>
</a>
