# ComfyUI — lokalne multimedia bez płatnego API

## Grafika projektowa: integracja z zadaniami (2026-09-13)

Panel `/os/media`: wspólna sesja właściciela, opis i seed, historia,
podgląd PNG, raport, pobieranie i odbiór obrazu. W Centrum realizacji każde
zadanie ma link „Grafika do tego zadania”; wyszukiwarka znajduje „Grafika
projektowa”. Centrum pomocy zawiera instrukcję „Jak wygenerować grafikę”.
To pierwszy profil grafiki: jedna generacja Z-Image Turbo 768×512/8 kroków.
Nie obejmuje wideo, muzyki ani automatycznego wstawiania grafiki do źródeł aplikacji.

Właściciel wybiera istniejące zatwierdzone zadanie w statusie pending/in_progress.
POST `/api/tasks/{id}/images` przyjmuje request_id UUID, prompt do2000 znaków,
seed0..4294967295, confirm:true. Serwer nie przyjmuje adresów, ścieżek,
dowolnych grafów, custom nodes ani poleceń. Używa tylko127.0.0.1:8188.
Kontrola przed wysłaniem sprawdza wersję0.35.0, trzy wymagane modele,
pustą kolejkę ComfyUI i brak załadowanych modeli Ollama. Nie uruchamia usług,
nie pobiera wag i nie zwalnia samodzielnie pamięci modeli.

Tabela media_generations przechowuje UUID, stan, kontekst, profil, hash grafu
i powiązanie z zadaniem/projektem/planem. Rezerwacja SQLite BEGIN IMMEDIATE
koordynuje generowanie z uruchomieniami local_inference. Nie jest globalnym
schedulerem: nie kontroluje ręcznych procesów GPU, a cache ComfyUI może
pozostać w VRAM po generacji. Przed przejściem do innego dużego modelu sprawdź
zasoby i zwolnij nieużywane modele; nie uruchamiaj treningu równolegle.

UUID ComfyUI jest zapisywany przed wysłaniem. Ponowienie tego samego request_id
odczytuje istniejący wpis. Awaria transportu zostawia uncertain i blokadę slotu;
odświeżenie pobiera historię tego samego UUID, nigdy nie wysyła kolejnej generacji.
POST `/{job_id}/refresh` sprawdza zgodność grafu i wynik. Brak historii nie
zwalnia slotu. Przy usuniętej historii/restarcie ComfyUI może być potrzebna
ręczna diagnostyka; automatycznego odzyskania niepewnego slotu nie zaimplementowano.
Jawna odpowiedź400 z błędem walidacji grafu kończy wpis jako failed.
HTTP ma timeout5s na operację I/O. Pięć minut w panelu to limit odświeżania,
nie gwarantowany limit pracy serwera; panel nie wywołuje globalnego interrupt.

Obraz jest sprawdzany pod względem formatu PNG, wymiarów, limitu8MiB i
niejednorodności; metadane workflow są usuwane z pliku do pobrania. Artefakt
OTHER zawiera PNG/base64, raport, parametry i sumy źródła/obrazu/grafu.
GET `/{job_id}/report` nie zwraca base64; GET `/{job_id}/download` sprawdza
integralność i zwraca PNG tylko właścicielowi. POST `/{job_id}/review` wymaga
checksumy artefaktu, accepted/rejected i uzasadnienia. Nie zmienia statusu
zadania, nie tworzy fikcyjnego TaskAttempt i nie publikuje klientowi.
Kontrola jakości artystycznej, zgodności z briefem i praw pozostaje osobnym odbiorem.

Dowód integracji: `integration-check-wh4upiem/report.json` w katalogu ComfyUI,
rzeczywisty obraz,18.402s, osobna baza/syntetyczne zadanie, status zadania
niezmieniony. Asystent obejrzał wynik; generacja zgodna z opisem kuli na postumencie.
TestUI z atrapamiAPI: `/tmp/ai-media-browser-nk3uqafw/report.json`, sesja,
pojedyncze wysłanie,podgląd,odbiór,bezpieczny tekst,tryby i responsywność390/768px.
Regresja94testy passed/3.77s. Nie wykonano projektu prawdziwego klienta.

