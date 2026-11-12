import adapter from "@sveltejs/adapter-static";
import preprocess from "svelte-preprocess";

// GitHub Pages project sites live under /<repo>/ (here: /RIME, case-sensitive). Pass the
// prefix via BASE_PATH at build time; `vite dev` always serves from "/".
// BASE_PATH must start with "/" and have no trailing slash (or be empty).
const dev = process.argv.includes("dev");
const base = dev ? "" : (process.env.BASE_PATH ?? "");
if (base && (!base.startsWith("/") || base.endsWith("/"))) {
  throw new Error(`BASE_PATH must look like "/RIME" (got "${base}")`);
}

// Output directory: build/ by default (GitHub Actions deploy). The
// `build:docs` script sets OUT_DIR=docs for the publish-from-branch fallback.
const outDir = process.env.OUT_DIR ?? "build";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: [preprocess({ postcss: true })],
  kit: {
    adapter: adapter({
      pages: outDir,
      assets: outDir,
      fallback: "404.html",
      strict: true,
    }),
    paths: {
      base,
    },
    prerender: {
      handleHttpError: ({ path, message }) => {
        // Only the deliberate "__IMAGE_PLACEHOLDER__" src is tolerated; any other
        // missing file (images, iframes, links) fails the build.
        if (path.includes("IMAGE_PLACEHOLDER")) return;
        throw new Error(message);
      },
    },
  },
};

export default config;
