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

## Tryb AFK (Away From Keyboard) — `afk-ralph.sh` + Docker sandbox

AFK = pętla działa bez nadzoru, z twardym limitem iteracji, w izolowanym
środowisku (Docker sandbox), nie w gołym terminalu. Przechodzimy tu **dopiero
gdy kilka iteracji HITL z rzędu zachowa się zgodnie z oczekiwaniami** —
planowo po domknięciu zadań 2-3 (`PRD.json`) pod HITL, startując od zadania 4.

Kroki logowania/uruchamiania poniżej wykonujesz Ty, we własnym terminalu —
to interaktywne akcje (OAuth w przeglądarce), których nie da się zrobić z tej
sesji Claude Code.

### Setup środowiska (jednorazowo)

1. Docker Desktop **4.50+** zainstalowany i faktycznie uruchomiony (ikona w pasku menu).
2. Sprawdź dostępność subkomendy:
   ```
   docker sandbox --help
   ```
3. Pierwsze logowanie do Anthropic w sandboksie:
   ```
   docker sandbox run claude
   ```
   Dane logowania trzymane są w wolumenie Dockera — logujesz się raz, stan przeżywa między uruchomieniami (jeden sandbox na workspace).
4. **Znany bug:** logowanie subskrypcją Pro/Max może się wywalić błędem "Invalid bearer token" (wtyczka sandboksa nadpisuje OAuth przez `apiKeyHelper`). Obejście:
   ```
   docker sandbox exec -it <nazwa> bash
   ```
   a w środku usuń linię `apiKeyHelper` z `~/.claude/settings.json`.
5. Jeśli chcemy, żeby AFK sam pushował na GitHub (nie tylko lokalny commit), jednorazowo:
   ```
   sbx secret set -g github
   ```

### Dostęp do plików projektu

Katalog roboczy montuje się w kontenerze pod tą samą ścieżką (bind mount) —
zmiany lądują naprawdę na dysku hosta, w czasie rzeczywistym, widoczne od razu
jako zwykły `git diff`, nic nie ginie po zamknięciu kontenera. Reszta systemu
poza tym katalogiem jest niedostępna — to cała idea izolacji. Globalny
`~/.claude/CLAUDE.md` i user-level skille **nie** ładują się w sandboksie —
bez znaczenia dla nas, bo cała logika projektu siedzi w tutejszym
`CLAUDE.md`/`PRD.json`.

### Uruchomienie pętli AFK

`afk-ralph.sh` zostanie dopisany do repo, gdy dojdziemy do tego etapu (po
udanych iteracjach HITL na zadaniach 2-3). Będzie przyjmował limit iteracji
jako argument, np.:

```
./afk-ralph.sh 5
```

W środku: `docker sandbox run claude --permission-mode acceptEdits -p "..."`
w pętli — tryb `-p` (headless/print) zamiast interaktywnego, bo nikt nie
patrzy na żywo. Skrypt sam sprawdza w stdout sygnał
`<promise>COMPLETE</promise>` i kończy się wcześniej, jeśli `PRD.json` jest
już całe zrobione, zamiast czekać do limitu iteracji.

## Kto co robi

- **Ty, w osobnym terminalu**: odpalasz `ralph-once.sh` / `afk-ralph.sh`,
  logujesz się do Dockera/Anthropica, obserwujesz iteracje, decydujesz o
  przejściu HITL→AFK.
- **Ta sesja Claude Code (planowanie)**: PRD.json, CLAUDE.md, README,
  przygotowanie `afk-ralph.sh`, przegląd commitów i diffów, commit/push na
  Twoją prośbę. Nie odpala autonomicznych pętli sama.
