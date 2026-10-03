# Campus Customs — Usability Improvements

Four improvements: two on the front end, two in the agent and backend. All
four are live in the running app, and each section below says where to find it.

---

## 1. Front-end Improvement: Product Filtering and Sorting

### What I added

A filter and sort bar on the Products page, above the catalogue grid:

- **Category chips** — Hoodies, Crewnecks, T-shirts, Quarter-zips,
  Jackets & fleece, Long sleeve. Each shows a live count.
- **Colour chips** — Navy, Grey, White & cream, Black, Red, Blue.
- **"In stock only"** toggle, which hides anything with no stock in any size.
- **Sort** — Name A–Z, Price low→high, Price high→low, Most in stock.
- **"Showing N of 102"**, plus a Reset link once a filter is on.

The important part is not the controls themselves but what sits behind them.
Analysing the database in Problem 2 turned up two inconsistencies that make a
naive filter wrong:

- `garment_type` is free text with 22 distinct values. `short-sleeve t-shirt`
  (16 products) and `short-sleeve T-shirt` (6) are the same garment with
  different capitalisation, and **five** separate values describe hooded
  garments: `pullover hoodie`, `hoodie`, `hooded sweatshirt`,
  `hooded pullover sweatshirt`, `full-zip hooded sweatshirt`.
- `colors` has unmerged synonyms: `navy` and `navy blue` are the same colour,
  and there are six spellings of grey.

So the filters group raw values into families using case-insensitive substring
matching rather than exact equality. "Hoodies" returns **27** products — all
five spellings — and "T-shirts" returns **25**, which includes the 6 that an
exact, case-sensitive match would silently drop.

### Why it helps

**For the shopper:** 102 products in one grid is a wall. A shopper who wants a
navy hoodie under a budget can now get there in two clicks instead of
scrolling. "In stock only" matters especially here, because 145 of the 612
size options are out of stock — without it, people click into products they
cannot actually buy.

**For the business:** fewer dead-end clicks, and price sorting surfaces the
$32 tier (25 products) to budget-conscious shoppers rather than burying it.
Grouping the messy category values also means the shop does not have to clean
up the database before the filters are useful.

### Where to find it

- `frontend/src/filters.ts` — the category and colour groupings, sort logic,
  and the comments explaining which data problem each one works around.
- `frontend/src/pages/Products.tsx` — the filter bar and the filtered grid.
- In the app: **Products** page, the bar directly under the search box.

---

## 2. Front-end Improvement: Improved Chat UX

### What I added

Four changes to the floating chat widget:

- **Suggested prompts.** On opening, the widget offers three starters. They
  are **context aware**: on a product page they become "How much is this?",
  "What colours does this come in?", "Do you have this in medium?", which also
  teaches the shopper that the assistant knows what they are looking at.
- **A clearer loading state.** The animated dots are now paired with
  "Checking the catalogue…", so the wait reads as work being done rather than
  a stall. Replies involve real tool calls and can take a few seconds.
- **Distinct error styling with a retry.** A failure renders in red with
  "Your message wasn't lost — you can try again" and a **Try again** button
  that resends the original message. The shopper never retypes.
- **Duplicate-send protection.** Send is disabled while a request is in
  flight, so an impatient second click cannot fire a second request.

### Why it helps

**For the shopper:** an empty chat box is a blank-page problem — most people
do not know what a shop assistant can answer. The starters show the range in
one glance. When something breaks, a red bubble with a working retry is the
difference between "this is broken" and "that didn't go through, try again".

**For the business:** suggested prompts steer people toward questions the
agent answers well, which means fewer unhelpful first impressions. The retry
button recovers conversations that would otherwise be abandoned at the first
hiccup.

### Where to find it

- `frontend/src/components/ChatWidget.tsx` — `SUGGESTIONS` and
  `PRODUCT_SUGGESTIONS`, the `send(message, isRetry)` function, the
  `bubble-failed` branch and the retry button.
- `frontend/src/App.css` — `.suggest`, `.bubble-failed`, `.chat-retry`,
  `.typing-text`.
- In the app: click **Ask us**, bottom right. Open it on a product page to see
  the context-aware starters.

---

## 3. Agent/Backend Improvement: More Robust Product Search

### What I added

