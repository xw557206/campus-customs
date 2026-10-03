import { createContext, useContext, useMemo, useState } from 'react'
import type { Product } from './api'

/**
 * Products the assistant found, shared between the chat widget and the page.
 *
 * Plain React context rather than a state library — the app has no store and
 * this is one small piece of state. The widget writes; the Products page
 * reads and renders the results with the same `ProductCard` the catalogue
 * uses, so a chat result behaves exactly like a browsed one.
 */
interface ChatResultsState {
  products: Product[]
  query: string | null
  /** True once a search has run, so "no matches" can be told apart from "nothing searched yet". */
  searched: boolean
  setResults: (query: string, products: Product[]) => void
  clear: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: React.ReactNode }) {
  const [products, setProducts] = useState<Product[]>([])
  const [query, setQuery] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)

  const value = useMemo<ChatResultsState>(
    () => ({
      products,
      query,
      searched,
      // Every reply replaces the previous results, including with an empty
      // list — so a search that finds nothing clears stale cards rather than
      // leaving the last answer's products on screen.
      setResults(nextQuery, nextProducts) {
        setQuery(nextQuery)
        setProducts(nextProducts)
        setSearched(true)
      },
      clear() {
        setQuery(null)
        setProducts([])
        setSearched(false)
      },
    }),
    [products, query, searched],
  )

  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
