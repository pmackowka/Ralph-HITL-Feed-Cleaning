#!/bin/bash

claude --permission-mode acceptEdits "@PRD.json @progress.txt @CLAUDE.md \
1. Przeczytaj PRD.json i progress.txt. \
2. Znajdź w PRD.json pierwsze zadanie z passes: false (w kolejności z listy) i zaimplementuj TYLKO je — nie ruszaj plików wykluczonych (pole files.exclude) ani plików należących do innych zadań. \
3. Przed commitem uruchom WSZYSTKIE feedback loops i upewnij się, że przechodzą: uv run pytest, uv run mypy src, uv run ruff check . — jeśli którykolwiek nie przechodzi, napraw i uruchom ponownie. NIE commituj czerwonego stanu. \
4. Sprawdź, że wszystkie edge_cases wymienione w zadaniu mają pokrycie testowe. \
5. Zacommituj zmiany razem z aktualizacją passes: true dla ukończonego zadania w PRD.json. \
6. Dopisz do progress.txt krótką notatkę: co zrobiłeś, jakie decyzje podjąłeś, co zostało do dokończenia (jeśli coś). \
ZRÓB TYLKO JEDNO ZADANIE NA RAZ. Nie zaczynaj kolejnego zadania z listy."
