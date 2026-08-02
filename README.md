# Ralph — CLI do czyszczenia feedu produktowego

Projekt testowy do nauki metody Ralpha (autonomiczna pętla kodowania z Claude Code).
Pełna specyfikacja i metodologia: `CLAUDE.md`. Lista zadań: `PRD.json`.

Pętlę odpalasz **w osobnym terminalu**, nie w tej sesji planistycznej Claude Code —
patrz "Kto co robi" na końcu tego pliku.

## Tryb HITL (Human In The Loop) — `ralph-once.sh`

HITL = człowiek patrzy na każdą iterację na żywo, zanim pozwoli odpalić kolejną.
Jedno uruchomienie skryptu = jedno zadanie z `PRD.json`, w pełni interaktywna
sesja Claude Code (`--permission-mode acceptEdits` — edycje plików
auto-zatwierdzane, ale sesja widoczna i przerywalna Ctrl+C). Ten tryb jest na
start, żeby zbudować zaufanie do promptu, zanim oddamy stery.

### Jak odpalić jedną iterację

1. Bądź w katalogu głównym repo, miej zainstalowane `uv` i `claude` (Claude Code CLI).
2. Uruchom:
   ```
   ./ralph-once.sh
   ```
3. Sesja Claude Code czyta `PRD.json` + `progress.txt` + `CLAUDE.md`, znajduje pierwsze zadanie z `passes: false` i implementuje TYLKO je.
4. Ralph sam uruchamia `pytest`/`mypy`/`ruff`, commituje, ustawia `passes: true` dla ukończonego zadania i dopisuje notatkę do `progress.txt`.
5. Gdy skończy, sesja Claude zostaje otwarta (interaktywna) — wyjdź z niej (`/exit` albo Ctrl+D), zanim uruchomisz skrypt ponownie.
6. Przejrzyj diff i commit — to jest sedno HITL. Jeśli wygląda dobrze, wróć do kroku 2 dla kolejnego zadania. Powtarzaj, aż uznasz, że można przejść na AFK (patrz niżej), albo aż wszystkie zadania mają `passes: true`.

### Co sprawdzić po każdej iteracji

- `git show --stat HEAD` — jakie pliki zmienione
- `cat progress.txt` — notatka Ralpha
- `PRD.json` — czy właściwe zadanie ma teraz `passes: true`
- `uv run pytest && uv run mypy src && uv run ruff check .` — niezależna weryfikacja, nie ufaj samemu zielonemu commitowi

### Kiedy NIE odpalać kolejnej iteracji

- feedback loops nie przechodzą mimo commitu
- zadanie niezgodne z opisem/`edge_cases` w PRD.json
- Ralph tknął pliki spoza `files.include` danego zadania

## Tryb AFK (Away From Keyboard) — `afk-ralph.sh` + Docker Sandboxes (`sbx`)

AFK = pętla działa bez nadzoru, z twardym limitem iteracji, w izolowanym
środowisku, nie w gołym terminalu. Przechodzimy tu **dopiero gdy kilka
iteracji HITL z rzędu zachowa się zgodnie z oczekiwaniami**.

> **Uwaga — narzędzie się zmieniło.** Stare `docker sandbox run claude`
> (opisane w notatce Ralpha) zostało **zdeprecjonowane i usunięte**. Następca
> to samodzielny CLI `sbx` — **nie wymaga już Docker Desktop**. Poniższe
> komendy zweryfikowane bezpośrednio przez `sbx --help` (nie z dokumentacji,
> która bywa nieaktualna), 2026-08-02.

Kroki logowania/uruchamiania poniżej wykonujesz Ty, we własnym terminalu —
to interaktywne akcje (OAuth w przeglądarce), których nie da się zrobić z tej
sesji Claude Code.

### Setup środowiska (jednorazowo)

1. Instalacja (macOS, Docker Desktop **niepotrzebny**):
   ```
   brew trust docker/tap
   brew install docker/tap/sbx
   ```
2. Logowanie — **do Dockera, nie do Anthropica**:
   ```
   sbx login
   ```
   Otwiera OAuth w przeglądarce, przy pierwszym razie pyta o domyślną politykę sieciową (Open/Balanced/Locked Down). Token zostaje na hoście, nie w sandboksie — persystuje między uruchomieniami.
3. **Auth Claude w środku — potwierdzone empirycznie (2026-08-02):** `sbx run claude .` odpala świeżą, niezalogowaną instancję Claude Code w środku (`Not logged in · Run /login`) — dokładnie jak przy nowej instalacji, nie wymusza klucza API mimo że `sbx secret set -g anthropic` sugerowałby API key. Zwykłe `/login` w środku sandboksa i logowanie subskrypcją Pro/Max **działa** — rozliczanie zostaje jak dotychczas, nie per-token. Bonus: sandbox sam jest warstwą izolacji, więc Claude Code w środku domyślnie startuje w `bypass permissions on` — `--permission-mode acceptEdits` może być zbędne przy uruchamianiu w `sbx`.
4. Jeśli chcemy, żeby AFK sam pushował na GitHub (nie tylko lokalny commit):
   ```
   gh auth token | sbx secret set -g github
   ```

### Dostęp do plików projektu

Domyślnie: bind mount, read-write — katalog roboczy widoczny w sandboksie,
zmiany agenta lądują na hoście natychmiast, widoczne od razu jako zwykły
`git diff`. Alternatywa: `--clone` (przy `sbx create`/`sbx run`) — agent
dostaje prywatny klon repo w kontenerze, jego commity trafiają z powrotem
przez git remote `sandbox-<name>` na hoście, zamiast dotykać working tree
bezpośrednio. Reszta systemu poza workspace'em niedostępna.

### Uruchomienie — komendy zweryfikowane, ale jeszcze bez `afk-ralph.sh`

Interaktywnie (jak `ralph-once.sh`, ale w sandboksie):
```
sbx run claude .
```

Do pętli bez nadzoru prawdopodobnie potrzebujemy `create` (sandbox bez
attachu) + `exec` (komenda non-interactive w środku), bo `sbx run` sam w
sobie otwiera sesję interaktywną:
```
sbx create --name ralph-afk claude .          # raz, tworzy sandbox
sbx exec ralph-afk claude --permission-mode acceptEdits -p "..."   # w pętli
```
Argumenty do samego agenta idą po separatorze `--` (np. `sbx run claude -- --continue`).

**To jest hipoteza wynikająca z realnego `--help`, NIE potwierdzone
end-to-end** — logowanie (krok 3 wyżej) już potwierdzone, ale `sbx exec` w
pętli (bez attachu, z `-p`) jeszcze nie testowany na żywo. `sbx` nie ma
własnego trybu headless, więc opieramy się na `-p` samego `claude`
przekazanym przez `sbx exec`. `afk-ralph.sh` napiszę dopiero po tym, jak
przetestujemy tę część razem.

## Kto co robi

- **Ty, w osobnym terminalu**: odpalasz `ralph-once.sh` / `afk-ralph.sh`,
  logujesz się do Dockera/Anthropica, obserwujesz iteracje, decydujesz o
  przejściu HITL→AFK.
- **Ta sesja Claude Code (planowanie)**: PRD.json, CLAUDE.md, README,
  przygotowanie `afk-ralph.sh`, przegląd commitów i diffów, commit/push na
  Twoją prośbę. Nie odpala autonomicznych pętli sama.
