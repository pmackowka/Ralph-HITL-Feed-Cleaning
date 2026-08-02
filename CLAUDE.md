# Ralph — Projekt testowy #1: CLI do czyszczenia feedu produktowego

> Rozszerzona notatka o ideologii i mechanice Ralpha (Autonomiczna Pętla Kodowania): `/Users/p/Documents/dev/Knowledge-Base/wiki/AI/Ralph-Autonomiczna-Petla-Kodowania.md`

## Co ma robić

Mały CLI (Python), który:

1. Wczytuje syntetyczny feed produktowy w CSV (celowo "brudny" — duplikaty SKU, ceny jako tekst z przecinkiem/walutą, brakujące pola, ujemne ilości, złe typy).
2. Waliduje każdy rekord wg jawnego schematu (Pydantic) i klasyfikuje: OK / do naprawy / do odrzucenia.
3. Czyści to, co da się naprawić automatycznie (np. `"29,99 zł"` → `29.99`), odrzuca resztę z podanym powodem.
4. Eksportuje wynik do Parquet (czyste dane) + osobny raport jakości danych (ile rekordów OK/naprawiono/odrzucono, wg jakiej reguły).

Dane wejściowe: generuję deterministycznym skryptem, **przed** startem pętli (nie zadaniem dla Ralpha) — dzięki temu znam z góry, ile i jakich błędów wstrzyknąłem, więc mogę zweryfikować, czy Ralph faktycznie je złapał, zamiast oceniać "na oko".

## Stop condition (mierzalne, nie ocena)

- `pytest` — 100% zielony (testy jednostkowe parsera, walidacji, eksportu).
- `mypy` — bez błędów.
- `ruff` — bez błędów.
- Raport jakości danych zawiera policzone metryki zgodne z liczbą błędów wstrzykniętych do syntetycznego feedu (weryfikacja ręczna, nie automatyczna — to sprawdzam ja).

## Jak ma działać w pętli — HITL (`ralph-once.sh`)

Zanim cokolwiek zostanie zautomatyzowane bez nadzoru (AFK, Docker sandbox) — najpierw kilka ręcznych iteracji, żeby zbudować zaufanie do promptu.

1. **Plan mode** (`shift-tab`) w nowej sesji Claude Code — dopytanie o niejasności, zapis `PRD.json` jako lista zadań (każde z: `description`, `files`, `stop_condition`, `edge_cases`, `passes: false`).
2. Zadania uporządkowane wg ryzyka: **najpierw** schemat walidacji (Pydantic) i strategia dla rekordów wadliwych (odrzuć vs napraw) — to jest decyzja architektoniczna, którą trzeba rozstrzygnąć pod nadzorem, zanim pętla zacznie działać sama. Potem parser, potem eksport, na końcu polish/raport.
3. Pusty `progress.txt` — pamięć sesyjna na czas trwania tego sprintu, kasowana po zakończeniu.
4. `ralph-once.sh` uruchamiany pojedynczo:
   - Czyta `PRD.json` + `progress.txt`.
   - Znajduje pierwsze nieukończone zadanie, implementuje TYLKO je.
   - Uruchamia feedback loops (pytest/mypy/ruff) — commit blokowany, jeśli coś nie przechodzi.
   - Commituje, aktualizuje `progress.txt`.
5. Po każdej iteracji: przegląd diffa i commita, zanim uruchomię kolejną — to jest sedno HITL, uczysz się, jak pętla się zachowuje, zanim oddasz jej stery.
6. Dopiero gdy kilka iteracji z rzędu zachowuje się zgodnie z oczekiwaniami → przejście do `afk-ralph.sh` w Docker sandboksie (`docker sandbox run claude`), z limitem iteracji.

## Następny krok

Gdy ten zarys zaakceptowany — przygotowanie gotowego promptu startowego do wklejenia w nowej sesji Claude Code (plan mode), obejmującego kroki 1-6 powyżej.
