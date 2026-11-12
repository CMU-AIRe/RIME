// Single source of truth for the title block, <title>/description, and logo.
// Edit src/maintext/meta.json, not this file.
import raw from "../maintext/meta.json";

export type Author = {
  name: string; // a trailing "*" renders as a superscript (equal contribution)
  /** One affiliation or several; each should also appear in `affiliations`. */
  affiliation?: string | string[];
  url?: string;
};

export type Meta = {
  title: string;
  subtitle?: string;
  /** <meta name="description"> / og:description; falls back to subtitle, then title. */
  description?: string;
  authors: Author[];
  affiliations?: string[];
  /** Small lines under the affiliations, e.g. "* Equal contribution". */
  notes?: string[];
  date?: string;
  github_url?: string;
  /** Optional top-right logo; `src` is relative to static/, e.g. "assets/logo.png". */
  logo?: { src: string; alt: string } | null;
};

export const meta: Meta = raw as Meta;