Typo-tolerant search, as a fallback inside the agent's `search_catalogue`
tool. When an exact and substring search returns nothing, the query is
compared against every product's name, garment type, colours and search tags
using `difflib.SequenceMatcher`, both whole-string and word-by-word, with a
similarity cutoff of 0.68.

Measured results:

| typed | exact matches | with fuzzy fallback |
| --- | --- | --- |
| `crewnek` | 0 | Baseball Left Chest Crewneck, Champion Reverse Weave Crewneck, … |
| `quater zip` | 0 | Benjamin Franklin 1 4 Zip, Berkeley 1 4 Zip, … |
| `sweatshrt` | 0 | the sweatshirt range |
| `bulldg` | 0 | the vintage Bulldog range |
| `harvrd` | 0 | 2025 Yale Vs Harvard T Shirt |
| `zzzqqq`, `asdfghjk`, `xylophone` | 0 | **0** — nonsense still finds nothing |

The fallback runs **only** when the normal search is empty, so it never
displaces a good exact match, and the cutoff is high enough that gibberish
still returns nothing rather than a random product.

### Why it helps

**For the shopper:** people type quickly and misspell. Before this, "do you
have any crewneks?" got "we don't seem to carry that", which is simply wrong —
the shop has 26 of them. Now it answers the question.

**For the business:** a missed search is a missed sale, and this is the
cheapest possible fix — no index, no new dependency, 102 rows compared in
memory. It also avoids the worse failure mode: a shopper concluding the shop
does not stock something it does.

### Where to find it

- `backend/db.py` — `fuzzy_find()`, with the cutoff and scoring.
- `backend/tools.py` — `search_catalogue()`, which calls it only when
  `list_products()` comes back empty.
- To see it: ask the chat **"do you have any crewneks?"**

---

## 4. Agent/Backend Improvement: Ambiguity and Hallucination Guardrails

### What I added

Two guards that stop the assistant asserting things the database did not say.

**Ambiguity — ask instead of guessing.** Product lookup resolves strongest
identifier first: exact `product_id`, then exact product name
(case-insensitive, and names are unique across all 102 rows), then a name
fragment that matches exactly one product. When a fragment matches several,
the tool chooses **nothing** — it returns the candidates with
`ambiguous: true` and a message telling the agent to ask. This matters because
"hoodie" appears in 25 product names and "yale" in 37.

> **"do you have this hoodie in medium?"** (no product open)
> → *"Which hoodie do you mean? We have the Basic Hoodie Big Yale, Brooks
> Brothers Double Knit Full Zip Hoodie Yale, Champion Reverse Weave Hoodie 1,
> and several others."*

**Hallucination — a card must be earned.** Every tool records the product ids
it actually returned into `ChatDeps.served_product_ids`. After the run, the
chat route renders cards **only** for ids in that set. An id the model
invented was never served, so it is dropped and logged.

Demonstrated directly: with one product served and three cited, both extras
were dropped — including `champion-full-zip-hood`, which is a **real product
in the catalogue**. Existing is not enough; a tool has to have returned it in
*this* run.

This is stricter than the earlier check, which only verified that an id
existed in the database.

### Why it helps

**For the shopper:** the two failure modes that destroy trust in a shop
assistant are confidently answering about the wrong product and inventing one
that does not exist. The first guard turns a guess into a question; the second
makes an invented product card structurally impossible rather than merely
discouraged by the prompt.

**For the business:** every claim shown as a product card traces to a database
read. That is the difference between a chatbot you can put in front of
customers and one you cannot — nobody has to apologise for an order placed
against a product the assistant made up.

### Where to find it

- `backend/tools.py` — `_resolve()` for the identifier ladder, `_record()` for
  the served-id tracking.
- `backend/models.py` — `ProductLookup.ambiguous`,
  `ChatDeps.served_product_ids`.
- `backend/main.py` — the guard in `api_chat`, which filters cited ids against
  the served set and logs any it drops.
- `backend/prompts/prompt.md` — the matching instruction to ask rather than
  choose.
- To see it: ask the chat **"do you have this hoodie in medium?"** with no
  product page open.

---

## Running the app

```bash
cd backend
uvicorn main:app --reload --port 8000
```

```bash
cd frontend
npm run dev
```

Then open http://localhost:5173.
