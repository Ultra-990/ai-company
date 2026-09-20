"""Teacher-owned requirements. No page implementation or model-written tests."""
import json

FILES = ('index.html', 'style.css', 'app.js')
SYSTEM = '''You are the local website implementer. Write the entire website yourself:
HTML, CSS, JavaScript, illustrations and interactions. No supplied page templates.
The teacher provides requirements and later independent failure reports, not fixes.
Return only the requested JSON. Never claim tests ran. No tools or host commands.
Use native browser APIs, Polish UI, local style.css and deferred app.js. No imports,
remote resources, inline script, event attributes, eval, storage, service workers,
network requests, OS controls, automatic focus or automatic navigation.
CSS/inline SVG illustrations are allowed. HTML/CSS/JS will run only in a sandbox.
Keep source compact enough for the response limit, but deliver complete code.'''

def catalog(variant):
    countries = ['Polska', 'Japonia', 'Francja', 'Norwegia', 'Włochy', 'Kanada']
    categories = ['Kosmos', 'Przyroda', 'Architektura', 'Transport']
    return [dict(id=f's{i+1:02}', title=f'{categories[(i+variant)%4]} — {countries[i%6]} {1960+i}',
                 country=countries[i%6], category=categories[(i+variant)%4],
                 year=1960+i, price=25 + ((i*37+variant*19)%170)) for i in range(12)]

def brief(variant=0):
    return '''Build a complete polished demonstration shop for a private stamp
collector starting to sell a collection. Design your own visual identity, layout,
typography, colors and illustrated stamp cards. Responsive 320/390/768/1440px.
Do not copy a previous demo. No genuine rarity claims or real payment/order.
All products are illustrative, single quantity. Display a visible Polish demo notice.
Use this exact fixture catalog (keep prices as integer PLN, do not invent stock):
''' + json.dumps(catalog(variant), ensure_ascii=False) + '''
Functional acceptance contract (selectors enable independent browser testing):
- Header with h1, #menu-toggle button (aria-expanded), #site-menu nav; collapsed
  initially on phone, toggle both ways, Escape closes it. Menu links to sections.
- #country and #category SELECTs: empty value means all. All catalog values
  present; exact filters intersect. #search INPUT searches title/country,
  case insensitive and trimmed. #sort SELECT: featured, price-asc, price-desc.
  #clear resets these four controls and results. #empty visible only with no results.
- #products contains ONLY currently matching .product cards. Each card has
  data-id, data-price, data-country, data-category matching the fixture and visible
  title/price, original CSS/SVG stamp illustration and button [data-open="ID"].
- Clicking a product opens #gallery DIALOG using showModal(). Set its data-id
  to current product ID; show title and price in #detail; #prev/#next cycle through
  currently filtered products in rendered sort order; #close-gallery closes it.
  #add adds the shown product once; duplicate attempts cannot increase quantity.
- #cart-count textContent is just count as integer; #cart-total textContent is just
  total as integer (currency label outside). Cart always visible in section #cart.
  Each cart row .cart-row has data-id and button [data-remove="ID"]. Removing updates
  count/total and invalidates any old checkout summary. Empty cart disables #checkout.
- #checkout displays #receipt with visible Polish text that no payment was taken
  and no order was sent. #receipt hidden initially and on any cart change.
- Labels for every input/select, keyboard buttons, visible focus style, no overflow,
  reduced-motion disables animations and sets html scroll-behavior:auto. No focus()
  calls outside native dialog behavior. Avoid full-page scroll hijacking.
Deliver exactly three separate files index.html, style.css, app.js. All HTML references
must resolve to those files; all data and behavior in app.js. No other files needed.
The quality of the design will also be reviewed visually; selectors alone are not enough.'''

LESSONS = {
    'filters': 'Keep all filters in one state and apply their intersection before sorting and rendering.',
    'search': 'Trim and normalize search text; clearing controls must also reset the underlying state.',
    'gallery': 'Rebuild gallery navigation from the currently filtered and sorted list, including wraparound.',
    'cart': 'Represent single-stock products by unique ID; derive count and total from that collection on every change.',
    'receipt': 'Invalidate the checkout summary whenever the cart changes and clearly state demo-only behavior.',
    'menu': 'Synchronize aria-expanded and visibility, including Escape and mobile breakpoints.',
    'overflow': 'Check intrinsic grid/flex widths and long text at the smallest viewport, not just desktop.',
    'motion': 'Use prefers-reduced-motion to disable movement and smooth scrolling.',
    'catalog': 'Render the supplied catalog faithfully; DOM metadata and visible content must represent the same products.',
    'runtime': 'Resolve browser exceptions before functional evaluation; the page must initialize without hidden dependencies.',
}
