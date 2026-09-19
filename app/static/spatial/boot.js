// Module/network errors must never leave the user looking at an endless loader.
import('./spatial.js?v=7').catch(() => {
  document.getElementById('scene-loading').textContent = 'Nie udało się uruchomić sceny. Odśwież stronę lub przejdź do pełnego pulpitu przez link u góry.';
  document.getElementById('sync').textContent = 'Błąd ładowania modułu 3D';
  document.getElementById('retry').onclick = () => location.reload();
  document.getElementById('owner-shortcut').onclick = () => {location.href='/os';};
});
