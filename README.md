# Ralph — CLI do czyszczenia feedu produktowego

Narzędzie do czyszczenia i walidacji feedów produktowych z e-commerce: wczytuje
"brudny" feed CSV (duplikaty SKU, błędne ceny, ujemne ilości, brakujące pola),
naprawia to, co da się bezpiecznie naprawić automatycznie, a resztę odrzuca
z podanym powodem. Wynik (`clean.parquet` + raport jakości) można dalej
przetransformować do formatu czytanego przez Google Merchant Center (TSV/XML)
i na tej podstawie uruchomić kampanię produktową w Google Ads.

Projekt zbudowany metodą Ralpha (autonomiczna pętla kodowania z Claude Code)
— metodologia i specyfikacja: `CLAUDE.md`, lista zadań: `PRD.json`, instrukcja
pracy z gotowym narzędziem: `WORKFLOW.md`.

## `feed-cleaner` — instalacja i uruchomienie

### Instalacja

```bash
uv sync   # raz na start / po zmianie zależności — nie trzeba przed każdym uruchomieniem, uv run sam dosynchronizuje
```

### Przykładowe uruchomienie

```bash
uv run feed-cleaner --input data/raw/feed.csv --output-dir output/
```

- `--input` (wymagane) — ścieżka do wejściowego pliku CSV.
- `--output-dir` (opcjonalne, domyślnie `output/`) — katalog na wyniki;
  tworzony automatycznie, jeśli nie istnieje.

Kod wyjścia `0` oznacza sukces, nawet jeśli część rekordów została odrzucona
(to normalne zachowanie danych, nie błąd CLI). Kod `2` to błąd użycia
z czytelnym komunikatem na stderr — np. nieistniejący plik wejściowy.
Znane ograniczenie: plik w kodowaniu innym niż UTF-8 nie jest obsłużony,
leci surowy `UnicodeDecodeError` i kod `1`.

### Pliki wyjściowe

- `clean.parquet` — zaakceptowane rekordy (`OK` + `REPAIRED`) po naprawach,
  w formacie Parquet. Odrzucone (`REJECTED`) w ogóle tu nie trafiają — są
  wyłącznie w raporcie jakości poniżej. Schemat kolumn jest wyprowadzony
  z `ProductRecord` (`models.py`), który waliduje też każdy wiersz przed zapisem.
- `report.json` — raport jakości danych: liczniki `row_counts`
  (total/ok/repaired/rejected) oraz osobno `repaired_reasons` i
  `rejected_reasons` (liczba wystąpień każdego powodu naprawy/odrzucenia).
  Skrót tego raportu jest też wypisywany na stdout po każdym uruchomieniu.

## Co to w ogóle jest Ralph i po co te dwa tryby

Ralph to ten sam prompt uruchamiany w kółko: agent czyta listę zadań (`PRD.json`),
sam wybiera pierwsze nieukończone, implementuje TYLKO je, uruchamia testy,
commituje, zapisuje postęp — i tak od nowa, aż lista się skończy. Sedno:
**Ty definiujesz cel (PRD), agent sam dochodzi do niego krok po kroku**,
zamiast Ciebie piszącego nowy prompt do każdej fazy.

Dwa tryby, w tej kolejności — nigdy odwrotnie:

- **HITL** (`ralph-once.sh`) — jedna iteracja na raz, na żywo, ręcznie
  odpalasz kolejną. Buduje zaufanie do promptu.
- **AFK** (`afk-ralph.sh`) — wiele iteracji bez nadzoru, z twardym limitem,
  w izolowanym sandboksie. Dopiero gdy HITL parę razy z rzędu zachował się
  zgodnie z oczekiwaniami.

Pętlę odpalasz **w osobnym terminalu**, nie w tej sesji planistycznej Claude
Code — patrz "Kto co robi" na końcu tego pliku.

## Tryb HITL (Human In The Loop) — `ralph-once.sh`

### Ściąga — same komendy

