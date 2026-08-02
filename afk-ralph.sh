#!/bin/bash
set -e

SANDBOX="claude-Ralph-HITL-Feed-Cleaning"
WORKDIR="/Users/p/Documents/dev/Ralph-HITL-Feed-Cleaning"

if [ -z "$1" ]; then
  echo "Użycie: $0 <liczba_iteracji>"
  exit 1
fi

for ((i=1; i<=$1; i++)); do
  echo "--- Iteracja $i/$1 ---"

  result=$(sbx exec -w "$WORKDIR" "$SANDBOX" claude -p "@PRD.json @progress.txt @CLAUDE.md \
1. Przeczytaj PRD.json, progress.txt i CLAUDE.md. \
2. Znajdź w PRD.json pierwsze zadanie z passes: false i zaimplementuj TYLKO je — nie ruszaj plików wykluczonych w polu files.exclude ani plików należących do innych zadań. \
3. Przed commitem uruchom WSZYSTKIE feedback loops: uv run pytest, uv run mypy src, uv run ruff check . — jeśli którykolwiek nie przechodzi, napraw i uruchom ponownie. NIE commituj czerwonego stanu. \
4. Sprawdź, że wszystkie edge_cases zadania mają pokrycie testowe. \
5. Zacommituj zmiany razem z aktualizacją passes: true dla ukończonego zadania w PRD.json. \
6. Dopisz do progress.txt krótką notatkę: co zrobiłeś, jakie decyzje podjąłeś, co zostało do dokończenia (jeśli coś). \
ZRÓB TYLKO JEDNO ZADANIE NA RAZ. \
Jeśli WSZYSTKIE zadania w PRD.json mają już passes: true, nic nie rób i wypisz na końcu dokładnie: <promise>COMPLETE</promise>." < /dev/null)

  echo "$result"

  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    echo "PRD ukończony po $i iteracjach."
    exit 0
  fi
done

echo "Osiągnięto limit iteracji ($1) bez sygnału ukończenia PRD."
