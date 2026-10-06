# Bernice Hairplace — Mobile Web UI/UX Design Prompt

## ROLE

Act as a senior mobile UI/UX designer, mobile e-commerce product designer, design-systems architect, conversion-rate optimization specialist, accessibility specialist, and luxury beauty/fashion digital designer.

Design a complete, production-ready **mobile web** UI/UX system for **Bernice Hairplace**, a premium hair extensions and accessories e-commerce store serving customers in Nigeria, with an initial focus on Lagos.

This is the **mobile version of the responsive website** (not a native app). It must cover the complete customer journey on a phone: browsing, search, filtering, persistent cart, Google sign-in, checkout, Paystack payment, payment states, confirmation, account, and order history.

Treat mobile as the **primary** experience. Most Bernice Hairplace customers will discover, browse and pay on a phone, often arriving from Instagram, TikTok or WhatsApp links.

## DESIGN OBJECTIVE

Create an attractive, minimalist, premium mobile shopping experience that communicates:

- Beauty
- Confidence
- Quality
- Elegance
- Trust
- Ease
- Modern African luxury
- Frictionless one-handed shopping

Prioritize:

**Product → clarity → trust → action → thumb reach**

The products and photography are the visual heroes. On a small screen every element must earn its space; UI should support the shopping journey, never compete with it.

Avoid the stereotypical "beauty website" look: excessive pink, gradients, glitter, bubbly rounded cards, decorative script fonts, or noisy layouts. Aim for a refined editorial aesthetic adapted to a narrow, vertical canvas.

---

# 1. MOBILE CONTEXT & CONSTRAINTS

Design for the real conditions of Nigerian mobile shoppers:

### Devices

- Primary target: **360px–430px** viewport width (Android mid-range and iPhone).
- Must also work at **320px** without breaking (small/older devices).
- Include both mid-range Android (Chrome) and iOS (Safari) considerations.
- Respect iOS safe areas (notch, home indicator) and Android gesture navigation bars.

### Network

- Assume variable 3G/4G connections and data-cost sensitivity.
- Pages must be usable before all images load.
- Prefer skeletons and progressive image loading over blank screens.
- Design graceful offline/poor-connection states.

### Usage patterns

- One-handed use, often while commuting or multitasking.
- Short sessions; customers may leave and return later — the persistent cart must make that seamless.
- Arrival via social links directly onto product pages (not always the homepage). Every product page must stand on its own.
- Frequent app-switching (to WhatsApp, banking apps, OTP SMS during Paystack payment). The experience must survive the customer leaving and returning.

### Orientation

- Design for **portrait**. Landscape must not break, but does not need a bespoke layout except for the image lightbox.

---

# 2. BRAND DIRECTION

## Brand

**Bernice Hairplace**

## Market

Nigeria / Lagos

## Currency

NGN / ₦ (format as ₦85,000 — no decimals unless the backend requires them)

## Product category

Hair extensions and accessories.

## Brand personality

- Elegant
- Feminine but not overly girly
- Confident
- Sophisticated
- Warm
- Contemporary
- Trustworthy
- Effortlessly premium

The experience should suit both everyday-hair customers and premium/occasion-hair customers.

## Mobile design principle

Use restraint — even more than on desktop.

Prefer:

- whitespace used deliberately, not wastefully
- full-bleed photography
- excellent typography at small sizes
- subtle dividers instead of boxed cards
- clear hierarchy in a single column
- calm, purposeful micro-interactions

Avoid:

- clutter and stacked banners
- pop-ups on arrival (newsletter, discount) that block content
- excessive badges and shadows
- tiny tap targets
- horizontal scrolling of page content (carousels excepted)
- competing accent colours

---

# 3. VISUAL STYLE

Minimalist luxury beauty/editorial aesthetic.

- **Primary background:** warm ivory / soft off-white
- **Primary text:** deep espresso / almost-black brown
- **Secondary text:** muted warm grey
- **Accent:** muted champagne / warm neutral gold
- **CTA:** darkest brand tone for high-confidence actions

No neon colours. Gold must not look metallic or flashy.

Use the accent sparingly for selected states, subtle highlights, premium indicators, and small details.

### Mobile-specific colour rules

- Verify all text contrast in **bright outdoor light** conditions — muted greys and champagne must still pass WCAG AA on ivory.
- Never use champagne/gold for body text or small text.
- Set the browser `theme-color` to match the header background.

---

