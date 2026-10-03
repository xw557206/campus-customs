import type { Product } from './api'

/**
 * Filter and sort helpers for the catalogue.
 *
 * These exist because the database's own values are inconsistent, which was
 * found while analysing the schema:
 *
 *  - `garment_type` is free text: "short-sleeve t-shirt" and "short-sleeve
 *    T-shirt" are the same garment, and five different values describe hooded
 *    garments. A filter built on the raw column would under-report.
 *  - `colors` has unmerged synonyms: "navy" and "navy blue" are the same
 *    colour, and there are six spellings of grey.
 *
 * So the filter UI groups the raw values into a small set of families rather
 * than listing all 22 garment types and 22 colour terms.
 */

export interface CategoryGroup {
  label: string
  /** Lower-cased substrings; a product matches if its garment_type contains any. */
  match: string[]
}

export const CATEGORIES: CategoryGroup[] = [
  { label: 'Hoodies', match: ['hoodie', 'hood'] },
  { label: 'Crewnecks', match: ['crewneck', 'crew-neck', 'mockneck'] },
  { label: 'T-shirts', match: ['t-shirt', 'tee'] },
  { label: 'Quarter-zips', match: ['quarter-zip', '1/4 zip'] },
  { label: 'Jackets & fleece', match: ['jacket', 'fleece'] },
  { label: 'Long sleeve', match: ['long-sleeve'] },
]

export interface ColourGroup {
  label: string
  match: string[]
}

export const COLOURS: ColourGroup[] = [
  { label: 'Navy', match: ['navy'] },
  { label: 'Grey', match: ['gray', 'grey', 'charcoal'] },
  { label: 'White & cream', match: ['white', 'cream', 'ivory'] },
  { label: 'Black', match: ['black'] },
  { label: 'Red', match: ['red', 'maroon', 'coral'] },
  { label: 'Blue', match: ['blue'] },
]

export type SortKey = 'name' | 'price-asc' | 'price-desc' | 'stock'

export const SORTS: { key: SortKey; label: string }[] = [
  { key: 'name', label: 'Name (A–Z)' },
  { key: 'price-asc', label: 'Price: low to high' },
  { key: 'price-desc', label: 'Price: high to low' },
  { key: 'stock', label: 'Most in stock' },
]

export interface Filters {
  category: string | null
  colour: string | null
  inStockOnly: boolean
  sort: SortKey
}

export const NO_FILTERS: Filters = {
  category: null,
  colour: null,
  inStockOnly: false,
  sort: 'name',
}

function matchesCategory(product: Product, label: string): boolean {
  const group = CATEGORIES.find((c) => c.label === label)
  if (!group) return true
  const type = product.garment_type.toLowerCase()
  // Case-insensitive substring, so the "t-shirt"/"T-shirt" split cannot
  // silently drop products.
  return group.match.some((m) => type.includes(m))
}

function matchesColour(product: Product, label: string): boolean {
  const group = COLOURS.find((c) => c.label === label)
  if (!group) return true
  return product.colors.some((c) => {
    const lower = c.toLowerCase()
    return group.match.some((m) => lower.includes(m))
  })
}

export function applyFilters(products: Product[], filters: Filters): Product[] {
  let out = products

  if (filters.category) out = out.filter((p) => matchesCategory(p, filters.category!))
  if (filters.colour) out = out.filter((p) => matchesColour(p, filters.colour!))
  if (filters.inStockOnly) out = out.filter((p) => p.total_stock > 0)

  const sorted = [...out]
  switch (filters.sort) {
    case 'price-asc':
      sorted.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
      break
    case 'price-desc':
      sorted.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
      break
    case 'stock':
      sorted.sort((a, b) => b.total_stock - a.total_stock || a.name.localeCompare(b.name))
      break
    default:
      sorted.sort((a, b) => a.name.localeCompare(b.name))
  }
  return sorted
}

/** How many products each category would show, so empty filters can be hidden. */
export function categoryCounts(products: Product[]): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const group of CATEGORIES) {
    counts[group.label] = products.filter((p) => matchesCategory(p, group.label)).length
  }
  return counts
}
