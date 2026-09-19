/* Synthetic briefs, not offers, generated apps, or evidence of readiness. */
(() => {
  'use strict';
  const notes = 'Przykład ćwiczeniowy, nie przyjęte zlecenie klienta. Bez kont, bazy danych, zewnętrznych API, płatności i hostingu. Uruchomienie modeli oraz testów wykonawczych dopiero przy dostępnych zasobach, poza wynajmem Vast.ai.';
  const common = ' Mała lokalna aplikacja Python stdlib z HTML/CSS/JS, obsługa bezstanowego GET. Bez zależności i zasobów z internetu. README opisuje uruchomienie serwera, adres w przeglądarce i testy; otwarcie przez file:// pokazuje wyjaśnienie.';
  const examples = [
    {id:'hours', label:'Godziny × stawka', title:'Ćwiczenie: kalkulator godzin i stawki',
      job_text:'Zbuduj kalkulator iloczynu godzin i stawki. Dwa pola liczbowe, przycisk Oblicz i wynik z dwoma miejscami po przecinku. Przyjmuj liczby od 0 do 10000, maksymalnie dwa miejsca dziesiętne, separator kropka lub przecinek. Puste, nieliczbowe, ujemne i zbyt duże wartości dają czytelny błąd zamiast wyniku. Zaokrąglanie dziesiętne HALF_UP. Bez podatków, faktur ani rozliczania płatności.'+common,
      criteria:['8 godzin × 322 daje 2576.00.', '1,5 godziny × 20 daje 30.00; zero godzin daje 0.00.', '0.01 × 0.50 daje 0.01 (HALF_UP).', 'Puste pole, abc, -1, 10001 oraz 1.234 są odrzucane; wcześniejszy wynik znika.', 'Po uruchomieniu serwera formularz działa na telefonie i desktopie; file:// pokazuje instrukcję.']},
    {id:'length', label:'Przelicznik długości', title:'Ćwiczenie: przelicznik metrów i centymetrów',
      job_text:'Zbuduj przelicznik długości: wybór metry → centymetry lub centymetry → metry, pole wartości, przycisk Przelicz. Mnożnik 100 lub dzielnik 100. Przyjmuj liczby od 0 do 10000, do dwóch miejsc dziesiętnych, z kropką albo przecinkiem. Wynik z jednostką, do czterech miejsc dziesiętnych, bez zbędnych zer. Błędne dane czyszczą poprzedni wynik i pokazują komunikat.'+common,
      criteria:['1.25 m daje 125 cm.', '250 cm daje 2.5 m; 0.01 cm daje 0.0001 m.', '1,5 m daje 150 cm; 0 m daje 0 cm.', 'Puste pole, abc, -1, 10001 i 1.234 są odrzucane.', 'Zmiana kierunku przeliczenia daje prawidłowy wynik i jednostkę; file:// pokazuje instrukcję.']},
    {id:'words', label:'Licznik słów', title:'Ćwiczenie: licznik słów w tekście',
      job_text:'Zbuduj lokalny licznik słów: pole tekstowe do 2000 znaków, przycisk Policz i przycisk Wyczyść. Słowo to niepusty fragment oddzielony spacją, tabulatorem albo końcem wiersza; interpunkcja wewnątrz fragmentu nie rozdziela słów. Pusty tekst daje zero. Tekst pozostaje wyłącznie w pamięci bieżącej strony: liczenie w JavaScript, bez wysyłania tekstu w GET/POST, bez zapisu i bez analityki. Serwer dostarcza tylko stronę i /health. Nie interpretuj tekstu jako HTML.'+common,
      criteria:['Ala ma kota daje 3 słowa.', 'Dwie spacje między Ala i ma, tabulator i nowy wiersz nie dodają pustych słów.', 'Pusty tekst lub same spacje daje 0; kot,pies daje 1.', 'Wyczyść usuwa tekst i zeruje wynik; liczenie nie wysyła tekstu do serwera ani go nie zapisuje.', 'Tekst <img src=x onerror=alert(1)> nie wykonuje HTML/JS; file:// pokazuje instrukcję.']},
  ].map(example => Object.freeze({...example, criteria:Object.freeze(example.criteria), notes, source_url:''}));
  function mount(container, choose) {
    for (const example of examples) {
      const button = document.createElement('button');
      button.type = 'button'; button.textContent = example.label;
      button.addEventListener('click', () => choose(example));
      container.append(button);
    }
  }
  const api = Object.freeze({examples:Object.freeze(examples), mount});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.UpworkStarters = api;
})();