# 4. TYPOGRAPHY (MOBILE)

### Display font

Elegant high-contrast serif for hero headlines, section headings and editorial moments only. Verify hairline strokes remain legible at mobile sizes; use a heavier optical weight if needed.

### UI/body font

Clean modern sans-serif for navigation, product names, prices, buttons, forms, checkout and account pages.

### Mobile type scale (starting point — refine in the design system)

```text
Display      32–36px   serif   line-height 1.1
H1           26–28px   serif   line-height 1.2
H2           22px      serif   line-height 1.25
H3           18px      sans    line-height 1.3   medium
Body Large   17px      sans    line-height 1.5
Body         15–16px   sans    line-height 1.5
Small        13–14px   sans    line-height 1.45
Caption      12px      sans    line-height 1.4
Label        12–13px   sans    medium, slight letter-spacing
Price        15–17px   sans    medium, tabular numerals
```

Rules:

- **Form inputs must use at least 16px text** to prevent iOS auto-zoom on focus.
- Never go below 12px for any text.
- Support user font scaling (up to 200%) without truncating prices, CTAs, or order totals.
- Limit line length; avoid long centred paragraphs.
- No decorative script fonts in functional UI.

---

# 5. MOBILE DESIGN SYSTEM

Create a reusable mobile-first design system before designing screens.

### Colors

Background, Surface, Primary text, Secondary text, Border/divider, Accent, Success, Warning, Error, Info, Overlay/scrim.

### Typography

Families, weights, sizes, line heights, letter spacing (per the scale above).

### Spacing

4px base scale (4, 8, 12, 16, 20, 24, 32, 40, 48, 64).

- Default page side gutter: **16px** (20px on ≥400px widths if desired).
- Vertical section spacing: 40–56px.

### Touch targets

- Minimum **44×44px** for every interactive element; prefer **48px** for primary actions.
- Minimum 8px gap between adjacent targets.

### Radius

Restrained: 2–6px for inputs/buttons, 0–4px for imagery. Bottom sheets may use 12–16px top corners only.

### Elevation

Extremely soft shadows, used only for sticky bars, bottom sheets and drawers.

### Icons

One consistent thin-line icon family, 20–24px, always inside a 44px+ hit area. Icon-only buttons need accessible labels.

---

# 6. MOBILE NAVIGATION

## Header

```text
------------------------------------------------
☰   🔍        BERNICE HAIRPLACE         👤  Bag (2)
------------------------------------------------
```

- Height ~56px, sticky.
- Wordmark centred; menu and search on the left; account and bag on the right.
- Bag count always visible.
- Optional transparent/editorial state over the homepage hero, switching to solid ivory after scroll.
- On scroll down, the header may hide; on scroll up, it reappears. Keep transitions calm — no aggressive shrinking.
- Respect the top safe area.

## Menu drawer (☰)

Full-height drawer sliding from the left:

```text
✕                                  

SHOP ALL
Hair Extensions
Wigs
Closures & Frontals
Bundles
Accessories

COLLECTIONS
New Arrivals
Best Sellers

ABOUT
Contact / Help

----------------------
My Account
Orders
Sign in with Google
----------------------
Instagram  TikTok  WhatsApp
```

- Show only categories and links that actually exist.
- Large tap rows (48–56px).
- Closes on ✕, scrim tap, swipe, and Android back.
- Focus is trapped while open and returns to the menu button on close.

## Bottom navigation

Do **not** use a persistent app-style bottom tab bar by default — it competes with sticky purchase bars. The bottom of the screen is reserved for context-specific primary actions (Add to Bag, Checkout, Pay).

## Back behaviour

- Browser back must always behave predictably (closes sheets/drawers/lightbox before leaving the page).
- Preserve scroll position and applied filters when returning from a product to the catalogue.

---

# 7. MOBILE HOMEPAGE

Keep it shorter than desktop. Structure:

```text
Header
Hero (full-bleed)
Shop by Category (horizontal scroll)
Best Sellers (2-column grid or carousel)
Brand Story (short editorial block)
Shop by Collection
Why Bernice Hairplace (3 compact trust points)
New Arrivals
Social Proof / Instagram
Contact / WhatsApp CTA
Footer
```

## Hero

- Full-bleed portrait image (approx. 4:5 or 3:4), with the subject's face/hair clear of the text area.
- Concise headline, one supporting line, one primary CTA, optional text-link secondary CTA.

Example:

> Hair that completes the look.