Pierwsza próba integracyjna nie przeszła: działająca starsza instancja
ComfyUI nie miała argumentu extra-model-paths-config i nie widziała modeli.
Raport `integration-check-4uq7b6sa/report.json` zachowano. Po identyfikacji
i zgodzie zatrzymano tylko jej PID2790142 z pustą kolejką, uruchomiono
ComfyUI przez aktualny launcher i potwierdzono udaną próbę. Bez restartu hosta,
Ollamy lub Docker. Windows nadal tylko do odczytu.

Poniżej historyczne kroki instalacji i pierwszego osobnego testu generatora.

## Aktualny wynik: pierwsza lokalna generacja działa (2026-09-13)

Z-Image Turbo wygenerował obraz 768×512, 8 kroków, seed 20260913.
Użyto istniejących z_image_turbo_bf16.safetensors, qwen_3_4b.safetensors
i ae.safetensors oraz 10 wbudowanych węzłów. Bez pobierania wag i custom nodes.
Od wysłania zadania do odebrania obrazu: 22.079 s, z ładowaniem modeli;
cały test ze startem/zatrzymaniem własnego procesu: 25.856 s.
To pojedyncza próba, nie benchmark wszystkich modeli.

Dowody w `/home/marcin/ai-company-workspaces/comfyui/generation-check-lsrce_nu`:
`report.json`, `server.log`, `workflow-api.json`, `output/local-smoke_00001_.png`.
PNG SHA256: `cca1e19ed018d9e573c10fe741d0c88504e84b46840bd819d53ba2f59bfe8fe5`.
Automatycznie sprawdzono sukces API, rozmiar/format i niejednorodność obrazu.
Następnie asystent obejrzał PNG: niebieska szklana kula na jasnym postumencie,
zgodna z opisem. Pole visual_reviewed=false w surowym raporcie oznacza, że
sam skrypt nie ocenia wizualnie; raportu automatycznego nie zmieniano.

### Gotowy workflow do otwarcia

- Plik w repo: `config/comfyui-workflows/ai-company-z-image.json`.
- Kopia w ComfyUI: `ComfyUI/user/default/workflows/AI Company - Z-Image.json`.
- W otwartym ComfyUI przeciągnij ten plik JSON na płótno. Zmień opis obrazu
  w węźle Z-Image i kliknij Run. Wyniki trafią do `ComfyUI/output/AI-Company`
  na Linuksie. Stały seed pozwala odtwarzać próbę; zmień go dla nowego wariantu.
- To adaptacja zainstalowanego oficjalnego szablonu image_z_image_turbo.json.
  Parametry UI sprawdza test statyczny. Import/klikanie tej kopii w przeglądarce
  nie zostały przetestowane; realna generacja używała równoważnego grafu API.

`scripts/check_comfyui_generation.py --run`, uruchamiany Pythonem venv ComfyUI,
wykonuje jedną ograniczoną próbę na własnym porcie8189 i osobnych danych.
Kontroluje pustą kolejkę użytkownika8188 oraz brak załadowanych modeli Ollama;
kończy tylko własny proces, jeśli wykryje aktywność. To kontrola współpracy,
nie atomowa rezerwacja GPU. Timeout inferencji300s, bez automatycznych ponowień.
Windows pozostaje tylko do odczytu. Brak integracji generowania z zadaniami
firmy, kontroli licencji/pochodzenia wag, publikacji lub zmian postępu działów.
Sekcje poniżej dokumentują wcześniejsze kontrole samej instalacji.

## Aktualizacja: istniejące wagi Windows podłączone tylko do odczytu