```bash
# --- w ZWYKŁYM TERMINALU (host) ---
./ralph-once.sh                                             # WCHODZISZ w interaktywną sesję Claude (skrypt to jedna komenda `claude ...`) — Ralph robi jedno zadanie z PRD.json
# ...poczekaj aż sesja odpowie i skończy...

# --- jesteś W SESJI CLAUDE — zadanie skończone, sesja NIE zamyka się sama: ---
/exit                                                        # albo Ctrl+D — WYJDŹ z powrotem do zwykłego shella

# --- z powrotem w ZWYKŁYM TERMINALU (host) ---
git show --stat HEAD                                        # co zmienił ostatni commit
cat progress.txt                                             # notatka Ralpha o tej iteracji
uv run pytest && uv run mypy src && uv run ruff check .     # niezależna weryfikacja, nie ufaj samemu commitowi
./ralph-once.sh                                              # jeśli OK — kolejna iteracja (znów WCHODZISZ w sesję)
```

### Co sprawdzić po każdej iteracji i dlaczego

Ściąga — same komendy git do przeglądu jednego commita:
```bash
git log --oneline -5        # orientacja: co ostatnio się działo w historii
git show --stat HEAD        # SAME NAZWY plików zmienionych w ostatnim commicie
git show HEAD                # PEŁNY diff ostatniego commita — dokładnie co się zmieniło, linijka po linijce
git diff HEAD~1 HEAD         # to samo co wyżej, inny zapis (przydatne gdy chcesz porównać dowolne dwa punkty)
```

- `git show --stat HEAD` — sprawdzasz, czy Ralph ruszył tylko to, co miał w
  zakresie zadania (`files.include`), a nie poszedł "przy okazji" majstrować
  gdzie indziej.
- `git show HEAD` — to jest to, co naprawdę chcesz przeczytać, nie sama lista
  plików ze `--stat`.
- `cat progress.txt` — to jego "pamięć" między iteracjami: czytasz ją, żeby
  wiedzieć, czy trafił na coś niejasnego, co wymaga Twojej decyzji, zanim
  pójdzie dalej.
- `PRD.json` — czy właściwe zadanie ma teraz `passes: true`.
- `uv run pytest && uv run mypy src && uv run ruff check .` — **niezależna
  weryfikacja własnymi rękami**: agent może się mylić co do tego, czy
  naprawdę wszystko przeszło, a odpalenie tego samemu zajmuje kilka sekund.

HITL = człowiek patrzy na każdą iterację na żywo, zanim pozwoli odpalić
kolejną. Dlaczego to ważne: agent bez nadzoru, przy niejasnym zadaniu, potrafi
po cichu zawęzić zakres i "ogłosić zwycięstwo" przedwcześnie. HITL to sposób,
żeby złapać takie zachowanie, zanim narobi szkód na wielu zadaniach naraz.

### Jak odpalić jedną iterację

1. Bądź w katalogu głównym repo, miej zainstalowane `uv` i `claude` (Claude Code CLI).
2. Uruchom `./ralph-once.sh`. Skrypt to jedna komenda:
   `claude --permission-mode acceptEdits "@PRD.json @progress.txt @CLAUDE.md ..."`.
   `@plik` wczytuje zawartość pliku od razu na start rozmowy — agent od
   pierwszej sekundy widzi listę zadań, pamięć z poprzednich iteracji i
   zasady projektu. `--permission-mode acceptEdits` automatycznie zatwierdza
   edycje, żeby pętla nie zatrzymywała się na promptach o zgodę.
3. Sesja czyta `PRD.json` + `progress.txt` + `CLAUDE.md`, znajduje pierwsze
   zadanie z `passes: false` i implementuje TYLKO je.
4. Ralph sam uruchamia `pytest`/`mypy`/`ruff`, commituje, ustawia
   `passes: true` i dopisuje notatkę do `progress.txt`.
