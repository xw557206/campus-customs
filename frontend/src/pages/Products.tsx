import { useEffect, useState } from 'react'
import { fetchProducts, type Product } from '../api'
import { useChatResults } from '../chatResults'
import {
  applyFilters,
  categoryCounts,
  CATEGORIES,
  COLOURS,
  NO_FILTERS,
  SORTS,
  type Filters,
  type SortKey,
} from '../filters'
import { ProductCard } from '../components/ProductCard'

export function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [count, setCount] = useState(0)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const chat = useChatResults()
  const [filters, setFilters] = useState<Filters>(NO_FILTERS)

  useEffect(() => {
    let cancelled = false
    // Debounced so typing doesn't fire a request per keystroke.
    const timer = setTimeout(() => {
      setLoading(true)
      fetchProducts(query)
        .then((data) => {
          if (cancelled) return
          setProducts(data.products)
          setCount(data.count)
          setError(null)
        })
        .catch((e: unknown) => {
          if (cancelled) return
          setError(e instanceof Error ? e.message : String(e))
          setProducts([])
          setCount(0)
        })
        .finally(() => !cancelled && setLoading(false))
    }, 250)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query])

  const visible = applyFilters(products, filters)
  const counts = categoryCounts(products)
  const filtersActive =
    filters.category !== null || filters.colour !== null || filters.inStockOnly

  return (
    <>
      <section className="page-head">
        <p className="eyebrow">The catalogue</p>
        <h1>Everything we carry</h1>
        <p className="page-lede">
          Officially licensed Yale apparel, XS through XXL. Stock is read live, so the
          sizes shown are the sizes we have.
        </p>
      </section>

      {/* Results the assistant found. Same ProductCard as the catalogue
          below, so a chat result behaves identically to a browsed one. */}
      {chat.searched && (
        <section className="section results">
          <div className="results-head">
            <div>
              <h2>
                {chat.products.length > 0
                  ? `${chat.products.length} ${chat.products.length === 1 ? 'match' : 'matches'} from your question`
                  : 'No matching products'}
              </h2>
              {chat.query && <p className="muted">You asked: “{chat.query}”</p>}
            </div>
            <button className="link-btn" onClick={chat.clear}>
              Clear results
            </button>
          </div>

          {chat.products.length > 0 ? (
            <div className="grid">
              {chat.products.map((p) => (
                <ProductCard key={p.product_id} product={p} />
              ))}
            </div>
          ) : (
            <div className="notice">
              The assistant didn't find anything in the catalogue for that.
              The full range is below — or ask again with a colour, a garment
              type, or a team.
            </div>
          )}
        </section>
      )}

      <section className="section">
        <div className="toolbar">
          <input
            className="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, colour, garment or occasion…"
            aria-label="Search products"
          />
          {query && (
            <button className="link-btn" onClick={() => setQuery('')}>
              Clear
            </button>
          )}
          <span className="count">
            {loading ? 'Loading…' : `${count} ${count === 1 ? 'product' : 'products'}`}
          </span>
        </div>

        <div className="filters">
          <div className="filter-row">
            <span className="filter-label">Category</span>
            <div className="chips-row">
              {CATEGORIES.filter((c) => counts[c.label] > 0).map((c) => (
                <button
                  key={c.label}
                  className={filters.category === c.label ? 'fchip on' : 'fchip'}
                  onClick={() =>
                    setFilters((f) => ({
                      ...f,
                      category: f.category === c.label ? null : c.label,
                    }))
                  }
                >
                  {c.label} <span className="fchip-n">{counts[c.label]}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="filter-row">
            <span className="filter-label">Colour</span>
            <div className="chips-row">
              {COLOURS.map((c) => (
                <button
                  key={c.label}
                  className={filters.colour === c.label ? 'fchip on' : 'fchip'}
                  onClick={() =>
                    setFilters((f) => ({
                      ...f,
                      colour: f.colour === c.label ? null : c.label,
                    }))
                  }
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          <div className="filter-row">
            <label className="switch">
              <input
                type="checkbox"
                checked={filters.inStockOnly}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, inStockOnly: e.target.checked }))
                }
              />
              In stock only
            </label>

            <label className="sort">
              Sort
              <select
                value={filters.sort}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, sort: e.target.value as SortKey }))
                }
              >
                {SORTS.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>

            {filtersActive && (
              <button className="link-btn" onClick={() => setFilters(NO_FILTERS)}>
                Reset filters
              </button>
            )}

            <span className="count">
              Showing {visible.length} of {products.length}
            </span>
          </div>
        </div>

        {error && (
          <div className="notice notice-error">
            We couldn't load the catalogue ({error}). Check that the shop service is
            running, then refresh.
          </div>
        )}

        {loading && !error && <div className="notice">Loading the catalogue…</div>}

        {!loading && !error && visible.length === 0 && (
          <div className="notice">
            {products.length === 0
              ? `Nothing matches “${query}”. Try a colour, a garment type, or a team.`
              : 'No products match those filters. Try widening them or reset.'}
          </div>
        )}

        <div className="grid">
          {visible.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </section>
    </>
  )
}
