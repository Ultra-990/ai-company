"""Read-only, server-rendered manuals; client help never receives owner topics."""
from html import escape
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.help_content import OWNER,CLIENT,UPDATED

owner_router=APIRouter(include_in_schema=False)
client_router=APIRouter(include_in_schema=False)
HEADERS={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff',
         'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"}


def render(audience):
    owner=audience=='owner';topics=OWNER if owner else CLIENT
    home='/os' if owner else '/client';label='właściciela' if owner else 'klienta'
    context='Zlecenia, Qwen, testy, poprawki i przekazanie.' if owner else 'Dostęp do projektu, etapy, materiały i Twoje uwagi.'
    search_assets='<link rel="stylesheet" href="/static/organization-os/navigation-search.css?v=1"><script src="/static/organization-os/navigation-search.js?v=1" defer></script>' if owner else ''
    articles=[];links=[]
    for index,t in enumerate(topics):
        id_=escape(t['id'],quote=True)
        steps=''.join(f'<li>{escape(s)}</li>' for s in t['steps'])
        links.append(f'<li><a href="#{id_}">{escape(t["title"])}</a></li>')
        articles.append(f'''<article class="help-article" data-keywords="{escape(t['keywords'],quote=True)}">
<details id="{id_}" {'open' if index==0 else ''}><summary>{escape(t['title'])}</summary>
<div class="help-answer"><p class="help-summary">{escape(t['summary'])}</p><ol>{steps}</ol>
<p class="help-warning"><strong>Ważne:</strong> {escape(t['warning'])}</p>
<div class="help-actions"><a href="{escape(t['href'],quote=True)}">{escape(t['action'])} →</a>
<a href="#{id_}" aria-label="Stały odnośnik: {escape(t['title'],quote=True)}">Odnośnik do instrukcji</a></div></div></details></article>''')
    return HTMLResponse(f'''<!doctype html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Pomoc dla {label} · AI Company</title>
<script src="/static/organization-os/theme.js?v=4"></script><link rel="stylesheet" href="/static/organization-os/theme.css?v=2">
<link rel="stylesheet" href="/static/organization-os/help.css?v=1"><script src="/static/organization-os/help.js?v=1" defer></script>{search_assets}</head>
<body><a class="help-skip" href="#help-topics">Przejdź do instrukcji</a>
<nav class="app-navigation" aria-label="Nawigacja pomocy"><a href="{home}" data-back>← Wstecz</a><a href="{home}" data-home>{'Pulpit' if owner else 'Panel klienta'}</a><a href="#start">Pierwsze kroki</a></nav>
<main class="help-shell"><header><p class="help-eyebrow">AI COMPANY / CENTRUM POMOCY</p><h1>Pomoc dla {label}.</h1><p class="help-lead">{context}</p><p>Instrukcje działających funkcji · aktualizacja {UPDATED}.</p></header>
<section class="help-search" aria-label="Wyszukiwanie instrukcji"><label for="help-search">Czego potrzebujesz?</label>
<input id="help-search" type="search" maxlength="200" placeholder="Np. kod dostępu, poprawki, materiały" autocomplete="off">
<div class="help-actions"><button id="help-clear" type="button">Wyczyść wyszukiwanie</button><button id="help-print" type="button">Drukuj instrukcje / zapisz PDF</button></div>
<p id="help-count" role="status" aria-live="polite">Dostępne instrukcje: {len(topics)}.</p><p class="help-privacy">Wyszukiwanie działa tylko w tej stronie. Nie wysyła zapytań ani nie wymaga kodu dostępu. Nie wpisuj tu sekretów.</p>
<noscript>Wyszukiwanie wymaga JavaScript, ale wszystkie instrukcje i spis treści działają bez niego. Możesz też użyć wyszukiwania przeglądarki.</noscript></section>
<div class="help-layout"><aside><nav aria-label="Spis treści pomocy"><h2>Przejdź do tematu</h2><ul>{''.join(links)}</ul></nav></aside>
<section id="help-topics" aria-label="Instrukcje" tabindex="-1">{''.join(articles)}<p id="help-empty" hidden>Nie znaleziono tematu. Użyj krótszego hasła albo wyczyść wyszukiwanie. To nie jest rozmowa z agentem.</p></section></div>
<footer><p>Ta pomoc opisuje obecną wersję platformy. Funkcje planowane nie są przedstawiane jako dostępne.</p><a href="{home}">← Wróć do {'pulpitu' if owner else 'projektu'}</a></footer></main></body></html>''',headers=HEADERS)


@owner_router.get('/os/help')
def owner_help():return render('owner')


@client_router.get('/client/help')
def client_help():return render('client')