`config/comfyui-model-paths.yaml` wskazuje istniejący magazyn
`/media/marcin/Windows/Users/kusmi/Desktop/Comfy UI/models`. Launcher przekazuje
go przez `--extra-model-paths-config`. `is_default: false`: katalogi Windows
nie zastępują domyślnych katalogów pobierania na Linuksie. Nie podłączamy
windowsowego custom_nodes ani kodu. `unet` i `diffusion_models` są widoczne
w jednej kategorii modeli dyfuzyjnych, `clip` i `text_encoders` jako enkodery.

Właściciel dopuścił ten wyjątek od pierwotnego rozdzielenia dysków. Launcher
sprawdza oczekiwaną partycję `/dev/nvme0n1p4` i opcję `ro`; przy dostępnym
magazynie na partycji zapisywalnej odmawia startu. Brak zamontowanego Windows
nie blokuje lokalnego ComfyUI, ale modele z Windows nie będą dostępne.
Nie dodano automatycznego montowania ani zmian fstab/EFI/bootloadera.
Po ponownym uruchomieniu komputera Windows może wymagać ponownego podłączenia
tylko do odczytu. Nie wymuszać zapisu na NTFS.

Sprawdzony komplet nazw (kontenery Safetensors czytelne, bez ładowania tensorów):

| Plik | Bajty | Liczba tensorów |
| --- | ---: | ---: |
| unet/flux-2-klein-base-4b-fp8.safetensors | 4089498488 | 305 |
| text_encoders/qwen_3_4b.safetensors | 8044982048 | 398 |
| vae/flux2-vae.safetensors | 336213556 | 251 |

To **Base 4B, nie Distilled**. Nie stosować automatycznie ustawień4kroków
przeznaczonych dla modelu distilled. Odczyt kontenera nie uwierzytelnia
pochodzenia/licencji ani nie dowodzi jakości lub kompletności workflow.

`check_comfyui_installation.py --run --shared-models` przeszedł: wszystkie3
nazwy są widoczne w API UNETLoader/CLIPLoader/VAELoader,0cloud nodes,pusta
kolejka, własny proces testowy zatrzymany. Raport:
`ai-company-workspaces/comfyui/install-check-8fbyrre0/report.json`.
Nie wygenerowano jeszcze obrazu; nie skopiowano ani nie pobrano wag.
10testów launchera/konfiguracji/ochrony montowania: passed/0.21s.

Nowa konfiguracja działa przy następnym starcie przez skrót. Jeśli ComfyUI
było już uruchomione, otwarcie kolejnej karty nie przeładuje konfiguracji:
potrzebny jest restart wyłącznie jego własnej usługi po zakończeniu jej pracy.
Nie zatrzymywano wcześniej działających usług ani zadań użytkownika.

Stan 2026-09-13: zainstalowano i sprawdzono start usługi, nie generowanie
modelu ani integrację z zadaniami firmy. Nie ma jeszcze przycisku ComfyUI
w centrum realizacji. Nie zwiększano statusów ani procentów działów.

## Zainstalowane

- Oddzielny katalog Linux: `/home/marcin/ai-company-workspaces/comfyui`.
- Oficjalne repozytorium `https://github.com/Comfy-Org/ComfyUI.git`, commit
  `19e1058f4c445ef74047e77a23f9ca7684c1e4b6`, ComfyUI 0.35.0.
- Własny `venv`, Python 3.12.3, PyTorch 2.14.0+cu130, frontend 1.52.7.
- Snapshot pakietów: `config/comfyui-environment.lock.txt` — wyłącznie dla
  tego środowiska; nie instalować go w `.venv` backendu ani w Qwen training.
- Nie zmieniono sterowników, Ollama, QLoRA, Dockera, usług ani dysku Windows.
- Pobranie w sandbox nie powiodło się z powodu DNS; ponowiono po zgodzie
  na sieć. Instalacja z oficjalnego źródła i PyPI/PyTorch zakończona, `pip check` OK.

## Uruchomienie dla właściciela