5. Sesja zostaje otwarta po zakończeniu (interaktywna, bo skrypt NIE używa
   trybu headless) — wyjdź (`/exit`/Ctrl+D), zanim odpalisz ponownie. Każde
   uruchomienie startuje NOWY proces `claude` — to chroni przed "context rot"
   (im dłuższa sesja, tym gorszy output). Nie dopisuj nic ręcznie do starej
   sesji, zepsujesz tę świeżość.
6. Przejrzyj diff i commit — sedno HITL. Wróć do kroku 2 dla kolejnego
   zadania, aż uznasz, że można przejść na AFK, albo aż wszystkie zadania
   mają `passes: true`.

### Kiedy NIE odpalać kolejnej iteracji

- feedback loops nie przechodzą mimo commitu
- zadanie niezgodne z opisem/`edge_cases` w PRD.json
- Ralph tknął pliki spoza `files.include` danego zadania

## Tryb AFK (Away From Keyboard) — `afk-ralph.sh` + sandbox `sbx`

### Ściąga — same komendy

```bash
# --- w ZWYKŁYM TERMINALU (host) ---
brew trust docker/tap                       # zaufaj paczkom Dockera w Homebrew
brew install docker/tap/sbx                 # zainstaluj sbx (bez Docker Desktop)
sbx login                                   # zaloguj do Dockera, wybierz politykę sieci (Balanced)
sbx run claude .                            # WEJŚCIE #1 — tworzy sandbox i WCHODZI w interaktywną sesję Claude w środku

# --- teraz jesteś W SESJI CLAUDE (sesja #1), wewnątrz sandboksa ---
/login                                      # zaloguj Claude Pro/Max (w środku sandboksa)
/exit                                        # WYJŚCIE #1 — z powrotem do zwykłego shella, zanim pójdziesz dalej

# --- z powrotem w ZWYKŁYM TERMINALU (host) ---
brew install gh                             # jeśli `which gh` nic nie pokazuje — potrzebne do kroku niżej
gh auth login                               # interaktywne logowanie do GitHub (przeglądarka + jednorazowy kod)
gh auth token | sbx secret set -g github    # opcjonalnie: dostęp do push na GitHub
sbx stop claude-Ralph-HITL-Feed-Cleaning    # zatrzymaj — sandbox już działał PRZED sekretem, może go nie podłapać bez restartu
sbx run claude .                            # WEJŚCIE #2 — odpal ponownie, NOWA sesja Claude (tym razem z sekretem GitHub w środku)

# --- znowu W SESJI CLAUDE (sesja #2) — sprawdź że działa (np. git push), potem: ---
/exit                                        # WYJŚCIE #2 — z powrotem, zanim odpalisz pętlę AFK

# --- z powrotem w ZWYKŁYM TERMINALU (host) ---
sbx ls                                       # sprawdź nazwę i status sandboksa
./afk-ralph.sh 5                            # odpal pętlę AFK, limit 5 iteracji (to też host — headless, przez sbx exec)
```

### Co sprawdzić po pętli AFK (może być kilka commitów naraz)

Różnica względem HITL: jedno uruchomienie `./afk-ralph.sh 5` może zrobić
do 5 commitów, zanim znów na to spojrzysz — więc przeglądasz ZAKRES, nie
pojedynczy commit. Zapisz sobie punkt startowy PRZED odpaleniem pętli:

```bash
start=$(git rev-parse HEAD)                 # zapamiętaj, gdzie byliśmy PRZED pętlą
./afk-ralph.sh 5                             # odpal pętlę
git log --oneline "$start"..HEAD             # które commity dodała ta pętla, w skrócie
git diff "$start"..HEAD --stat               # szybki przegląd: ile plików, ile linii, bez treści
git diff "$start"..HEAD                      # PEŁNY diff wszystkich zmian z całej pętli naraz
uv run pytest && uv run mypy src && uv run ruff check .   # niezależna weryfikacja stanu na końcu
```

`git rev-parse HEAD` wypisuje pełny hash aktualnego commita — to Twój punkt
odniesienia "sprzed pętli". `git log`/`git diff` z zapisem `A..B` pokazują
wszystko, co się zmieniło MIĘDZY dwoma punktami, więc nie musisz sprawdzać
commitów jeden po drugim.

