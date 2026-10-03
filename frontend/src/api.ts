// All product data comes from the FastAPI backend, which reads
// campus_customs.db. Nothing about a product is duplicated in the frontend.

export interface SizeStock {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_file_path: string
  image_url: string
  price: number
  inventory: SizeStock[]
  total_stock: number
}

export interface ProductList {
  count: number
  products: Product[]
}

export interface ChatResponse {
  reply: string
  products: Product[]
}

async function asJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      // response had no JSON body; keep the status text
    }
    throw new Error(detail)
  }
  return (await response.json()) as T
}

export async function fetchProducts(search?: string): Promise<ProductList> {
  const query = search ? `?search=${encodeURIComponent(search)}` : ''
  return asJson<ProductList>(await fetch(`/api/products${query}`))
}

export async function fetchProduct(productId: string): Promise<Product> {
  return asJson<Product>(await fetch(`/api/products/${encodeURIComponent(productId)}`))
}

/** Bearer header when signed in, nothing when a guest. */
function authHeaders(token?: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function sendChat(
  message: string,
  options: { token?: string | null; productId?: string | null } = {},
): Promise<ChatResponse> {
  return asJson<ChatResponse>(
    await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders(options.token) },
      // product_id tells the agent what the shopper has open, so "this"
      // resolves to the right product.
      body: JSON.stringify({ message, product_id: options.productId ?? null }),
    }),
  )
}

export interface ChatTurn {
  id: number
  role: 'user' | 'assistant'
  content: string
  products: Product[]
  created_at: string
}

export interface ChatHistory {
  turns: ChatTurn[]
  persisted: boolean
}

export async function fetchChatHistory(token: string): Promise<ChatHistory> {
  return asJson<ChatHistory>(
    await fetch('/api/chat/history', { headers: authHeaders(token) }),
  )
}

export async function clearChatHistory(token: string): Promise<void> {
  const res = await fetch('/api/chat/history', {
    method: 'DELETE',
    headers: authHeaders(token),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
}

/** Prices are stored as whole-dollar floats, so 68.0 must not render as "68.0". */
export function formatPrice(price: number): string {
  return `$${price.toFixed(0)}`
}

// ---------------------------------------------------------------------------
// Accounts
// ---------------------------------------------------------------------------

export interface User {
  id: number
  name: string
  first_name: string | null
  last_name: string | null
  email: string
  created_at: string
}

export interface AuthResponse {
  user: User
  token: string
}

export interface RegisterInput {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

export async function register(input: RegisterInput): Promise<AuthResponse> {
  return asJson<AuthResponse>(
    await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    }),
  )
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return asJson<AuthResponse>(
    await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }),
  )
}

export async function fetchMe(token: string): Promise<User> {
  return asJson<User>(
    await fetch('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } }),
  )
}