Na pulpicie `/home/marcin/Pulpit` jest skrót **ComfyUI** z własną ikoną.
Uruchamia `scripts/open_comfyui.py`: sprawdza działającą usługę, w razie potrzeby
startuje osobny proces w tle, czeka do90s i otwiera przeglądarkę. Ponowne
kliknięcie korzysta z działającej usługi; blokada pliku zapobiega podwójnemu
startowi. Log: `ai-company-workspaces/comfyui/desktop.log`. Zamknięcie karty
przeglądarki nie zatrzymuje usługi. Skrót nie uruchamia żadnego generowania.
Jeśli pulpit pyta o zaufanie, wybierz prawym przyciskiem **Zezwól na uruchamianie**.
GIO metadata::trusted nie jest obsługiwane w bieżącym środowisku; plik ma
uprawnienia wykonywania i przeszedł desktop-file-validate.

W nowym terminalu:

```bash
cd /home/marcin/ai-company
.venv/bin/python scripts/start_comfyui.py
```

Następnie otwórz `http://127.0.0.1:8188`. Terminal pozostaje uruchomiony;
Ctrl+C zatrzymuje tylko tę usługę. Nie zatrzymuj procesu zajmującego port
bez ustalenia, czym jest. `--check` kontroluje pliki i commit bez startu;
`--cpu` służy do diagnostyki, nie szybkiego generowania.

Launcher ustawia loopback, wyłącza płatne/API nodes, custom nodes,
automatyczne otwieranie przeglądarki i cache wyników pośrednich. Manager
nie jest włączony. HF/Transformers mają tryb offline. To NIE jest izolacja
sieciowa ani sandbox kodu: natywne węzły wykonują Python z prawami użytkownika.
Nie należy importować niezweryfikowanych workflow, udostępniać portu klientom
lub dodawać dowolnych rozszerzeń. Nie ma logowania klienta do tej usługi.
Nie wyłączono zabezpieczeń treści modeli; nie modyfikowano firewalla.

Przy przyszłych generacjach Qwen/QLoRA i ComfyUI nie powinny jednocześnie
zajmować GPU bez wspólnej kontroli zasobów. `--reserve-vram 3` nie jest
gwarantowaną izolacją i nie zastępuje kolejki. Launcher nie zatrzymuje Qwena.

## Dowód instalacji

`scripts/check_comfyui_installation.py --run` uruchamia własny proces na
127.0.0.1:8189, z oddzielnym katalogiem danych i DB ComfyUI. Sprawdza stronę,
system_stats, object_info i pustą kolejkę; w finally kończy wyłącznie ten
proces. Nie dotyka DB aplikacji ani statusów klientów.

Raport: `/home/marcin/ai-company-workspaces/comfyui/install-check-ux8bpgyj/report.json`.
Wynik: passed, CUDA RTX5090,660 węzłów,0 modułów comfy_api_nodes, pusta
kolejka, proces własny zatrzymany. Log SHA256:
`2c11c6089375e317f2a72ec6669e3b66fb23fece2b53e4bda5744798983ad4d4`.
Nie wykonano generacji, testu wszystkich660węzłów ani wizualnego odbioru w Chrome.
Log zawiera ostrzeżenie o przechowywaniu ustawień na serwerze, deprecacji
torch.jit.script i braku opcjonalnego OpenGL_accelerate; brak błędu startu.

## Modele i następny zakres

ComfyUI to silnik workflow, nie model i nie sposób bezpłatnego dostępu do
zamkniętych modeli chmurowych. Qwen pozostaje wykonawcą tekstu/kodu.
QLoRA to metoda dostrajania, nie zamiennik modelu. Pobranie wag nie usuwa
wymagań pamięciowych ani warunków licencji. Brak opłat API nie oznacza
braku kosztów energii, sprzętu i ewentualnej licencji.

