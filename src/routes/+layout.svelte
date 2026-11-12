<script lang="ts">
  import "../app.css";

  import { browser } from "$app/environment";
  import { base } from "$app/paths";
  import { fly } from "svelte/transition";

  import Header from "$lib/components/Header.svelte";
  import Footer from "$lib/components/Footer.svelte";
  import { meta } from "$lib/meta";
  import type { LayoutData } from "./$types";

  export let data: LayoutData;

  const isMobile = browser && /Android|iPhone/i.test(navigator.userAgent);
  const reducedMotion =
    browser && matchMedia("(prefers-reduced-motion: reduce)").matches;
</script>

{#if meta.logo?.src}
  <div class="page-upper-right-inline">
    <img
      src={`${base}/${meta.logo.src.replace(/^\/+/, "")}`}
      alt={meta.logo.alt ?? ""}
      class="page-upper-right"
      decoding="async"
    />
  </div>
{/if}

<Header />

{#if isMobile || reducedMotion}
  <!--
    Disable page transitions on mobile due to a browser engine bug.
    Also disable them for reduced-motion users.
  -->
  <main>
    <slot />
  </main>
{:else}
  {#key data.pathname}
    <main
      in:fly={{ x: -10, duration: 350, delay: 350 }}
      out:fly={{ y: 5, duration: 350 }}
    >
      <slot />
    </main>
  {/key}
{/if}

<Footer />

<style lang="postcss">
  .page-upper-right-inline {
    position: absolute;
    top: 3px;
    right: 16px;
    display: flex;
    justify-content: flex-end;
    pointer-events: none;
  }

  .page-upper-right {
    width: clamp(220px, 18vw, 320px);
    height: auto;
    pointer-events: none;
  }

  @media (max-width: 720px) {
    .page-upper-right-inline {
      top: 4px;
      right: 4px;
    }

    .page-upper-right {
      width: clamp(140px, 30vw, 220px);
    }
  }
</style>
