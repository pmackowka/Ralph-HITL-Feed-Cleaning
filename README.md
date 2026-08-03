# Ralph — CLI do czyszczenia feedu produktowego

Projekt testowy do nauki metody Ralpha (autonomiczna pętla kodowania z Claude Code).
Pełna specyfikacja i metodologia: `CLAUDE.md`. Lista zadań: `PRD.json`.

## Co to w ogóle jest Ralph i po co te dwa tryby

Ralph to ten sam prompt uruchamiany w kółko: agent czyta listę zadań
(`PRD.json`), sam wybiera pierwsze nieukończone, implementuje TYLKO je,
uruchamia testy, commituje, zapisuje postęp — i tak od nowa, aż lista się
skończy. Sedno: **Ty definiujesz cel (PRD), agent sam dochodzi do niego
krok po kroku**, zamiast Ciebie piszącego nowy prompt do każdej fazy.

Są dwa tryby, w tej kolejności — nigdy odwrotnie:

- **HITL** (`ralph-once.sh`) — jedna iteracja na raz, Ty patrzysz na żywo
  i ręcznie odpalasz kolejną. Na start, żeby zbudować zaufanie do promptu.
- **AFK** (`afk-ralph.sh`) — wiele iteracji z rzędu, bez Twojego nadzoru,
  z twardym limitem i w izolowanym środowisku (sandbox). Dopiero gdy HITL
  parę razy z rzędu zachował się tak, jak się spodziewałeś.

Pętlę odpalasz **w osobnym terminalu**, nie w tej sesji planistycznej Claude
Code — patrz "Kto co robi" na końcu tego pliku.

## Tryb HITL (Human In The Loop) — `ralph-once.sh`

### Ściąga — same komendy

```bash
./ralph-once.sh                                            # 1 iteracja: Ralph robi jedno zadanie z PRD.json
# ...poczekaj aż sesja odpowie i skończy...
/exit                                                       # albo Ctrl+D — zamknij sesję przed kolejnym uruchomieniem
git show --stat HEAD                                       # co zmienił ostatni commit
cat progress.txt                                            # notatka Ralpha o tej iteracji
uv run pytest && uv run mypy src && uv run ruff check .    # niezależna weryfikacja, nie ufaj samemu commitowi
./ralph-once.sh                                             # jeśli OK — kolejna iteracja
```

### Co sprawdzić po każdej iteracji i dlaczego

Ściąga — same komendy git do przeglądu jednego commita:
```bash
git log --oneline -5        # orientacja: co ostatnio się działo w historii
git show --stat HEAD        # SAME NAZWY plików zmienionych w ostatnim commicie
git show HEAD                # PEŁNY diff ostatniego commita — dokładnie co się zmieniło, linijka po linijce
git diff HEAD~1 HEAD         # to samo co wyżej, inny zapis (przydatne gdy chcesz porównać dowolne dwa punkty)
```

- `git show --stat HEAD` — jakie pliki zmienione. Sprawdzasz, czy Ralph
  ruszył tylko to, co miał w zakresie zadania (`files.include`), a nie
  poszedł "przy okazji" majstrować gdzie indziej.
- `git show HEAD` — pełny diff, nie tylko lista plików. To jest to, co
  naprawdę chcesz przeczytać: dokładna treść zmian, linia po linii, ze
  znakiem `+`/`-` przy każdej dodanej/usuniętej linijce.
- `cat progress.txt` — notatka Ralpha o tym, co zrobił i jakie decyzje podjął.
  To jego "pamięć" między iteracjami — czytasz ją, żeby wiedzieć, czy trafił
  na coś niejasnego, co wymaga Twojej decyzji, zanim pójdzie dalej.
- `PRD.json` — czy właściwe zadanie ma teraz `passes: true`.
- `uv run pytest && uv run mypy src && uv run ruff check .` — **niezależna
  weryfikacja własnymi rękami**, nie ufaj samemu zielonemu commitowi. Agent
  może się mylić co do tego, czy naprawdę wszystko przeszło — odpalenie tego
  samemu zajmuje kilka sekund i jest jedynym pewnym dowodem.

HITL = człowiek patrzy na każdą iterację na żywo, zanim pozwoli odpalić
kolejną. Dlaczego to ważne: agent bez nadzoru, przy niejasnym zadaniu, potrafi
po cichu zawęzić zakres i "ogłosić zwycięstwo" przedwcześnie. HITL to sposób,
żeby złapać takie zachowanie, zanim narobi szkód na wielu zadaniach naraz.

### Jak odpalić jedną iterację

