# Praca z projektem — scenariusze dzień po dniu

Ten plik to instrukcje obsługi gotowego narzędzia `feed-cleaner` (nie pętli
Ralpha — to opisuje `README.md`). Format: komenda, potem krótkie wyjaśnienie.

## Skąd się bierze co — drzewko

```
data/raw/
├── feed.csv                    # wejście: syntetyczny "brudny" feed (dane testowe)
└── feed_manifest.json          # STATYCZNY ground truth — ile błędów każdego typu wstrzyknął generator

scripts/
└── generate_synthetic_feed.py  # tworzy OBA pliki powyżej NA RAZ, RAZEM, ZANIM cokolwiek innego się dzieje

src/feed_cleaner/                # sam CLI — czyta feed.csv, produkuje wyniki niżej
├── loader.py / parsing.py / classify.py / export.py / report.py / cli.py

output/                          # DYNAMICZNE — powstaje PO KAŻDYM uruchomieniu CLI, nadpisywane za każdym razem
├── clean.parquet                # zaakceptowane rekordy po naprawie
└── report.json                  # to, co CLI SAMO naliczyło — dopiero TO porównujesz z manifestem
```

**Najważniejsze rozróżnienie:** `feed_manifest.json` powstaje RAZ, PRZED wszystkim,
tylko dla TEGO JEDNEGO syntetycznego pliku testowego — to "odpowiedzi z klucza",
znane z góry, bo błędy sam wstrzyknął generator. Dla prawdziwego feedu od
dostawcy takiego pliku NIGDY nie będzie — nikt nie zna błędów z góry. `report.json`
to coś zupełnie innego: CLI liczy go SAM, za każdym razem od nowa, dla dowolnego
pliku wejściowego, bez wiedzy o "prawidłowej odpowiedzi". Porównanie manifest
↔ report (Scenariusz "mam plik testowy z gotowym manifestem" niżej) działa
wyłącznie dlatego, że mamy oba na raz dla tego samego pliku testowego — to
sposób sprawdzenia, czy CLI się nie myli, nie normalny krok pracy z prawdziwymi
danymi (ten opisuje Scenariusz 1 niżej).

## Scenariusz: nowy plik CSV trafił do `data/raw/` (prawdopodobnie brudny)

1. Sprawdź, że plik faktycznie tam jest i jak się nazywa:
   ```bash
   ls -la data/raw/
   ```

2. Uruchom przetwarzanie:
   ```bash
   uv run feed-cleaner --input data/raw/<nazwa>.csv --output-dir output/
   ```
   Skrót raportu (ile OK/naprawiono/odrzucono) wypisuje się od razu na stdout.

3. Sprawdź kod wyjścia:
   ```bash
   echo $?
   ```
   `0` = sukces, NAWET jeśli część rekordów odrzucona (to normalne). Różne od
   `0` = błąd użycia (np. zły plik wejściowy) — czytaj komunikat na stderr.

4. Obejrzyj pełny raport jakości:
   ```bash
   cat output/report.json
   ```
   `row_counts` — ile OK/repaired/rejected z ilu total. `repaired_reasons` /
   `rejected_reasons` — rozbicie na konkretne powody (patrz `models.py` —
   `Reason` dla pełnej listy nazw).

5. Jeśli `rejected` jest wysoki względem `total` — to sygnał o jakości
   DANYCH wejściowych, nie błąd narzędzia. Zajrzyj do `rejected_reasons`,
   który powód dominuje, i sprawdź źródłowy CSV pod tym kątem.

6. Sprawdź dane wyjściowe:
   ```bash
   uv run python3 -c "
   import pandas as pd
   df = pd.read_parquet('output/clean.parquet')
   print(len(df), 'wierszy')
   print(df.head(10))
   "
   ```
   Liczba wierszy musi się zgadzać z `row_counts.ok + row_counts.repaired`
   z `report.json`. Wartości muszą być już PO naprawie (np. `price` jako
   liczba, nie tekst z walutą).

## Scenariusz: mam plik testowy z gotowym manifestem błędów

Dotyczy danych syntetycznych generowanych przez `scripts/generate_synthetic_feed.py`
— każdy taki plik ma bliźniaczy `*_manifest.json` z policzonymi z góry
błędami (ground truth).

```bash
python3 -c "
import json
m = json.load(open('data/raw/feed_manifest.json'))
r = json.load(open('output/report.json'))
for key in ('row_counts', 'repaired_reasons', 'rejected_reasons'):
    diff = {k: (m[key][k], r[key].get(k)) for k in m[key] if m[key][k] != r[key].get(k)}
    print(key, 'OK' if not diff else f'ROZBIEŻNOŚĆ: {diff}')
"
```
Każda rozbieżność = bug w parserze/klasyfikacji, nie w danych — manifest jest
prawdą, narzędzie ma się do niej dopasować.

## Scenariusz: chcę sprawdzić, że sam kod nie ma regresji

```bash
uv run pytest && uv run mypy src && uv run ruff check .
```
Niezależna weryfikacja własnymi rękami — nie ufaj samemu zielonemu CI/commitowi.

## Scenariusz: coś w wyniku wygląda podejrzanie

1. Znajdź konkretny powód w `rejected_reasons`/`repaired_reasons` w
   `report.json`, który wygląda nie na miejscu.
2. Ręcznie znajdź w źródłowym CSV wiersz, który mógł go wywołać (`grep`/otwórz
   w edytorze).
3. Prześledź go przez pipeline ręcznie w Pythonie:
   ```bash
   uv run python3 -c "
   from feed_cleaner.classify import classify_row
   row = {'sku': '...', 'name': '...', 'price': '...', 'quantity': '...', 'category': '...'}
   print(classify_row(row))
   "
   ```
   Podstaw realne wartości z podejrzanego wiersza — `classify_row` zwraca
   pełny `ClassifiedRow` z wynikiem dla każdego pola osobno, więc widać
   dokładnie, które pole i dlaczego zadecydowało o statusie.