**[ Shop Hair ]**  
Explore Collections →

- Primary CTA full-width or near full-width, 48px tall.
- Hero must not exceed ~85% of the viewport height so the next section is hinted.
- Subtle gradient scrim only where needed for contrast.
- No autoplay video hero.

## Category section

- Horizontally scrolling row of portrait category cards (~70–75% width each, so the next card peeks).
- Image + category name + "Shop" affordance.
- Scroll-snap; no auto-advancing carousels.

## Trust points

Three compact rows with a thin icon, e.g.:

- Secure payment via Paystack
- Delivery across Lagos (state actual coverage only)
- Real support on WhatsApp (only if offered)

No unsupported claims.

---

# 8. SHOP / CATALOGUE (MOBILE)

```text
------------------------------------------------
SHOP · Wigs                        124 items

[🔍 Search hair, wigs, accessories…]

[ Filter (2) ]      [ Sort: Featured ▾ ]
[Bone Straight ✕] [Under ₦100k ✕]
------------------------------------------------
| Product      | Product      |
| Product      | Product      |
------------------------------------------------
```

- **2-column grid** by default with consistent 3:4 or 4:5 image ratio.
- Switch to 1 column only for visually complex products, or offer a subtle grid/list toggle if valuable.
- Filter and Sort sit in a sticky toolbar that appears below the header when scrolling.
- Show active filters as removable chips (horizontally scrollable).
- Show result count.
- Pagination: "Load more" button or infinite scroll with a visible footer escape; preserve position on back.

---

# 9. PRODUCT CARD (MOBILE)

```text
[ IMAGE  3:4 ]
Product Name (max 2 lines)
Short descriptor (1 line, optional)
₦XX,XXX
```

Optional single label: `New`, `Bestseller`, or `Low Stock` — one per card maximum.

- Entire card is one tap target.
- No hover-dependent content. No hidden secondary image on hover.
- Optional small "+" quick-add only for products with no required variants; otherwise tapping opens the product page.
- Out-of-stock products: clear text label, image slightly muted, not hidden behind colour alone.
- Truncate names gracefully; never truncate prices.

---

# 10. SEARCH (MOBILE)

- Tapping the search icon opens a **full-screen search overlay** with the input auto-focused and the keyboard raised.
- Input uses `type="search"` with a clear (✕) button and a Cancel action.

Overlay contents:

- **Before typing:** recent searches (stored locally), popular categories.
- **While typing:** live suggestions (products with thumbnail + price, categories).
- **Results:** 2-column product grid with result count.
- **No results:**

> No matches for "bone stright".

Suggestions: check spelling, browse categories, view best sellers, clear search.

- **Loading:** skeleton suggestion rows.
- **Error:** concise message + Try Again.

Search supports product names, SKU, relevant descriptions and categories. Dismiss the keyboard on scroll of results.

---

# 11. FILTER & SORT (MOBILE)

## Filter — bottom sheet

```text
------------------------------------------------
Filter                                  Clear all
------------------------------------------------
Category                                      ▾
Price                                         ▾
Length                                        ▾
Texture / Type                                ▾
Availability                                  ▾
------------------------------------------------
[         Show 48 results          ]
------------------------------------------------
```

