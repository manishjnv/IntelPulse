/**
 * HTML and URL sanitizers for rendering backend-sourced content safely.
 *
 * The briefings print/export path builds an HTML string from backend data
 * and hands it to `document.write()` / Blob download. Any unescaped `<`
 * from the model or from cached article content becomes script execution
 * in the print window. Use `escapeHtml` for every text interpolation and
 * `safeUrl` for every `href` that is not a literal constant.
 */

const HTML_ENTITY: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
  "/": "&#x2F;",
  "`": "&#96;",
};

/** Escape a string for safe interpolation into HTML text content or attribute values. */
export function escapeHtml(value: unknown): string {
  if (value === null || value === undefined) return "";
  const str = typeof value === "string" ? value : String(value);
  return str.replace(/[&<>"'`/]/g, (ch) => HTML_ENTITY[ch] ?? ch);
}

/**
 * Return a safe URL for use in `href`/`src`.
 *
 * Only allows http:, https:, and mailto: schemes. Anything else (including
 * javascript:, data:, vbscript:, file:, or unparseable values) collapses to
 * "#". Whitespace is trimmed and control chars are stripped before parsing
 * because browsers tolerate them in schemes (e.g. "java\tscript:alert(1)").
 */
const ALLOWED_URL_SCHEMES = new Set(["http:", "https:", "mailto:"]);

export function safeUrl(value: unknown): string {
  if (value === null || value === undefined) return "#";
  const raw = typeof value === "string" ? value : String(value);
  const cleaned = raw.trim().replace(/[\u0000-\u001F\u007F]/g, "");
  if (!cleaned) return "#";
  // Relative URLs (no scheme, starting with / or #) are safe — keep them.
  if (/^[/#?]/.test(cleaned)) return cleaned;
  try {
    const parsed = new URL(cleaned, "https://placeholder.invalid/");
    if (parsed.origin === "https://placeholder.invalid") {
      // It parsed only because of the base; no scheme — treat as relative.
      return cleaned;
    }
    if (!ALLOWED_URL_SCHEMES.has(parsed.protocol)) return "#";
    return parsed.toString();
  } catch {
    return "#";
  }
}