1. Bądź w katalogu głównym repo, miej zainstalowane `uv` i `claude` (Claude Code CLI).
2. Uruchom:
   ```
   ./ralph-once.sh
   ```
   **Co to robi:** skrypt zawiera jedną komendę —
   `claude --permission-mode acceptEdits "@PRD.json @progress.txt @CLAUDE.md ..."`.
   `@plik` to sposób, w jaki Claude Code wczytuje zawartość konkretnego pliku
   od razu na start rozmowy — agent od pierwszej sekundy "widzi" listę zadań,
   swoją pamięć z poprzednich iteracji i zasady projektu. Flaga
   `--permission-mode acceptEdits` mówi Claude Code, żeby automatycznie
   zatwierdzał edycje plików, zamiast pytać Cię o zgodę na każdą zmianę —
   bez tego pętla zatrzymywałaby się na promptach o zgodę i przestałaby być
   automatyzacją.
3. Sesja Claude Code czyta `PRD.json` + `progress.txt` + `CLAUDE.md`, znajduje pierwsze zadanie z `passes: false` i implementuje TYLKO je.
4. Ralph sam uruchamia `pytest`/`mypy`/`ruff`, commituje, ustawia `passes: true` dla ukończonego zadania i dopisuje notatkę do `progress.txt`.
5. Gdy skończy, sesja Claude zostaje otwarta (interaktywna — bo skrypt NIE używa trybu headless) — wyjdź z niej (`/exit` albo Ctrl+D), zanim uruchomisz skrypt ponownie. **Dlaczego to ważne:** każde uruchomienie `./ralph-once.sh` odpala NOWY, świeży proces `claude` — to jest właśnie to, co chroni Ralpha przed tzw. "context rot" (im dłużej trwa jedna sesja, tym gorszy staje się output). Jeśli zostawisz starą sesję otwartą i wpiszesz w niej coś ręcznie, zepsujesz tę świeżość.
6. Przejrzyj diff i commit — to jest sedno HITL. Jeśli wygląda dobrze, wróć do kroku 2 dla kolejnego zadania. Powtarzaj, aż uznasz, że można przejść na AFK (patrz niżej), albo aż wszystkie zadania mają `passes: true`.

### Kiedy NIE odpalać kolejnej iteracji

- feedback loops nie przechodzą mimo commitu
- zadanie niezgodne z opisem/`edge_cases` w PRD.json
- Ralph tknął pliki spoza `files.include` danego zadania

## Tryb AFK (Away From Keyboard) — `afk-ralph.sh` + Docker Sandboxes (`sbx`)

### Ściąga — same komendy

