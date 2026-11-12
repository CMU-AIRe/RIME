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
  /* Top-right institution wordmark (meta.logo). */
  .page-upper-right-inline {
    position: absolute;
    top: 22px;
    right: 28px;
    display: flex;
    justify-content: flex-end;
    pointer-events: none;
  }

  .page-upper-right {
    width: clamp(140px, 11vw, 180px);
    height: auto;
    pointer-events: none;
  }

  /* Narrow screens: keep it in the flow above the title so it never covers text. */
  @media (max-width: 1024px) {
    .page-upper-right-inline {
      position: static;
      padding: 14px 18px 0;
    }

    .page-upper-right {
      width: 112px;
    }
  }
</style>