- Opens as a tall bottom sheet (or full-screen on small devices).
- Accordion sections; selected counts shown on headers.
- Apply button shows a live result count.
- Length as tappable chips (e.g. 12", 14", 16"); price as preset ranges plus optional min/max with numeric keyboard.
- Only show filters supported by real product data.
- Drag handle, swipe-down to dismiss, scrim tap, and back button all close it without applying unless the user tapped Apply.

## Sort — small bottom sheet

Radio list: Featured, Newest, Price: Low to High, Price: High to Low. Selecting applies immediately and closes.

---

# 12. PRODUCT DETAIL PAGE (MOBILE)

Order of content:

```text
Header
[ Full-width image gallery — swipe ]
  ● ○ ○ ○ ○   (position indicator)

Product Name
₦XX,XXX
In stock · Ready to ship (actual availability)
Rating/reviews (only if real reviews exist)

Short description (2–3 lines)

Length:   [12"] [14"] [16"] [18"]
Texture:  [Straight] [Body Wave]
Quantity: [ − 1 + ]

Delivery estimate / delivery info
Returns / exchange note

▸ Description
▸ Specifications
▸ Care Guide (if available)
▸ Delivery & Returns

Complete the Look (horizontal scroll)
You May Also Like
```

## Sticky purchase bar

```text
------------------------------------------------
₦85,000                    [   Add to Bag   ]
------------------------------------------------
```

- Appears once the main Add to Bag button scrolls out of view.
- Sits above the bottom safe area; does not cover content (add bottom padding to page).
- If a required variant is unselected, tapping it scrolls to the options and highlights them with a clear message ("Select a length").
- Variant price changes update immediately in both the page price and the sticky bar.
- Out-of-stock variants: visibly disabled with text label, not just strikethrough colour.

Details live in accordions to keep the page scannable.

---

# 13. PRODUCT IMAGES (MOBILE)

- Swipeable full-width gallery with scroll-snap and position dots/counter (e.g. 2/5).
- Consistent ratio (recommend 4:5) across all products.
- Tap opens a **full-screen lightbox** with pinch-to-zoom, double-tap zoom, swipe between images, and swipe-down/✕ to close.
- Include close-up texture shots and lifestyle images where available.
- First image loads with priority; others lazy-load. Show a neutral placeholder (blur or solid tone) while loading.
- Every image has meaningful alt text.

---

# 14. ADD TO BAG CONFIRMATION (MOBILE)

After adding an item, show a restrained bottom sheet or toast — do not redirect:

```text
------------------------------------------------
✓ Added to your bag
[img] Bone Straight Wig · 16"      ₦85,000

[ View Bag (2) ]   [ Continue Shopping ]
------------------------------------------------
```

- Bag count in header animates subtly.
- Auto-dismisses after a few seconds if not interacted with (toast variant), or stays until dismissed (sheet variant) — pick one and use it consistently.
- Announce the update to screen readers.
- Disable the Add to Bag button during the request to prevent double-adds; show a loading state.

---

# 15. SHOPPING BAG (MOBILE)

Use a full page (preferred on mobile) rather than a narrow drawer.

```text
------------------------------------------------
Shopping Bag (2)
------------------------------------------------
[img] Product Name                   ₦85,000
      16" · Straight
      [ − 1 + ]                      Remove
------------------------------------------------
[img] Product Name                   ₦12,000
      [ − 1 + ]                      Remove
------------------------------------------------
Add a finishing touch (optional, quiet)
------------------------------------------------
Subtotal                             ₦97,000
Delivery                Calculated at checkout
------------------------------------------------
Total                                ₦97,000
------------------------------------------------
[        Checkout · ₦97,000        ]  ← sticky
Continue Shopping
------------------------------------------------
```

- Sticky Checkout bar at the bottom with the total visible.
- Quantity steppers with 44px targets; respect stock limits with a clear message.
- Remove offers an **Undo** toast rather than a confirmation dialog.
- Price changes or stock changes since the item was added must be flagged clearly on the item.
- Persistence should feel invisible: the bag is simply there when the customer returns.

## Empty bag

> Your bag is empty.

Short supporting line, then **[ Shop the collection ]** plus a few best sellers below so it is never a dead end.

---

# 16. AUTHENTICATION (MOBILE)

Full-screen, minimal:

```text
✕

Welcome back.

Sign in to check out and track your orders.

[ G  Continue with Google ]

Continue as guest   ← only if guest checkout is supported
```

- Google button full-width, 48px+.
- Handle the OAuth redirect gracefully: show "Signing you in…" on return, then send the user back exactly where they were (e.g. checkout with bag intact).
- Account for in-app browsers (Instagram/TikTok webviews), where Google sign-in may be blocked. Detect this where possible and show a clear message with an "Open in browser" instruction. Never let the customer lose their bag.
- No email/password screens unless engineering later introduces them.

---

# 17. CHECKOUT (MOBILE)

Single focused column. No site navigation distractions — use a simplified checkout header:

```text
------------------------------------------------
←      Secure Checkout              🔒
------------------------------------------------
```

Progress indicator (compact):

```text
Details ── Delivery ── Review ── Pay
```

## Order summary

Collapsed by default at the top:

```text
▸ Show order summary              ₦97,000
```

Expands inline to show items, subtotal, delivery, tax (if applicable) and total.

## Steps

1. **Contact** — email (prefilled from Google), phone.
2. **Delivery** — address fields, delivery option (if applicable) with price and timeframe.
3. **Review** — items, address, totals, edit links.
4. **Pay** — Paystack hand-off.

Steps may be one scrolling page with sections or separate screens; choose based on field count. Keep the customer's progress if they leave and return.

## Sticky pay bar

```text
------------------------------------------------
Total ₦103,500
[        Pay ₦103,500        ]
Secure payment via Paystack
------------------------------------------------
```

---

# 18. CHECKOUT FORM DESIGN (MOBILE)

- Labels always visible above fields (no placeholder-only labels).
- Inputs 48px tall, 16px+ text.
- Correct keyboards and autofill:

```text
Email        type="email"   autocomplete="email"
Phone        type="tel"     autocomplete="tel"         inputmode="tel"
Name         autocomplete="name"
Address      autocomplete="street-address"
City         autocomplete="address-level2"
State        select (Nigerian states)  autocomplete="address-level1"
```

- Phone field with +234 prefix; accept both 080… and +23480… formats.
- Optional "Nearest landmark / delivery note" field only if the backend stores it.
- Validate on blur, not on every keystroke. Inline errors below the field, linked to it, announced to screen readers.
- On submit with errors, scroll to and focus the first error.
- Ensure the keyboard never covers the focused field or the primary CTA.
- Only collect fields the backend actually requires.

Error example:

> Please enter a valid Nigerian phone number.

No technical error messages.

---

# 19. PAYSTACK PAYMENT EXPERIENCE (MOBILE)

Make it clear the CTA moves the customer to Paystack's secure payment flow.

CTA: **Pay ₦XX,XXX**  
Supporting text: **Secure payment via Paystack**

### Mobile-specific requirements

- Disable the pay button immediately on tap and show a loading state to prevent double payment.
- Expect customers to switch apps (bank app, SMS OTP, USSD). The return URL must land on a clear status screen, not the bag.
- If the customer returns via browser back or reopens the tab, show the current payment state rather than a fresh checkout.
- Never display "Payment successful" until the application has authoritative confirmation.
- Status screens must be readable at a glance and work at large font sizes.

### States

**Initializing**

```text
Preparing your secure payment…
```

**Redirecting**

```text
Redirecting to Paystack…
```

**Pending**

```text
We're confirming your payment.

Your order has been received and payment
confirmation is in progress. This page will
update automatically.

Please don't pay again.
```

**Successful**

```text
Payment successful.
Order #ORD-XXXX
Thank you for shopping with Bernice Hairplace.
```

**Failed**

```text
Payment could not be completed.
Your order has not been confirmed.

[ Try Payment Again ]
Return to Bag
```

**Abandoned**

```text
Payment was not completed.
Your bag is saved.

[ Complete Payment ]
```

**Verification error**

```text
We're still verifying your payment.
Please don't make another payment yet.

[ Check Status ]
Contact support
```

Design to remove duplicate-payment anxiety.

---

# 20. ORDER SUCCESS (MOBILE)

Calm, restrained, celebratory.

```text
✓

Payment successful

Thank you, [First Name].

Order #ORD-XXXX
₦103,500 paid

A confirmation email has been sent to
name@email.com

▸ Order summary
▸ Delivery details

[        View Order        ]
Continue Shopping
```

- Subtle success icon; no confetti or heavy animation.
- Order number selectable/copyable.
- Clear next step (what happens with delivery).

---

# 21. PAYMENT FAILURE (MOBILE)

State plainly:

- what happened
- that the order is **not** confirmed
- whether money may have been debited (and that reversals are handled per Paystack/bank timelines, if applicable)
- how to retry

Primary: **Try Payment Again** (sticky)  
Secondary: **Return to Bag**  
Tertiary: Contact support

---

# 22. ACCOUNT (MOBILE)

```text
------------------------------------------------
Hello, Ada

[ Orders              › ]
[ Profile             › ]
[ Addresses           › ]
[ Help & Contact      › ]

Sign Out
------------------------------------------------
```

- Stacked full-width rows (56px), each opening its own screen with a back arrow.
- Show the most recent order as a compact card at the top of the overview if one exists.

---

# 23. ORDER HISTORY (MOBILE)

Card list, not a table:

```text
------------------------------------------------
ORD-20261002-0001                       ›
2 Oct 2026 · 2 items
₦85,000
[ Paid ]  [ Processing ]
------------------------------------------------
```

Whole card is tappable.

Status semantics (text label always present, never colour alone):

- Paid / Delivered → success
- Pending → warning
- Failed / Reversed → error/attention
- Processing / Shipped → neutral/info

Empty state:

> You haven't placed an order yet.

**[ Start shopping ]**

---

# 24. ORDER DETAIL (MOBILE)

Vertical sections:

- Order number, date
- Payment status, fulfilment status (with a simple vertical progress timeline for fulfilment)
- Items (thumbnail, name, variant, qty, price)
- Subtotal, delivery, tax, total
- Delivery address
- Payment reference (where safe)
- Need help? → contact / WhatsApp (if offered)

Never expose sensitive Paystack data.

---

# 25. EMPTY / LOADING / ERROR / OFFLINE STATES

- **Empty search:** "No matches found." → Browse all products
- **Empty bag:** "Your bag is empty." → Shop the collection
- **Empty orders:** "You haven't placed an order yet." → Start shopping
- **Loading:** elegant skeletons matching final layouts; avoid full-screen spinners. Spinners only inside buttons.
- **Error:** concise explanation + **Try Again** + support option where appropriate.
- **Offline / poor connection:** a slim non-blocking banner ("You're offline. Some content may not load."). Keep already-loaded content visible. Disable payment actions while offline with a clear reason.
- **Slow image loads:** placeholder tone/blur at the correct ratio so layout never jumps.

---

# 26. GESTURES & MOBILE INTERACTIONS

Supported:

- Swipe: product galleries, horizontal carousels, lightbox
- Pinch/double-tap: zoom in lightbox only
- Swipe down: dismiss bottom sheets and lightbox
- Pull-to-refresh: native browser behaviour only — do not build custom pull-to-refresh

Rules:

- Every gesture must have a visible button alternative (✕, arrows, dots).
- No swipe-to-delete without an alternative Remove button.
- Don't hijack vertical scroll.
- Avoid accidental taps: keep destructive actions away from primary CTAs.

---

# 27. THUMB-ZONE LAYOUT RULES

- Primary actions (Add to Bag, Checkout, Pay, Apply filters) sit in the **bottom third** of the screen, usually in sticky bars.
- Secondary/rare actions (menu, account, sign out) may sit at the top.
- Only **one** sticky bottom bar on screen at a time.
- Sticky bars respect `env(safe-area-inset-bottom)`.
- Sticky elements combined must not take more than ~25% of viewport height.

---

# 28. MICRO-INTERACTIONS

Appropriate:

- button press feedback (subtle opacity/scale)
- bag count update
- bottom sheet / drawer open & close (200–300ms, ease-out)
- toast appearance
- skeleton shimmer (subtle)
- variant selection

Avoid parallax, bouncing, continuous animation, autoplay hero video, scroll-jacking.

Respect `prefers-reduced-motion`: replace slides with fades or instant changes.

---

# 29. MOBILE FOOTER

Collapsed accordion groups to save space:

```text
BERNICE HAIRPLACE
Beautiful hair. Effortless confidence.

▸ Shop
▸ Help (Contact, Delivery, Returns, FAQs)
▸ Account

Instagram   TikTok   Facebook   WhatsApp

© Bernice Hairplace · Privacy · Terms
```

Only show links that exist. Add bottom padding so sticky bars never cover the footer.

---

# 30. TRUST & CONVERSION (MOBILE)

Understated trust signals placed near decisions:

- "Secure payment via Paystack" under every pay CTA
- Delivery info on product pages and in the bag
- Returns/exchange policy one tap away
- Visible support channel (WhatsApp/contact) in checkout and order screens if offered
- Clear stock status

No unsupported claims ("100% guaranteed", "Best hair in Nigeria", "Number one", "Officially certified") without evidence.

No entry pop-ups, countdown timers, or fake scarcity.

---

# 31. DISCOVERY, CROSS-SELL & UP-SELL

- Product page: "Complete the Look" horizontal row (quiet, after details).
- Bag: "Add a finishing touch" — one compact row, maximum 3–4 items.
- Recently viewed (if technically appropriate) on homepage or empty states.
- **No upsells in checkout or payment screens.**

---

# 32. MOBILE ACCESSIBILITY

Target WCAG 2.2 AA:

- Semantic HTML and landmarks
- Touch targets ≥ 44×44px (WCAG 2.5.8 minimum 24px; we exceed it)
- Visible focus states for keyboard/switch users
- Sufficient contrast, including on images
- Bottom sheets, drawers and lightbox are accessible dialogs: focus trap, labelled, closable with Escape/back
- Live regions for bag updates, form errors and payment status changes
- No colour-only status indicators
- Supports text resizing to 200% and screen zoom (do not disable pinch-zoom on the page)
- Works with TalkBack (Android) and VoiceOver (iOS)
- Reduced-motion support
- Avoid content that requires precise dragging (WCAG 2.5.7) — provide tap alternatives

---

# 33. PERFORMANCE-AWARE MOBILE DESIGN

Design for Next.js on Vercel with low-bandwidth users in mind:

- Consistent image ratios (4:5 product, 3:4 category, defined hero ratio) so `next/image` can serve correct sizes.
- Hero image is the LCP element: design it to be a single optimized image, no video.
- Lazy-load below-the-fold imagery and carousels.
- Avoid heavy third-party widgets (e.g. embedded social feeds); use static image grids linking out.
- Limit web fonts to 2 families and few weights; define fallback fonts with similar metrics to reduce layout shift.
- Reserve space for all images, badges and banners to avoid layout shift.
- Target Core Web Vitals "good" on mid-range Android over 4G.

---

# 34. COMPONENT LIBRARY (MOBILE)

```text
Button (full-width + inline)
IconButton
Input / PhoneInput / Select (native on mobile)
Checkbox / Radio / Chip
Badge
Toast
BottomSheet
Drawer (menu)
Lightbox
Accordion
Tabs (only if needed)
StickyActionBar
Header / CheckoutHeader
SearchOverlay
ProductCard
ProductGrid
HorizontalCarousel
ImageGallery
VariantSelector
Price
QuantitySelector
FilterSheet / SortSheet
FilterChips
CartItem
OrderSummary (collapsible)
CheckoutProgress
AddressForm
PaymentStatus
OrderStatus
OrderCard
StatusTimeline
EmptyState
ErrorState
OfflineBanner
Skeletons
```

Variants: primary, secondary, outline, ghost, destructive, disabled, loading.

Use native `<select>` and native date/number inputs on mobile where practical — they are more accessible and familiar than custom dropdowns.

---

# 35. DESIGN TOKENS

Tokens for:

```text
colors
typography
spacing
radius
shadows
breakpoints (320, 360, 390, 430, 768)
safe-area insets
touch-target sizes
z-index (header, sticky bar, sheet, drawer, toast, lightbox)
transitions / durations / easing
container widths & gutters
```

No hardcoded one-off values.

---

# 36. FIGMA FILE STRUCTURE

```text
00 — Cover
01 — Mobile Design Principles & Context
02 — Brand / Visual Direction
03 — Design Tokens
04 — Components (mobile)
05 — Navigation, Menu Drawer & Search Overlay
06 — Homepage
07 — Shop, Filter & Sort Sheets
08 — Product Detail & Lightbox
09 — Add to Bag & Bag
10 — Authentication (incl. in-app browser state)
11 — Checkout
12 — Payment States
13 — Order Confirmation
14 — Account & Orders
15 — Empty / Loading / Error / Offline
16 — Accessibility & Gestures
17 — Prototype / User Flows
```

Frames: design at **390×844** (primary) and validate at **360×800** and **320×568**. Show keyboard-open states for all form screens.

---

# 37. CORE MOBILE SCREENS

1. Homepage
2. Menu drawer
3. Search overlay (default, typing, results, no results)
4. Shop/catalogue
5. Filter bottom sheet
6. Sort bottom sheet
7. Product detail (top, scrolled with sticky bar)
8. Image lightbox
9. Add-to-bag confirmation
10. Bag
11. Empty bag
12. Sign in (incl. in-app browser warning)
13. Checkout — contact, delivery, review (incl. keyboard-open state)
14. Payment initializing / redirecting
15. Payment pending
16. Payment success / order confirmation
17. Payment failed
18. Payment abandoned
19. Verification error
20. Account overview
21. Order history
22. Order detail
23. Empty orders
24. Error state
25. Offline banner state

---

# 38. PRIMARY MOBILE FLOWS

**Flow A — Social link to Bag**

```text
Instagram/TikTok/WhatsApp link
→ Product page (direct landing)
→ Select variant
→ Add to Bag
→ Confirmation sheet
→ Continue shopping or View Bag
```

**Flow B — Purchase**

```text
Bag
→ Sign in with Google (return to checkout)
→ Contact & Delivery
→ Review
→ Pay with Paystack (app switch / OTP)
→ Return → Pending
→ Payment Success
→ Order Confirmation
```

**Flow C — Failed / Abandoned Payment**

```text
Checkout → Paystack → Failed or closed
→ Return → Clear status
→ Try Again → Success
```

**Flow D — Returning Customer**

```text
Homepage → Account → Orders → Order Detail
```

**Flow E — Interrupted Session**

```text
Add to Bag → leave site → return later
→ Bag intact → Checkout resumes
```

---

# 39. CONVERSION PRINCIPLES (MOBILE)

- One obvious primary CTA per screen, in the thumb zone.
- Price and availability visible without scrolling on product pages.
- Total always visible in the bag and checkout.
- Minimal fields; correct keyboards; autofill everywhere.
- Errors are recoverable without losing entered data.
- Payment status is unmistakable.
- Product context is maintained throughout checkout.
- No dark patterns, forced sign-up walls before browsing, or manipulative urgency.

---

# 40. ENGINEERING ALIGNMENT

The UI must map to the existing architecture:

```text
Next.js
Supabase
Supabase Auth
Google OAuth
Paystack
Mailgun
Vercel
```

And support:

- persistent cart (across sessions and sign-in)
- authenticated account
- server-authoritative checkout and pricing
- payment initialization
- payment verification on return
- webhook-driven payment confirmation (UI polls or refreshes status while pending)
- order state management
- confirmation email
- order history

Do not design states the backend cannot represent.

---

# 41. PAYMENT & ORDER STATE ALIGNMENT

```text
Payment (backend)          Mobile UI
------------------------------------------------
pending_payment            Awaiting payment
initialized                Redirecting to Paystack
pending                    Confirming payment
success                    Payment successful
failed                     Payment failed
abandoned                  Payment not completed
reversed                   Payment reversed
refunded                   Payment refunded
```

```text
Order (backend)            Mobile UI
------------------------------------------------
pending_payment            Awaiting payment
paid                       Paid
processing                 Processing
shipped                    Shipped
delivered                  Delivered
cancelled                  Cancelled
payment_failed             Payment failed
payment_reversed           Payment reversed
refunded                   Refunded
```

Always pair visual styling with text labels.

---

# 42. DEVELOPER HANDOFF (MOBILE)

For every screen provide:

- 390px design plus 360px and 320px checks
- tablet behaviour notes (768px) where the layout changes
- component mapping
- spacing and typography specs
- sticky element behaviour and safe-area handling
- keyboard-open behaviour for forms
- gesture behaviour and button alternatives
- back-button behaviour for overlays
- loading, empty, error and offline states
- accessibility notes (focus order, labels, live regions)

For interactive elements document: default, pressed/active, focus, disabled, loading, success, error. (Hover is not a mobile state — do not rely on it.)

---

# 43. DESIGN QUALITY BAR

The finished mobile design should feel:

- premium, calm and editorial
- fast, even on average connections
- natural to use with one thumb
- trustworthy at the moment of payment
- Nigerian-market appropriate
- original — not a copy of any existing brand

It should resemble a polished direct-to-consumer beauty brand on mobile, not a shrunk-down desktop site or a generic template.

---

# 44. DELIVERABLES

1. Mobile visual direction
2. Mobile design system & tokens
3. Colour palette (with outdoor-contrast checks)
4. Mobile typography system
5. Spacing, gutter, and thumb-zone rules
6. Mobile component library
7. High-fidelity screens at 390px (validated at 360px and 320px)
8. Complete shopping flow
9. Complete checkout flow incl. keyboard states
10. Complete Paystack payment-state screens
11. Account and order experience
12. Empty / loading / error / offline states
13. Gesture and interaction specifications
14. Accessibility specifications
15. Developer handoff specifications
16. Interactive mobile prototype of the critical purchase journey (Flows A, B, C)

---

# 45. FINAL MOBILE UX ACCEPTANCE CRITERIA

A new customer on a phone can complete this journey without instruction, using one hand:

```text
Discover → Browse → Choose → Add to Bag → Review
→ Checkout → Pay with Paystack → Payment Confirmed → Order Confirmed
```

At every point the customer knows:

- what product they are viewing
- how much it costs
- how many items are in the bag
- the current total
- what the primary button will do
- whether payment is pending, successful or failed
- whether the order is actually confirmed
- how to recover from an error or interruption
- where to find their order later

And additionally:

- no primary action is out of thumb reach
- no form field is hidden by the keyboard
- leaving for a bank app or OTP and returning never loses progress
- the bag survives closing the browser
- the experience remains usable on a slow connection
