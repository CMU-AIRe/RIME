<script lang="ts">
  export let title: string = "Details";
  export let open: boolean = false;
  export let html: string; // already-marked HTML
</script>

<details class="foldbox foldbox--boxed my-4" open={open} data-foldbox="1">
  <summary class="foldbox__summary">
    <span class="foldbox__caret" aria-hidden="true"></span>
    <span class="foldbox__title">{title}</span>
  </summary>
  <div class="foldbox__body">
    <div class="md-output">{@html html}</div>
  </div>
</details>

<style lang="postcss">
  /* Global so auto-generated folds can reuse the exact same look */
  :global(.foldbox) {
    @apply my-2;
  }

  :global(.foldbox--boxed) {
    @apply rounded border border-neutral-200 bg-neutral-50;
  }

  :global(.foldbox__summary) {
    @apply cursor-pointer select-none font-semibold text-neutral-900;
    @apply flex items-center gap-3 text-sm;
  }

  :global(.foldbox--boxed > .foldbox__summary) {
    @apply px-4 py-3;
  }

  :global(.foldbox--boxed > .foldbox__summary:hover) {
    @apply bg-neutral-100;
  }

  :global(details.foldbox > summary::-webkit-details-marker) {
    display: none;
  }

  :global(.foldbox__caret) {
    width: 0;
    height: 0;
    border-top: 6px solid transparent;
    border-bottom: 6px solid transparent;
    border-left: 7px solid currentColor;
    transform: rotate(0deg);
    transform-origin: 2px 6px;
    transition: transform 120ms ease;
    opacity: 0.9;
    flex: 0 0 auto;
  }

  :global(details.foldbox[open] .foldbox__caret) {
    transform: rotate(90deg);
  }

  :global(details.foldbox.foldbox--boxed > summary .foldbox__caret) {
    transform: rotate(0deg);
  }

  :global(details.foldbox.foldbox--boxed[open] > summary .foldbox__caret) {
    transform: rotate(90deg);
  }

  :global(.foldbox--boxed > .foldbox__body) {
    @apply px-4 pb-3 pt-2;
  }
</style>