### Jeśli w trakcie AFK skończy się limit sesji Pro/Max

```bash
git status                              # cokolwiek niescommitowanego wisi po przerwanej iteracji?
git diff                                # jeśli tak — dokładna treść tych zmian
git log --oneline -3                    # ostatni FAKTYCZNY commit — na czym realnie stoimy
git stash                               # opcja A: schowaj niescommitowane zmiany na bok (odzyskiwalne później: git stash pop)
git checkout -- .                       # opcja B: odrzuć niescommitowane zmiany, zacznij to zadanie od zera
./afk-ralph.sh 5                        # po decyzji — po prostu odpal pętlę ponownie, gdy limit się zresetuje
```

AFK = pętla robi wiele zadań z rzędu **bez Twojego udziału**, z twardym
limitem iteracji jako zabezpieczeniem. Robimy to w izolowanym środowisku
(sandbox), nie w gołym terminalu: jeśli agent bez nadzoru zrobi coś głupiego,
szkoda zostaje zamknięta w tym środowisku, a nie rozlewa się na resztę
Twojego komputera.

> Sandboksy obsługuje samodzielny CLI `sbx` — osobny program od Dockera,
> nie wymaga Docker Desktop.

### Setup środowiska (jednorazowo)

1. Instalacja (macOS, Docker Desktop **niepotrzebny**): `brew trust docker/tap`
   mówi Homebrew "ufaj paczkom Dockera"; `brew install docker/tap/sbx`
   instaluje samo narzędzie — osobny proces (`sandboxd`), który tworzy i
   zarządza izolowanymi mikro-VM dla agentów AI, niezwiązany z Docker Desktop.
2. `sbx login` — logowanie **do Dockera, nie do Anthropica** (OAuth,
   konto Docker Hub/Docker ID). Przy pierwszym razie pyta o domyślną
   politykę sieciową: **Open** (bez ograniczeń) / **Balanced** (domyślny
   deny, popularne strony deweloperskie dozwolone — PyPI, GitHub) /
   **Locked Down** (wszystko zablokowane, chyba że jawnie odblokujesz).
   Wybraliśmy Balanced — loop potrzebuje `uv sync` (PyPI) i `git push`
   (GitHub), ale nie ma powodu, żeby agent miał nieograniczony dostęp do
   sieci, skoro cały sens sandboksa to ograniczenie szkód. Token loginu
   zostaje na hoście, persystuje między uruchomieniami.
3. **Auth Claude w środku:** `sbx run claude .` odpala świeżą, niezalogowaną
   instancję Claude Code (`Not logged in · Run /login`), jak przy nowej
   instalacji. Zwykłe `/login` subskrypcją Pro/Max działa — rozliczanie zostaje
   subskrypcyjne, nie przechodzi na płatność per token, mimo że dokumentacja
   `sbx secret set -g anthropic` sugerowała inaczej. Sam sandbox to warstwa
   izolacji, więc Claude Code startuje w środku w trybie "bypass permissions"
   — w praktyce to jednak nie wystarczyło (model i tak pytał o zgodę na Write),
   dlatego `afk-ralph.sh` podaje `--dangerously-skip-permissions` jawnie.
4. Jeśli chcemy, żeby AFK sam pushował na GitHub — komendy niżej **w
   zwykłym terminalu, NIE wewnątrz sesji Claude w sandboksie** (`sbx`/`gh`
   to komendy hosta, sandboksowa sesja sama je odrzuci):
   ```
   brew install gh
   gh auth login
   gh auth token | sbx secret set -g github
   ```
   `gh auth login` pyta: GitHub.com → HTTPS → przeglądarka → jednorazowy kod
   (wklej na stronie GitHuba, Authorize). Potwierdź `gh auth status`.
   `gh auth token` wypisuje token z już zalogowanego `gh`; `sbx secret set
   -g github` zapisuje go jako sekret globalny dla wszystkich sandboksów —
   `sbx` wstrzykuje go do środka bezpiecznie, token nigdy nie ląduje jako
   zwykły plik w kontenerze. Jeśli sandbox już działał PRZED ustawieniem
   sekretu (jak nasz `claude-Ralph-HITL-Feed-Cleaning`), zrestartuj:
   `sbx stop claude-Ralph-HITL-Feed-Cleaning` i `sbx run claude .` ponownie.

