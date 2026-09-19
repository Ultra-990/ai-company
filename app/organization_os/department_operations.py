"""Operating charters for existing departments, not claims of autonomous execution."""
OPERATIONS = {
    'strategy': ('Wyznacza kierunek i rozstrzyga priorytety.', 'Cel właściciela, ograniczenia i stan projektów.', 'Decyzja, priorytet i plan z kryteriami odbioru.', 'Ustal zakres pierwszej usługi', 'strategy.goals'),
    'platform': ('Buduje i utrzymuje wspólne narzędzia firmy.', 'Specyfikacja funkcji lub zgłoszenie błędu.', 'Wersjonowany kod, dokumentacja i wynik kontroli.', 'Zbuduj funkcję platformy', 'platform.backend-api'),
    'ai-automation': ('Projektuje agentów i automatyzacje z kontrolą wyników.', 'Proces do usprawnienia i kryteria jakości.', 'Instrukcje, integracja i raport ewaluacji.', 'Zaprojektuj automatyzację', 'ai-automation.agents'),
    'web-platforms': ('Realizuje aplikacje i platformy produktowe.', 'Problem użytkownika i uzgodniony zakres MVP.', 'Sprawdzona wersja aplikacji i instrukcja użycia.', 'Zaplanuj aplikację MVP', 'web-platforms.saas'),
    'digital-experience': ('Projektuje strony i czytelne doświadczenia cyfrowe.', 'Brief, treści, odbiorcy i identyfikacja.', 'Projekt interfejsu, źródła strony i raport dostępności.', 'Przygotuj stronę internetową', 'digital-experience.websites'),
    'systems-rnd': ('Bada narzędzia Linux i technologie systemowe.', 'Hipoteza, ograniczenia sprzętu i cel prototypu.', 'Izolowany prototyp oraz udokumentowane wnioski.', 'Zdefiniuj prototyp systemowy', 'systems-rnd.developer-tools'),
    'client-services': ('Prowadzi klienta od ustaleń do odbioru.', 'Zlecenie, ustalenia i zmiany zakresu.', 'Uzgodniony rezultat, publikacja i historia odbioru.', 'Przygotuj realizację zlecenia', 'client-services.custom-build'),
    'quality-security': ('Sprawdza jakość, uprawnienia i dowody wykonania.', 'Konkretna wersja wyniku oraz kryteria.', 'Raport testów, ryzyka i decyzja o gotowości do odbioru.', 'Przygotuj kontrolę jakości', 'quality-security.testing'),
    'operations': ('Zapewnia środowiska, diagnostykę i odtwarzanie.', 'Wymagania działania i ryzyka infrastruktury.', 'Procedura, konfiguracja i wynik kontrolowanej próby.', 'Opracuj procedurę operacyjną', 'operations.continuity'),
    'business-marketing': ('Przekłada możliwości firmy na ofertę i relacje.', 'Sprawdzona usługa, odbiorcy i warunki współpracy.', 'Oferta, kwalifikacja zapytania i materiały sprzedażowe.', 'Przygotuj ofertę usługi', 'business-marketing.offer'),
    'finance-legal': ('Porządkuje koszty, rozliczenia i wymagania formalne.', 'Model sprzedaży, zobowiązania i dane do weryfikacji.', 'Zestawienie oraz lista decyzji właściciela i specjalisty.', 'Przygotuj plan rozliczeń', 'finance-legal.budget'),
    'knowledge-community': ('Zamienia doświadczenia w instrukcje i standardy.', 'Sprawdzony proces, decyzje i wyniki projektu.', 'Aktualna instrukcja, szablon i materiały wdrożeniowe.', 'Opracuj instrukcję procesu', 'knowledge-community.documentation'),
}


def operating_model(key):
    entry = OPERATIONS.get(key)
    if not entry:
        return None
    mission, inputs, outputs, action, target = entry
    return {'mission': mission, 'inputs': inputs, 'outputs': outputs,
            'action_title': action, 'target_key': target,
            'execution': 'planned_human_review',
            'note': 'Można utworzyć zlecenie i przypisać role. Nie oznacza to działającego autonomicznie działu.'}


# The same four-stage review lifecycle, with actual department-specific results.
# These are deterministic planning templates, not generated work or agent runs.
DELIVERABLE_STAGES = {
    'strategy': ('Opracowanie decyzji i planu', 'strategy-planner'),
    'platform': ('Budowa funkcji platformy', 'platform-engineer'),
    'ai-automation': ('Projekt automatyzacji i ewaluacji', 'automation-engineer'),
    'web-platforms': ('Budowa wersji aplikacji', 'application-engineer'),
    'digital-experience': ('Projekt i wykonanie strony', 'web-developer'),
    'systems-rnd': ('Prototyp i raport badawczy', 'systems-researcher'),
    'client-services': ('Plan obsługi i przekazania zlecenia', 'client-coordinator'),
    'quality-security': ('Przeprowadzenie kontroli i raport', 'quality-auditor'),
    'operations': ('Procedura i plan próby odtworzenia', 'operations-engineer'),
    'business-marketing': ('Przygotowanie oferty i materiałów', 'offer-specialist'),
    'finance-legal': ('Zestawienie kosztów i wymagań', 'finance-analyst'),
    'knowledge-community': ('Opracowanie instrukcji i szablonu', 'knowledge-editor'),
}


def workflow_for(key):
    if key not in OPERATIONS:
        return None
    _, inputs, outputs, _, _ = OPERATIONS[key]
    name, role = DELIVERABLE_STAGES[key]
    return (
        ('Zakres i dane wejściowe', 'requirements-analyst',
         f'Zweryfikowane dane wejściowe: {inputs} Zakres, wyłączenia i kryteria zatwierdzone przez właściciela.'),
        (name, role, f'Wersjonowany rezultat: {outputs} Każda deklaracja ma źródło lub dowód; braki są wskazane.'),
        ('Niezależna weryfikacja wyniku', 'quality-reviewer',
         'Kontroler porównał konkretną wersję z kryteriami, sprawdził dowody i opisał ryzyka. Nie przypisuje niewykonanych testów.'),
        ('Odbiór i przekazanie', 'delivery-manager',
         'Właściciel odebrał konkretną wersję. Instrukcja, ograniczenia i zasady przekazania są zapisane; publikacja wymaga osobnej decyzji.'),
    )