```bash
brew trust docker/tap                       # zaufaj paczkom Dockera w Homebrew
brew install docker/tap/sbx                 # zainstaluj sbx (bez Docker Desktop)
sbx login                                   # zaloguj do Dockera, wybierz politykę sieci (Balanced)
sbx run claude .                            # utwórz sandbox; w środku /login do Claude (Pro/Max działa)
gh auth token | sbx secret set -g github    # opcjonalnie: dostęp do push na GitHub
sbx ls                                      # sprawdź nazwę i status sandboksa
./afk-ralph.sh 5                            # odpal pętlę AFK, limit 5 iteracji
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
limitem iteracji jako zabezpieczeniem ("nie więcej niż N prób, potem stop
niezależnie od tego, co się dzieje"). Robimy to w izolowanym środowisku
(sandbox), nie w gołym terminalu, z jednego prostego powodu: jeśli agent bez
nadzoru zrobi coś głupiego (np. usunie coś, czego nie powinien), szkoda
zostaje zamknięta w tym izolowanym środowisku, a nie rozlewa się na resztę
Twojego komputera.

> **Uwaga — narzędzie się zmieniło.** Stare `docker sandbox run claude`
> (opisane w notatce Ralpha) zostało **zdeprecjonowane i usunięte**. Następca
> to samodzielny CLI `sbx` — osobny program od Dockera, **nie wymaga już
> Docker Desktop** (możesz go nawet nie mieć zainstalowanego). Poniższe
> komendy zweryfikowane bezpośrednio przez `sbx --help` i realne testy w
> terminalu (nie z dokumentacji, która bywa nieaktualna), 2026-08-02.

Kroki logowania/uruchamiania poniżej wykonujesz Ty, we własnym terminalu —
to interaktywne akcje (OAuth w przeglądarce), których nie da się zrobić z tej
sesji Claude Code.

### Setup środowiska (jednorazowo)

1. Instalacja (macOS, Docker Desktop **niepotrzebny**):
   ```
   brew trust docker/tap
   brew install docker/tap/sbx
   ```
   **Co to robi:** `brew trust docker/tap` mówi Homebrew "ufaj paczkom
   publikowanym przez Dockera" (bez tego `brew` ostrzega przed instalacją z
   nieznanego źródła). Druga komenda instaluje samo narzędzie `sbx` —
   program, który tworzy i zarządza izolowanymi mikro-maszynami wirtualnymi
   dla agentów AI. To osobny proces (`sandboxd`), niezwiązany z Docker
   Desktop.
2. Logowanie — **do Dockera, nie do Anthropica**:
   ```
   sbx login
   ```
   Otwiera OAuth w przeglądarce (logujesz się kontem Docker Hub/Docker ID).
   Przy pierwszym razie pyta o domyślną politykę sieciową:
   **Open** (zero ograniczeń) / **Balanced** (domyślny deny, popularne
   strony deweloperskie dozwolone — PyPI, GitHub itd.) / **Locked Down**
   (wszystko zablokowane, chyba że jawnie odblokujesz). Wybraliśmy
   **Balanced** — nasz loop potrzebuje `uv sync` (PyPI) i `git push`
   (GitHub), ale nie ma powodu, żeby agent miał nieograniczony dostęp do
   sieci, skoro cały sens sandboksa to ograniczenie szkód. Token logowania
   zostaje zapisany na Twoim hoście (nie w środku sandboksa) — persystuje
   między uruchomieniami, nie musisz się logować od nowa jutro.
3. **Auth Claude w środku — potwierdzone empirycznie:** `sbx run claude .`
   odpala świeżą, niezalogowaną instancję Claude Code w środku sandboksa
   (`Not logged in · Run /login`) — dokładnie jak przy zupełnie nowej
   instalacji Claude Code na nowym komputerze. Zwykłe `/login` w środku i
   logowanie subskrypcją Pro/Max **działa** — rozliczanie zostaje jak
   dotychczas (subskrypcja), nie przechodzi na płatność per token przez
   klucz API, mimo że dokumentacja `sbx secret set -g anthropic` sugerowała
   inaczej. Bonus zauważony przy okazji: sandbox sam w sobie jest warstwą
   izolacji, więc Claude Code w środku domyślnie startuje w trybie
   "bypass permissions" (zero pytań o zgodę na edycje) — to dlatego w
   `afk-ralph.sh` niżej nie ma już `--permission-mode acceptEdits`, jak
   miał `ralph-once.sh`.
4. Jeśli chcemy, żeby AFK sam pushował na GitHub (nie tylko lokalny commit):
   ```
   gh auth token | sbx secret set -g github
   ```
   **Co to robi:** `gh auth token` wypisuje Twój token dostępu do GitHuba
   (z Twojego już zalogowanego `gh` CLI). `sbx secret set -g github`
   zapisuje go jako "sekret" dostępny globalnie dla wszystkich sandboksów —
   `sbx` wstrzykuje go do środka w bezpieczny sposób (agent może go użyć do
   pushowania, ale sam token nigdy nie ląduje jako zwykły plik widoczny w
   systemie plików kontenera).

### Dostęp do plików projektu

Domyślnie: bind mount, read-write — to znaczy, że katalog projektu jest po
prostu "wpięty" do sandboksa pod tą samą ścieżką, jakby to było okienko na
Twój prawdziwy folder. Zmiany agenta lądują na dysku hosta natychmiast,
widoczne od razu jako zwykły `git diff` — nic nie dzieje się "w oderwaniu"
i nic nie ginie po zamknięciu sandboksa. Alternatywa: `--clone` (przy
`sbx create`/`sbx run`) — agent dostaje prywatny klon repo w kontenerze,
a jego commity trafiają z powrotem przez specjalny git remote
`sandbox-<name>` zamiast dotykać Twojego working tree bezpośrednio. My
zostajemy przy domyślnym bind mount — prostsze, a `afk-ralph.sh` i tak ma
twardy limit iteracji jako zabezpieczenie. Reszta systemu poza tym
katalogiem jest dla agenta niewidoczna — to cała idea izolacji.

### Uruchomienie pętli AFK — `afk-ralph.sh`

Wszystko poniżej **potwierdzone empirycznie w tym terminalu**, nie hipoteza
z dokumentacji: headless `sbx exec ... claude -p "..."` zwraca czysty tekst
i kończy się samo (bez otwierania sesji interaktywnej), a sygnał
`<promise>COMPLETE</promise>` przechodzi przez przechwytywanie w zmiennej
bashowej nietknięty.

```
./afk-ralph.sh 5
```

Argument (`5`) to limit iteracji — twarde zabezpieczenie przed niekontrolowanym
kosztem/czasem, gdyby coś poszło w pętlę bez końca.

Pełna treść skryptu, linijka po linijce:

```bash
#!/bin/bash
set -e
```
`#!/bin/bash` mówi systemowi "uruchom to jako skrypt basha" — standardowy
nagłówek każdego skryptu bash. `set -e` oznacza: jeśli JAKAKOLWIEK komenda w
skrypcie zwróci błąd, cały skrypt natychmiast się zatrzymuje, zamiast lecieć
dalej w niewiadomym stanie. Wolimy, żeby pętla stanęła, niż żeby ciągnęła
kolejne iteracje po czymś, co poszło nie tak.

