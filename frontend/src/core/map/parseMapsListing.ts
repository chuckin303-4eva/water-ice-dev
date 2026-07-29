/** Best-effort parser for text a user copy/pastes from a Google Maps or
 * Bing Maps listing (selecting visible text in their own browser --
 * no automation, no scraping, no ToS exposure). Google/Bing Maps copy
 * output isn't a stable, documented format, so this is heuristic and
 * expected to need manual correction, not a guaranteed extraction.
 */

const ZIP_RE = /\b\d{5}(-\d{4})?\b/
const STREET_NUMBER_RE = /^\d+\s+\S/

export interface ParsedListing {
  name: string | null
  address: string | null
}

export function parseMapsListing(raw: string): ParsedListing {
  const lines = raw
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)

  if (lines.length === 0) {
    return { name: null, address: null }
  }

  // The business name is reliably the first line in every Google/Bing
  // Maps listing copy format seen so far.
  const name = lines[0]

  // Prefer a line with a ZIP code (strongest signal it's the address);
  // fall back to a line that looks like it starts with a street number.
  const address =
    lines.find((line) => ZIP_RE.test(line)) ??
    lines.find((line) => STREET_NUMBER_RE.test(line)) ??
    null

  return { name, address }
}
