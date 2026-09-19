/* Local navigation only: no project data, API calls, credentials or telemetry. */
(() => {
  'use strict';
  const pages = [
    {title: 'Grafika projektowa · ComfyUI', href: '/os/media', description: 'Generuj lokalne obrazy do zadania, sprawdź i odbierz wynik.', keywords: 'grafika obrazy zdjęcia comfyui z-image generator multimedia'},
    {title: 'Agenci działów', href: '/os/work?teams=1', description: 'Specjalizacje kierowników i wykonawców, zadania i rzeczywiste stany Qwen.', keywords: 'agenci agent kierownik mrówki zespół dział'},
    {title: 'Zlecenia Upwork', href: '/os/upwork', description: 'Wklej ogłoszenie, oceń zakres z Qwenem i przejdź do wykonania.', keywords: 'upwork zlecenie kwalifikacja zakres zarabianie'},
    {title: 'Panel klienta', href: '/client', description: 'Wejście klienta kodem otrzymanym od wykonawcy.', keywords: 'klient klijenta klijenci logowanie workflow'},
    {title: 'Podgląd panelu klienta dla właściciela', href: '/os/client-preview', description: 'Zobacz układ i opublikowany projekt jako właściciel.', keywords: 'klient klijenta przykład demo'},
    {title: 'Publikacje i dostęp klienta', href: '/os/publishing', description: 'Udostępnij etapy i materiały, utwórz kod dostępu.', keywords: 'klient klijenta token kod publikacja'},
    {title: 'Historia projektów i klientów', href: '/os/clients', description: 'Publikowane wersje, aktywność i zgłoszone uwagi.', keywords: 'klient klijenta historia poprawki'},
    {title: 'Centrum realizacji', href: '/os/work', description: 'Zlecenia, zadania, kierownicy, agenci i generowanie plików Qwen.', keywords: 'upwork projekt brain mrówki model aplikacja nowe zlecenie'},
    {title: 'Budowa i testy', href: '/os/build', description: 'Podgląd aplikacji, testy w izolacji i automatyczne naprawy.', keywords: 'qwen kod pliki kontener kalkulator wydanie zip'},
    {title: 'Odbiór wyników', href: '/os/review', description: 'Sprawdź i zaakceptuj lub odrzuć konkretny wynik zadania.', keywords: 'zatwierdzenie akceptacja wydanie wstrzymane'},
    {title: 'Działy i kompetencje', href: '/os#departments', description: 'Struktura organizacji, odpowiedzialności i zdolności.', keywords: 'dział kierownik agenci struktura'},
    {title: 'Decyzje i powiadomienia', href: '/os#decisions', description: 'Sprawy wymagające uwagi właściciela.', keywords: 'alerty blokady ryzyko dzwonek'},
    {title: 'Pulpit właściciela', href: '/os', description: 'Centrum dowodzenia i stan organizacji.', keywords: 'home główny start'},
    {title: 'Spatial', href: '/os/spatial', description: 'Przestrzenny widok firmy.', keywords: 'spatial spartial 3d kula brain'},
    {title: 'Pomoc dla właściciela', href: '/os/help', description: 'Instrukcje uruchamiania, testów i przekazania.', keywords: 'instrukcja dokumentacja pomoc token'},
    {title: 'Pomoc dla klienta', href: '/client/help', description: 'Kod dostępu, workflow, materiały i odbiory.', keywords: 'klient klijenta instrukcja hasło'},
  ];
  const nav = document.querySelector('.app-navigation');
  if (!nav || document.getElementById('site-search')) return;
  const make = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const box = make('div', '', 'site-search');
  box.setAttribute('role', 'search');
  box.setAttribute('aria-label', 'Wyszukiwarka stron i funkcji');
  const label = make('label', 'Znajdź stronę lub funkcję'); label.htmlFor = 'site-search';
  const input = make('input'); input.id = 'site-search'; input.type = 'search';
  input.placeholder = 'Np. panel klienta, testy, agenci…'; input.maxLength = 120;
  input.autocomplete = 'off'; input.spellcheck = false;
  input.setAttribute('aria-controls', 'site-search-results');
  input.setAttribute('aria-expanded', 'false');
  const panel = make('section', '', 'site-search-panel'); panel.id = 'site-search-results'; panel.hidden = true;
  panel.setAttribute('aria-label', 'Wyniki wyszukiwania stron');
  const count = make('p'); count.setAttribute('role', 'status'); count.setAttribute('aria-live', 'polite');
  const list = make('ul');
  const note = make('p', 'Szuka stron i funkcji, nie danych projektów. Zapytania nie są wysyłane. Escape: zamknij.', 'site-search-note');
  panel.append(count, list, note); box.append(label, input, panel); nav.prepend(box);
  nav.classList.add('has-site-search');
  const normalize = s => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l');
  function close() { panel.hidden = true; input.setAttribute('aria-expanded', 'false'); }
  function search() {
    const terms = normalize(input.value).trim().split(/\s+/).filter(Boolean);
    const results = pages.filter(p => terms.every(t => normalize(p.title+' '+p.description+' '+p.keywords).includes(t)));
    list.replaceChildren();
    for (const page of results) {
      const li = make('li'), a = make('a'); a.href = page.href;
      a.append(make('strong', page.title), make('span', page.description));
      a.addEventListener('click', close); li.append(a); list.append(li);
    }
    count.textContent = results.length ? (terms.length ? `Znalezione strony: ${results.length}` : 'Dokąd chcesz przejść?') : 'Brak wyników. Spróbuj: klient, testy albo pomoc.';
    panel.hidden = false; input.setAttribute('aria-expanded', 'true');
  }
  input.addEventListener('focus', search); input.addEventListener('input', search);
  input.addEventListener('click', () => { if (panel.hidden) search(); });
  box.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); input.focus(); close(); return; }
    const links = [...list.querySelectorAll('a')];
    if (['ArrowDown', 'ArrowUp'].includes(e.key)) {
      e.preventDefault(); e.stopPropagation();
      if (panel.hidden) search();
      const items = [...list.querySelectorAll('a')];
      if (!items.length) return;
      const current = items.indexOf(document.activeElement);
      const next = current < 0 ? (e.key === 'ArrowDown' ? 0 : items.length-1) : (current+(e.key === 'ArrowDown' ? 1 : -1)+items.length)%items.length;
      items[next].focus();
    } else if (e.key === 'Enter' && e.target === input) {
      e.preventDefault(); if (panel.hidden) search(); else links[0]?.click();
    }
  });
  box.addEventListener('focusout', e => { if (!box.contains(e.relatedTarget)) close(); });
  document.addEventListener('pointerdown', e => { if (!box.contains(e.target)) close(); });
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k' && !e.altKey && !document.querySelector('dialog[open]')) {
      e.preventDefault(); input.focus(); input.select(); search();
    }
  });
  window.addEventListener('pagehide', () => { input.value = ''; close(); });
})();
