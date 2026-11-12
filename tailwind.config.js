const defaultTheme = require("tailwindcss/defaultTheme");

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{html,js,svelte,ts}"],
  darkMode: "false",
  plugins: [],
  theme: {
    extend: {
      fontSize: {
        sm: ["1rem", { lineHeight: "1.4rem" }],
        xl: ["1.3rem", { lineHeight: "2rem" }],
      },
      colors: {
        mint: "#f2fcf8",
        darkmint: "#ebfff5",
      },
    },
  },
};