Pierwszy kandydat do lokalnej grafiki: FLUX.2 Klein **4B**, wariant distilled,
nie9B. Producent deklaruje Apache2.0, ok.13GB VRAM i generowanie/edycję;
nie zmierzono jeszcze czasu ani jakości na tej instalacji. Potrzebne są
diffusion model, encoder Qwen3 4B oraz VAE; wszystkie pliki należy pobrać
z oficjalnych źródeł, przypiąć rewizje, sumy i sprawdzić licencje składników.
**Wag jeszcze nie pobrano.** Krea2Turbo/MiniMaxH3 są kandydatami późniejszych
prób po weryfikacji zasobów i licencji; nie obiecano darmowego użycia
komercyjnego wszystkich tych modeli.

Docelowy adapter (jeszcze NIE zaimplementowany):

1. Zlecenie firmy → Qwen przygotowuje opis grafiki w ograniczonym JSON.
2. Backend wstawia parametry do zatwierdzonego szablonu workflow; nie przyjmuje
   dowolnego grafu/wtyczek/URL od modelu lub klienta.
3. Wspólna kolejka GPU uruchamia jeden job, z limitami rozmiaru, kroków i czasu.
4. ComfyUI zwraca ID; backend śledzi wynik/awarię, bez ślepego ponawiania
   niepewnych żądań. Pobierane artefakty muszą mieć zweryfikowane ścieżki i rozmiary.
5. Zapis modelu, seed, workflow i checksum wyniku do konkretnego projektu,
   kontrola jakości i praw do materiałów przed przekazaniem klientowi.

Źródła sprawdzone 2026-09-13:

- https://docs.comfy.org/installation/manual_install
- https://github.com/Comfy-Org/ComfyUI
- https://huggingface.co/black-forest-labs/FLUX.2-klein-4B
- https://docs.comfy.org/tutorials/flux/flux-2-klein
- https://github.com/krea-ai/krea-2
- https://huggingface.co/MiniMaxAI/MiniMax-H3
# Dostęp do modeli po odłączeniu dysku — 19.09.2026

Brak modeli w selektorze nie musi oznaczać braku pobranych wag. Jeśli
`/media/marcin/Windows` nie jest zamontowany, skonfigurowany extra-model-paths
nie ma czego odczytać. Launcher pokazuje teraz ostrzeżenie przed ponownym
pobieraniem. Sam nie montuje dysku, nie pobiera wag i nie zmienia Windows.

Na polecenie właściciela przygotowano opcjonalną jednostkę
`media-marcin-Windows.mount`. Publiczny wzór:
`config/media-marcin-Windows.mount.example`; należy zastąpić placeholder
zweryfikowanym UUID konkretnej partycji, nigdy kopiować identyfikatora
innego komputera. Lokalna konfiguracja znajduje się poza repozytorium.

- `ro,nosuid,nodev,noexec`: wyłącznie odczyt, bez wykonywania kodu stamtąd.
- `ConditionPathExists` i `WantedBy` (nie `RequiredBy`): brak opcjonalnego
  dysku nie jest wymogiem uruchomienia systemu; ograniczony timeout 15s.
- Brak zmian `/etc/fstab`, bootloadera, Dockera, partycji i sterowników.
- Instalacja przez administratora do `/etc/systemd/system/`, następnie
  `systemctl daemon-reload` i `systemctl enable media-marcin-Windows.mount`.
- Jednostkę zweryfikowano `systemd-analyze verify`. Na tym komputerze po
  komendach właściciela potwierdzono `enabled`, `active` i istniejący mount
  `ro`. Nie restartowano hosta, więc nie jest to test rozruchu po restarcie.

Obecne ręczne podłączenie może mieć mniej opcji niż przygotowana jednostka;
nie odmontowywać używanych modeli w trakcie pracy tylko w celu ich wyrównania.
Jeśli NTFS odmówi podłączenia z powodu hibernacji/uszkodzenia, nie używać
`force`, `remove_hiberfile` ani automatycznej naprawy — osobno ustalić przyczynę.
