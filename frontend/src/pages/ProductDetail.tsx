import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type Product } from '../api'

export function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setProduct(null)
    setSelected(null)
    fetchProduct(productId)
      .then((p) => {
        if (cancelled) return
        setProduct(p)
        setError(null)
        // Preselect the first size that is actually available.
        setSelected(p.inventory.find((s) => s.quantity > 0)?.size ?? null)
      })
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [productId])

  if (loading) return <div className="section"><div className="notice">Loading…</div></div>

  if (error || !product) {
    return (
      <div className="section">
        <div className="notice notice-error">
          We couldn't find that product ({error ?? 'not found'}).
        </div>
        <Link to="/products" className="btn btn-primary">
          Back to the catalogue
        </Link>
      </div>
    )
  }

  const inStock = product.inventory.filter((s) => s.quantity > 0)
  const chosen = product.inventory.find((s) => s.size === selected)

  return (
    <section className="section">
      <nav className="crumbs">
        <Link to="/products">Products</Link>
        <span>/</span>
        <span>{product.name}</span>
      </nav>

      <div className="detail">
        <div className="detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div className="detail-info">
          <span className="card-type">{product.garment_type}</span>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p className="detail-desc">{product.description}</p>

          {product.colors.length > 0 ? (
            <div className="field">
              <h3>Colours</h3>
              <div className="chips">
                {product.colors.map((c) => (
                  <span key={c} className="chip">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div className="field">
              <h3>Colours</h3>
              <p className="muted">Not listed for this item.</p>
            </div>
          )}

          <div className="field">
            <h3>Sizes</h3>
            <div className="sizes">
              {product.inventory.map((s) => (
                <button
                  key={s.size}
                  className={[
                    'size',
                    s.quantity === 0 ? 'size-out' : '',
                    selected === s.size ? 'size-on' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  disabled={s.quantity === 0}
                  onClick={() => setSelected(s.size)}
                  title={s.quantity === 0 ? 'Out of stock' : `${s.quantity} in stock`}
                >
                  {s.size}
                </button>
              ))}
            </div>

            {inStock.length === 0 ? (
              <p className="muted">Every size is out of stock right now.</p>
            ) : chosen ? (
              <p className="muted">
                {chosen.quantity <= 5
                  ? `Only ${chosen.quantity} left in ${chosen.size}.`
                  : `${chosen.quantity} in stock in ${chosen.size}.`}
              </p>
            ) : (
              <p className="muted">Pick a size to see availability.</p>
            )}
          </div>

          <button className="btn btn-primary btn-wide" disabled={inStock.length === 0}>
            {inStock.length === 0 ? 'Out of stock' : `Add ${selected ?? ''} to bag`}
          </button>
          <p className="fineprint">
            Checkout isn't wired up yet — this storefront is still being built.
          </p>

          {product.search_tags.length > 0 && (
            <div className="field">
              <h3>Tags</h3>
              <div className="chips">
                {product.search_tags.map((t) => (
                  <span key={t} className="chip chip-quiet">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