```bash
SANDBOX="claude-Ralph-HITL-Feed-Cleaning"
WORKDIR="/Users/p/Documents/dev/Ralph-HITL-Feed-Cleaning"
```
Dwie zmienne, żeby nie powtarzać tych samych ścieżek/nazw w kilku miejscach
skryptu. `SANDBOX` to nazwa Twojego już utworzonego i zalogowanego
sandboksa (potwierdzona przez `sbx ls`). `WORKDIR` to ścieżka do projektu —
potrzebna, żeby powiedzieć `sbx exec`, w którym katalogu ma uruchomić
komendę w środku kontenera.

```bash
if [ -z "$1" ]; then
  echo "Użycie: $0 <liczba_iteracji>"
  exit 1
fi
```
`$1` to pierwszy argument, z którym uruchamiasz skrypt (`./afk-ralph.sh 5`
→ `$1` = `"5"`). Jeśli go nie podałeś, skrypt wypisuje instrukcję użycia i
kończy działanie z kodem błędu (`exit 1`). Zabezpieczenie przed przypadkowym
odpaleniem bez limitu — limit jest obowiązkowy, nie opcjonalny.

```bash
for ((i=1; i<=$1; i++)); do
  echo "--- Iteracja $i/$1 ---"
```
Pętla licząca od 1 do podanego limitu. `echo` wypisuje numer aktualnej
iteracji, żebyś widział postęp w logu, gdy wrócisz i przewiniesz ekran.

```bash
  result=$(sbx exec -w "$WORKDIR" "$SANDBOX" claude -p "..." < /dev/null)
```
To jest serce skryptu. `sbx exec` wchodzi do już istniejącego, zalogowanego
sandboksa i uruchamia w nim komendę `claude -p "<długi prompt z instrukcją
zadania>"`. Flaga `-p` to tryb "print" Claude Code: agent dostaje prompt,
robi swoją robotę (czyta pliki, pisze kod, uruchamia testy, commituje), a
na końcu WYPISUJE odpowiedź jako zwykły tekst i sam kończy proces — zamiast
zostawić otwartą, interaktywną rozmowę, jak robi `ralph-once.sh`. To
konieczne dla AFK: nikt nie siedzi, żeby ręcznie zamknąć sesję.
`result=$(...)` przechwytuje to, co Claude wypisał, do zmiennej `result`,
żeby dało się to sprawdzić w kolejnej linijce. `< /dev/null` mówi komendzie
"nie czekaj na żadne dane wejściowe" — bez tego `sbx exec` czekał 3 sekundy
i wypisywał ostrzeżenie, bo domyślnie próbuje coś odczytać ze standardowego
wejścia.

```bash
  echo "$result"
```
Wypisuje odpowiedź Claude'a na ekran — żebyś miał log z każdej iteracji,
mimo że nikt nie patrzył na żywo w momencie jej wykonania.

```bash
  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    echo "PRD ukończony po $i iteracjach."
    exit 0
  fi
done
```
Sprawdza, czy w odpowiedzi pojawił się dokładnie napis
`<promise>COMPLETE</promise>` — Claude ma w promptcie instrukcję, żeby to
wypisać, GDY zobaczy, że wszystkie zadania w `PRD.json` mają już
`passes: true`. Jeśli tak, pętla kończy się od razu (`exit 0` = sukces),
zamiast marnować kolejne iteracje na nic. `done` zamyka pętlę `for`.

```bash
echo "Osiągnięto limit iteracji ($1) bez sygnału ukończenia PRD."
```
Jeśli pętla przeleciała wszystkie iteracje i nigdy nie zobaczyła sygnału
ukończenia, ta linijka wypisuje się na sam koniec — informacja dla Ciebie,
że PRD nie jest jeszcze skończone i trzeba albo podnieść limit, albo
sprawdzić, co poszło nie tak (np. przez `progress.txt` i `git log`).

## Kto co robi

- **Ty, w osobnym terminalu**: odpalasz `ralph-once.sh` / `afk-ralph.sh`,
  logujesz się do Dockera/Anthropica, obserwujesz iteracje, decydujesz o
  przejściu HITL→AFK.
- **Ta sesja Claude Code (planowanie)**: PRD.json, CLAUDE.md, README,
  przygotowanie `afk-ralph.sh`, przegląd commitów i diffów, commit/push na
  Twoją prośbę. Nie odpala autonomicznych pętli sama.
