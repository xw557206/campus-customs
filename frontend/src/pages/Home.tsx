import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import { ProductCard } from '../components/ProductCard'
import { BulldogCrest, BulldogMark } from '../components/BulldogMark'

export function Home() {
  const [featured, setFeatured] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchProducts()
      .then((data) => {
        if (cancelled) return
        // A small, varied set: one per garment type, in catalogue order.
        const seen = new Set<string>()
        const picks: Product[] = []
        for (const p of data.products) {
          const key = p.garment_type.toLowerCase()
          if (seen.has(key)) continue
          seen.add(key)
          picks.push(p)
          if (picks.length === 4) break
        }
        setFeatured(picks)
      })
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <p className="eyebrow">New Haven · Officially licensed</p>
          <h1>
            Wear the <span>Blue</span>.
          </h1>
          <p className="hero-lede">
            Campus Customs makes the Yale gear people actually keep — the crewneck that
            survives four winters, the tee you pull on the morning of The Game, the hoodie
            a parent quietly takes home. Every piece is officially licensed, and every
            piece is built to be worn, not folded away.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-primary">
              Shop the catalogue
            </Link>
            <Link to="/about" className="btn btn-ghost">
              Our story
            </Link>
          </div>
        </div>
        <div className="hero-crest" aria-hidden="true">
          <BulldogCrest size={190} />
        </div>
        <div className="hero-mark" aria-hidden="true">
          <BulldogMark size={420} mono />
        </div>
      </section>

      <section className="strip">
        <div>
          <strong>Officially licensed</strong>
          <span>Approved Yale marks on every garment</span>
        </div>
        <div>
          <strong>XS through XXL</strong>
          <span>Six sizes on every style we carry</span>
        </div>
        <div>
          <strong>Live stock</strong>
          <span>What the site shows is what is on the shelf</span>
        </div>
        <div>
          <strong>Here to help</strong>
          <span>Real answers about fit, colour and availability</span>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>A few favourites</h2>
          <Link to="/products" className="link-more">
            See everything →
          </Link>
        </div>

        {error && (
          <div className="notice notice-error">
            We couldn't load the catalogue just now ({error}). Please make sure the shop
            service is running, then refresh.
          </div>
        )}

        <div className="grid">
          {featured.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </section>

      <section className="band">
        <h2>Shopping for someone else?</h2>
        <p>
          Parents, alumni and the person who just needs something navy before Saturday —
          we help with all of them. Tell our assistant who it's for and we'll point you at
          something that fits, in a size we actually have.
        </p>
        <Link to="/products" className="btn btn-light">
          Browse the catalogue
        </Link>
      </section>
    </>
  )
}
