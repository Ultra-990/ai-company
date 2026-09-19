"""Original, public synthetic client brief. Evaluation only, never training data."""

CASE_ID = 'studio-website.v1'
BRIEF = '''Create an original Polish service studio website for fictional FORMA studio.
This is a synthetic Upwork-style delivery trial, not a real client or testimonial.
Editorial visual direction: generous spacing, large typography, warm white/ink
light theme, dark ink theme with a lime accent. Compose a striking typographic
hero and original CSS geometric artwork, numbered service cards, process, quote,
FAQ and footer. No external fonts, images, libraries, fake awards or client claims.
Use semantic header/nav/main/section/footer, one h1, real anchor navigation,
responsive layout without horizontal overflow at 390px and readable at 1440px.
Every action must work. Do not add contact submission, accounts or payments.
Quote is an indicative local calculation, not an order, payment or message sent.

Functional contract:
- A skip link href=#main, main id=main with tabindex=-1. Navigation #site-nav
  has links to #services, #quote and #faq. Button #menu-toggle controls site-nav,
  aria-controls=site-nav, aria-expanded=false initially. Hide menu on mobile
  until activated; toggle on click, Escape closes and returns focus to the button.
- Button #theme-toggle switches document.documentElement.dataset.theme between
  light and dark, changing actual background/text colors, without storage.
  Start light. Keyboard focus must remain visible; respect prefers-reduced-motion.
- Native details id=faq-delivery with summary and a useful Polish answer.
- Quote fields: labelled select #service values landing/site, labelled input
  #pages default 1, labelled checkbox #rush, button #calculate; output #result
  with aria-live=polite. Show errors in #result, using textContent, never innerHTML.
- modules.logic.estimate(service, pages, rush=False) returns a numeric total.
  Base landing=1200, site=2800 PLN, extra pages=(pages-1)*250.
  rush=True multiplies the whole amount by 1.25. pages accepts int or an integer
  digit string (1..20), no booleans/floats; rush must be bool, service exactly
  landing/site. All invalid input raises ValueError.
- GET /api/estimate?service=landing&pages=3&rush=1 returns {"total":2125}.
  rush query must be 0 or 1 and all three params required; invalid -> HTTP400
  JSON {"error":"..."}. Use the actual form values; handle HTTP/network errors.
  Successful result text exactly: Wycena: NUMBER PLN (integer if total integral).
  For empty/invalid pages UI says: Podaj liczbę stron od 1 do 20.
- README explains startup, tests, demo-only quote, no sending, no deployment,
  original CSS artwork and no external assets. Don't claim tests ran.
Keep HTML below 11000 UTF-8 bytes; place CSS/JS in style.css/app.js if needed.
Fit the full valid JSON response within 4096 output tokens, prefer compact code.
'''

# Independent assertions fixed before generation. Not sent to the model.
ACCEPTANCE = '''import unittest
from modules.logic import estimate
class ClientAcceptance(unittest.TestCase):
 def test_prices(self):
  for s,p,r,w in [('landing',1,False,1200),('site',1,False,2800),
                 ('landing','3',True,2125),('site',20,True,9437.5),
                 ('site',2,False,3050)]:
   with self.subTest(s=s,p=p,r=r):self.assertEqual(estimate(s,p,r),w)
 def test_invalid(self):
  for s,p,r in [('other',1,False),('landing',0,False),('site',21,False),
                ('site',True,False),('site',1.0,False),('site','2.5',False),
                ('site','',False),('site',None,False),('site',1,'1'),
                ('site',1,1),('site',1,None)]:
   with self.subTest(s=s,p=p,r=r):
    with self.assertRaises(ValueError):estimate(s,p,r)
'''

PROBES = [('/', 200, None),
          ('/api/estimate?service=landing&pages=3&rush=1', 200, 2125),
          ('/api/estimate?service=site&pages=20&rush=1', 200, 9437.5),
          ('/api/estimate?service=site&pages=1&rush=0', 200, 2800),
          ('/api/estimate?service=site&pages=0&rush=0', 400, None),
          ('/api/estimate?service=site&pages=2.5&rush=0', 400, None),
          ('/api/estimate?service=site&pages=1', 400, None),
          ('/api/estimate?service=site&pages=1&rush=yes', 400, None)]

BROWSER_CASES = [
    dict(inputs={'#service':'landing', '#pages':'3'}, checks={'#rush':True},
         result='Wycena: 2125 PLN', path=PROBES[1][0]),
    dict(inputs={'#service':'site', '#pages':'20'}, checks={'#rush':True},
         result='Wycena: 9437.5 PLN', path=PROBES[2][0]),
    dict(inputs={'#service':'site', '#pages':'1'}, checks={'#rush':False},
         result='Wycena: 2800 PLN', path=PROBES[3][0]),
    dict(inputs={'#pages':''}, result='Podaj liczbę stron od 1 do 20.', path=None),
]
