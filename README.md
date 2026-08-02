# Ralph — CLI do czyszczenia feedu produktowego

Projekt testowy do nauki metody Ralpha (autonomiczna pętla kodowania z Claude Code).
Pełna specyfikacja i metodologia: `CLAUDE.md`. Lista zadań: `PRD.json`.

## Jak odpalić jedną iterację (`ralph-once.sh`)

1. Bądź w katalogu głównym repo, miej zainstalowane `uv` i `claude` (Claude Code CLI).
2. Uruchom:
   ```
   ./ralph-once.sh
   ```
3. Sesja Claude Code (`--permission-mode acceptEdits`) czyta `PRD.json` + `progress.txt` + `CLAUDE.md`, znajduje pierwsze zadanie z `passes: false` i implementuje TYLKO je.
4. Ralph sam uruchamia `pytest`/`mypy`/`ruff`, commituje, ustawia `passes: true` dla ukończonego zadania i dopisuje notatkę do `progress.txt`.
5. Gdy skończy — przejrzyj diff i commit, zanim odpalisz kolejną iterację. To jest sedno HITL.
6. Jeśli wygląda dobrze, uruchom `./ralph-once.sh` ponownie dla kolejnego zadania. Powtarzaj, aż wszystkie zadania w `PRD.json` mają `passes: true`.

## Co sprawdzić po każdej iteracji

- `git show --stat HEAD` — jakie pliki zmienione
- `cat progress.txt` — notatka Ralpha
- `PRD.json` — czy właściwe zadanie ma teraz `passes: true`
- `uv run pytest && uv run mypy src && uv run ruff check .` — niezależna weryfikacja, nie ufaj samemu zielonemu commitowi

## Kiedy NIE odpalać kolejnej iteracji

- feedback loops nie przechodzą mimo commitu
- zadanie niezgodne z opisem/`edge_cases` w PRD.json
- Ralph tknął pliki spoza `files.include` danego zadania

## Docker / AFK (`afk-ralph.sh`)

Jeszcze nie istnieje. Zgodnie z `CLAUDE.md` przechodzimy do trybu bez nadzoru dopiero po kilku udanych iteracjach HITL z rzędu.