### Dostęp do plików projektu

Domyślnie: bind mount, read-write — katalog projektu jest po prostu "wpięty"
do sandboksa pod tą samą ścieżką, jak okienko na Twój prawdziwy folder.
Zmiany agenta lądują na dysku hosta natychmiast, widoczne od razu jako
zwykły `git diff`. Alternatywa: `--clone` (przy `sbx create`/`sbx run`) —
agent dostaje prywatny klon repo w kontenerze, a jego commity trafiają z
powrotem przez osobny git remote `sandbox-<name>`, zamiast dotykać Twojego
working tree bezpośrednio. Zostajemy przy bind mount — prostsze, a
`afk-ralph.sh` i tak ma twardy limit iteracji jako zabezpieczenie. Reszta
systemu poza tym katalogiem jest dla agenta niewidoczna.

### Uruchomienie pętli AFK — `afk-ralph.sh`

```
./afk-ralph.sh 5
```

Argument (`5`) to limit iteracji — zabezpieczenie przed niekontrolowanym
kosztem/czasem, gdyby coś poszło w pętlę bez końca. Headless
`sbx exec ... claude -p "..."` zwraca czysty tekst i kończy się sam (bez
otwierania sesji interaktywnej, inaczej niż `ralph-once.sh`), a sygnał
`<promise>COMPLETE</promise>` przechodzi przez przechwytywanie w zmiennej
bashowej nietknięty.

Skrypt krok po kroku: `set -e` zatrzymuje całość przy pierwszym błędzie,
zamiast lecieć dalej w niewiadomym stanie. `SANDBOX`/`WORKDIR` to nazwa
Twojego sandboksa i ścieżka projektu — potrzebne, żeby `sbx exec` wiedział,
gdzie i w czym uruchomić komendę. Brak argumentu (`$1`) → komunikat użycia
i `exit 1` — limit iteracji jest obowiązkowy, nie opcjonalny. Pętla `for`
woła `sbx exec -w "$WORKDIR" "$SANDBOX" claude -p --dangerously-skip-permissions "<prompt zadania>" < /dev/null`
— `-p` to tryb "print": agent robi swoją robotę (czyta pliki, pisze kod,
testuje, commituje) i sam kończy proces, zamiast zostawiać otwartą sesję
(konieczne dla AFK, nikt nie siedzi, żeby ją zamknąć). `< /dev/null` mówi
komendzie "nie czekaj na wejście" — bez tego `sbx exec` czekał 3 sekundy i
ostrzegał. Wynik trafia do `result` i na ekran (`echo "$result"`), żeby
zostać po sobie log z każdej iteracji. Jeśli w odpowiedzi pojawi się dokładnie
`<promise>COMPLETE</promise>` (Claude ma to wypisać, gdy wszystkie zadania w
`PRD.json` mają już `passes: true`) — pętla kończy się od razu (`exit 0`),
zamiast marnować kolejne iteracje. Jeśli limit się wyczerpie bez tego
sygnału, ostatnia linijka to mówi wprost — sprawdź `progress.txt` i
`git log`, co poszło nie tak.

## Kto co robi

- **Ty, w osobnym terminalu**: odpalasz `ralph-once.sh` / `afk-ralph.sh`,
  logujesz się do Dockera/Anthropica, obserwujesz iteracje, decydujesz o
  przejściu HITL→AFK.
- **Ta sesja Claude Code (planowanie)**: PRD.json, CLAUDE.md, README,
  przygotowanie `afk-ralph.sh`, przegląd commitów i diffów, commit/push na
  Twoją prośbę. Nie odpala autonomicznych pętli sama.
