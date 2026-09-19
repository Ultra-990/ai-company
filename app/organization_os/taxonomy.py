"""Kanoniczna, startowa taksonomia Organization OS.

Jest to katalog zdolności firmy, a nie lista bieżących zadań. Wagi domen
sumują się do 100; wagi dzieci każdego działu również sumują się do 100.
"""

from typing import TypedDict


class TaxonomyNode(TypedDict):
    key: str
    title: str
    weight: int
    icon: str
    color: str
    children: list[tuple[str, str, int]]


ORGANIZATION_OS_DOMAINS: tuple[TaxonomyNode, ...] = (
    {
        "key": "strategy",
        "title": "Strategia i zarządzanie",
        "weight": 10,
        "icon": "compass",
        "color": "#0EA5E9",
        "children": [
            ("goals", "Cele, wizja i model działania", 20),
            ("portfolio", "Portfolio produktów i usług", 20),
            ("roles", "Role, odpowiedzialności i uprawnienia", 15),
            ("priorities", "Priorytety, decyzje i ryzyka", 25),
            ("reporting", "Raportowanie zarządcze", 20),
        ],
    },
    {
        "key": "platform",
        "title": "Platforma technologiczna wspólna",
        "weight": 15,
        "icon": "code-2",
        "color": "#3B82F6",
        "children": [
            ("architecture", "Architektura referencyjna", 15),
            ("backend-api", "Backend i API", 20),
            ("data-identity", "Dane, tożsamość i uprawnienia", 15),
            ("frontend", "Frontend i komponenty interfejsu", 15),
            ("integrations", "Integracje i automatyzacje", 10),
            ("delivery", "CI/CD, środowiska i obserwowalność", 15),
            ("organization-os", "Wewnętrzny system Organization OS", 10),
        ],
    },
    {
        "key": "ai-automation",
        "title": "AI i automatyzacja",
        "weight": 10,
        "icon": "sparkles",
        "color": "#8B5CF6",
        "children": [
            ("generators", "Generatory treści i multimediów", 15),
            ("agents", "Agenci i przepływy wieloagentowe", 20),
            ("rag", "Wiedza, RAG i wyszukiwanie", 15),
            ("recommendations", "Analiza i rekomendacje", 15),
            ("evaluation", "Ewaluacja jakości i bezpieczeństwo AI", 20),
            ("costs", "Koszty modeli i interfejsy AI", 15),
        ],
    },
    {
        "key": "web-platforms",
        "title": "Aplikacje i platformy webowe",
        "weight": 10,
        "icon": "blocks",
        "color": "#6366F1",
        "children": [
            ("saas", "Aplikacje SaaS i panele administracyjne", 20),
            ("business", "CRM, ERP i systemy biznesowe", 15),
            ("marketplaces", "Marketplace i platformy branżowe", 15),
            ("content", "Portale informacyjne i treściowe", 15),
            ("social", "Platformy społecznościowe", 20),
            ("verticals", "Platformy edukacyjne, rezerwacyjne i inne", 15),
        ],
    },
    {
        "key": "digital-experience",
        "title": "Strony, marka i doświadczenie cyfrowe",
        "weight": 7,
        "icon": "palette",
        "color": "#EC4899",
        "children": [
            ("websites", "Strony firmowe i produktowe", 20),
            ("commerce", "Landing pages, CMS i e-commerce", 15),
            ("design", "Design system i UX/UI", 25),
            ("accessibility", "Dostępność i responsywność", 15),
            ("performance", "Wydajność, SEO i analityka", 25),
        ],
    },
    {
        "key": "systems-rnd",
        "title": "Systemy operacyjne i R&D",
        "weight": 5,
        "icon": "terminal",
        "color": "#64748B",
        "children": [
            ("linux", "Dystrybucje Linux i obrazy systemowe", 20),
            ("desktop", "Środowiska graficzne i compositor", 25),
            ("system-services", "Usługi systemowe, pakiety i aktualizacje", 20),
            ("developer-tools", "Narzędzia developerskie i kontenery", 15),
            ("compatibility", "Bezpieczeństwo i kompatybilność sprzętowa", 20),
        ],
    },
    {
        "key": "client-services",
        "title": "Usługi dla klientów",
        "weight": 12,
        "icon": "handshake",
        "color": "#06B6D4",
        "children": [
            ("upwork", "Upwork i inne kanały zleceń", 15),
            ("custom-build", "Aplikacje, strony i AI na zamówienie", 25),
            ("integration", "Integracje API i automatyzacje", 15),
            ("quality", "Testy, audyty i naprawy", 15),
            ("delivery", "Realizacja, odbiór i utrzymanie", 20),
            ("support", "Wsparcie techniczne klienta", 10),
        ],
    },
    {
        "key": "quality-security",
        "title": "Jakość, bezpieczeństwo i niezawodność",
        "weight": 8,
        "icon": "shield-check",
        "color": "#10B981",
        "children": [
            ("standards", "Standardy architektury i Definition of Done", 20),
            ("testing", "Testy jednostkowe, integracyjne i E2E", 25),
            ("review", "Code review i odbiór funkcjonalny", 15),
            ("security", "Testy bezpieczeństwa i ochrona danych", 20),
            ("incidents", "Błędy, regresje i incydenty", 20),
        ],
    },
    {
        "key": "operations",
        "title": "Operacje i infrastruktura",
        "weight": 7,
        "icon": "server",
        "color": "#38BDF8",
        "children": [
            ("environments", "Środowiska lokalne, testowe i produkcyjne", 20),
            ("configuration", "Konfiguracja, domeny i sekrety", 20),
            ("deployment", "Wdrożenia, wersjonowanie i rollback", 20),
            ("observability", "Monitoring, logi i alerty", 20),
            ("continuity", "Backup, odtwarzanie i ciągłość działania", 20),
        ],
    },
    {
        "key": "business-marketing",
        "title": "Biznes, sprzedaż i marketing",
        "weight": 7,
        "icon": "chart-no-axes-combined",
        "color": "#F97316",
        "children": [
            ("offer", "Oferta produktów i usług", 20),
            ("portfolio", "Portfolio i studia przypadków", 15),
            ("sales", "Leady, CRM, wycena i negocjacje", 25),
            ("brand", "Marka, komunikacja i marketing treści", 20),
            ("market", "Partnerstwa, rynek i konkurencja", 20),
        ],
    },
    {
        "key": "finance-legal",
        "title": "Finanse, prawo i zgodność",
        "weight": 4,
        "icon": "landmark",
        "color": "#14B8A6",
        "children": [
            ("budget", "Budżet, prognozy i rentowność", 25),
            ("billing", "Przychody, koszty i rozliczenia", 20),
            ("taxes", "Podatki i księgowość", 15),
            ("contracts", "Umowy, licencje i własność intelektualna", 25),
            ("privacy", "Prywatność i zgodność regulacyjna", 15),
        ],
    },
    {
        "key": "knowledge-community",
        "title": "Wiedza, ludzie i społeczność",
        "weight": 5,
        "icon": "users",
        "color": "#65F3BF",
        "children": [
            ("documentation", "Dokumentacja i baza wiedzy", 25),
            ("standards", "Standardy, szablony i procedury", 20),
            ("skills", "Rozwój kompetencji i szkolenia", 20),
            ("collaboration", "Rekrutacja, współpraca i onboarding", 20),
            ("community", "Open source i społeczność twórców", 15),
        ],
    },
)


# Tymczasowy układ utworzony przed zatwierdzeniem docelowej taksonomii.
# Wpisy są używane wyłącznie do bezpiecznej, jednokrotnej migracji danych.
LEGACY_DOMAIN_KEYS = {
    "strategy": "strategy",
    "engineering": "platform",
    "research": "ai-automation",
    "product": "web-platforms",
    "customer-success": "digital-experience",
    "infrastructure": "systems-rnd",
    "sales": "client-services",
    "legal": "quality-security",
    "operations": "operations",
    "marketing": "business-marketing",
    "finance": "finance-legal",
    "people": "knowledge-community",
}
