"""Curated inventory attached to existing department keys; not another progress tree.

File presence is evidence of an artifact, NOT completion, test success or
operational readiness. No scores are generated from this inventory.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOUNDATIONS = {
    'strategy': (
        ['app/services/next_move.py', 'docs/organization-os/DELIVERY_SPRINT.md'],
        'Przypisz historyczne prace do gałęzi i ustal zakres pierwszej usługi.',
        ['Jedna aktywna usługa ma zakres i kryteria odbioru.', 'Prace historyczne mają właściciela i dowód.', 'Priorytety oraz blokady są przeglądane.']),
    'platform': (
        ['app/api/work_orders.py', 'app/api/organization_os.py', 'app/services/workspace_packages.py'],
        'Połącz istniejące API, delegacje i paczki w jeden odebrany przepływ zlecenia.',
        ['Zlecenie tworzy projekt z zadaniami.', 'Wersja wyniku przechodzi kontrolę i odbiór.', 'Błędy nie gubią danych ani nie powielają wykonania.']),
    'ai-automation': (
        ['app/services/agent_teams.py', 'app/services/agent_packets.py', 'app/services/local_model_queue.py'],
        'Po zwolnieniu zasobów przetestuj jeden rzeczywisty przebieg Qwen z limitem obciążenia.',
        ['Model otrzymuje ograniczony zakres i aktualny kontekst.', 'Wynik ma pochodzenie i wymaga odbioru.', 'Limity i przerwanie są sprawdzone; symulacja nie udaje inferencji.']),
    'web-platforms': (
        ['app/api/client_portal.py', 'app/api/client_feedback.py'],
        'Zdefiniuj jedną platformę MVP i odróżnij jej brakujące funkcje od istniejących modułów wewnętrznych.',
        ['MVP ma użytkowników i kryteria odbioru.', 'Konta i izolacja danych są sprawdzone.', 'Przepływ użytkownika przechodzi test integracyjny.']),
    'digital-experience': (
        ['app/static/spatial/spatial.js', 'app/static/organization-os/client.js', 'scripts/check_work_browser.py'],
        'Odbierz wspólną nawigację i dostępność pulpitu, Spatial oraz panelu klienta.',
        ['Widoki mają spójną nawigację i wygląd.', 'Klawiatura i telefon obsługują najważniejsze działania.', 'Pomiar wydajności nie narusza wynajmu.']),
    'systems-rnd': (
        ['docs/organization-os/STORAGE.md'],
        'Określ zakres pierwszego prototypu systemowego; obecny panel webowy nie jest własnym systemem operacyjnym.',
        ['Wybrano konkretną zdolność systemową.', 'Eksperyment ma izolowane środowisko i limit zasobów.', 'Prototyp ma powtarzalną instrukcję uruchomienia.']),
    'client-services': (
        ['app/api/client_portal.py', 'app/api/client_feedback.py', 'docs/organization-os/WORKBENCH.md'],
        'Przeprowadź demonstracyjne zlecenie od ustaleń do publikacji i odpowiedzi klienta.',
        ['Zakres i zmiany są potwierdzane.', 'Klient widzi wyłącznie swoją publikację.', 'Wynik, poprawki i przekazanie mają historię.']),
    'quality-security': (
        ['tests/test_api_authorization.py', 'tests/test_result_acceptance.py', 'app/services/package_checks.py'],
        'Ustal bramkę wydania pierwszej usługi i powiąż aktualne raporty testów z konkretną wersją.',
        ['Zmiana ma testy i wynik ich wykonania.', 'Uprawnienia oraz izolacja klienta są sprawdzone.', 'Odbiór wskazuje wersję i dowody; plik testu nie oznacza zaliczenia.']),
    'operations': (
        ['docs/organization-os/EXECUTION.md', 'docs/organization-os/STORAGE.md', 'app/services/audit.py'],
        'Przygotuj i sprawdź odtwarzanie izolowanej kopii, bez ingerencji w usługi wynajmujących.',
        ['Konfiguracja i sekrety mają bezpieczny obieg.', 'Odtworzenie kopii ma udokumentowaną próbę.', 'Wydanie i awaria mają procedurę oraz odpowiedzialność.']),
    'business-marketing': (
        ['docs/organization-os/DELIVERY_SPRINT.md'],
        'Przygotuj jedną konkretną ofertę oraz uczciwy przykład rezultatu do portfolio.',
        ['Oferta opisuje rezultat, zakres i wyłączenia.', 'Portfolio zawiera prawdziwy, sprawdzony przykład.', 'Ogłoszenie przechodzi kwalifikację przed ofertą.']),
    'finance-legal': (
        ['docs/organization-os/CLIENT_ACCOUNTS_PLAN.md'],
        'Ustal model sprzedaży i odpowiedzialność za rozliczenia przed podłączeniem płatności.',
        ['Właściciel zatwierdził model sprzedaży.', 'Wybrano sposób rozliczeń i kontroli kosztów.', 'Wymagania formalne i zakres danych są zweryfikowane.']),
    'knowledge-community': (
        ['docs/WORK_LOG.md', 'docs/organization-os/AGENT_HANDOFF.md', 'docs/organization-os/CLIENT_PORTAL.md'],
        'Połącz instrukcje obsługi w ścieżkę od pierwszego logowania do odbioru zlecenia.',
        ['Nowa osoba znajduje instrukcję pierwszego zlecenia.', 'Dokumentacja wskazuje działające funkcje i ograniczenia.', 'Zmiany i decyzje mają aktualny dziennik.']),
}


def foundation_for(key):
    if key not in FOUNDATIONS:
        return None
    paths, next_step, criteria = FOUNDATIONS[key]
    return {'source': 'curated_repository_inventory', 'review_required': True,
            'note': 'Materiały istnieją w repozytorium. Nie potwierdza to gotowości działu ani zaliczenia testów.',
            'artifacts': [{'reference': path, 'present': (ROOT / path).is_file()} for path in paths],
            'next_step': next_step, 'completion_criteria': criteria}
