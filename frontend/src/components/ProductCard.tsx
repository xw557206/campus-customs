import { useState } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice, type Product } from '../api'

/** Sizes with stock, in wearable order (the API already sorts them). */
function sizesInStock(product: Product): string[] {
  return product.inventory.filter((s) => s.quantity > 0).map((s) => s.size)
}

export function ProductCard({ product }: { product: Product }) {
  const available = sizesInStock(product)
  // A missing image file must not leave a broken-image icon in the grid.
  const [imageFailed, setImageFailed] = useState(false)

  return (
    <Link to={`/products/${product.product_id}`} className="card">
      <div className="card-image">
        {imageFailed ? (
          <span className="image-missing">Image unavailable</span>
        ) : (
          <img
            src={product.image_url}
            alt={product.name}
            loading="lazy"
            onError={() => setImageFailed(true)}
          />
        )}
      </div>

      <div className="card-body">
        <span className="card-type">{product.garment_type}</span>
        <h3 className="card-name">{product.name}</h3>
        <p className="card-desc">{product.description}</p>

        <div className="card-foot">
          <span className="card-price">{formatPrice(product.price)}</span>
          {available.length === 0 ? (
            <span className="tag tag-out">Out of stock</span>
          ) : available.length < product.inventory.length ? (
            <span className="tag tag-some">{available.length} of 6 sizes</span>
          ) : (
            <span className="tag tag-in">All sizes</span>
          )}
        </div>
      </div>
    </Link>
  )
}
