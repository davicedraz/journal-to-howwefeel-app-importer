# Journal → How We Feel CSV

Scripts and examples to transform iOS [Journal](https://apps.apple.com/us/app/journal/id6447391597) exports into a CSV compatible with [How We Feel](https://howwefeel.org/) import.

This repository **does not contain personal data**: everything was replaced with Lorem ipsum examples.

## What the script does

- Reads HTML files in `AppleJournalEntries/Entries`
- Extracts the date, title, and body text
- Fills columns compatible with the How We Feel CSV
- Preserves the original header/column order
- Deduplicates by default (use `--force` to bypass)
- Uses OpenAI fallback to select `Mood` when needed
- Uses `moods.txt` (one mood per line) as the allowed mood list

## Expected structure (example)

```
Diário/
  AppleJournalEntries/
    Entries/
      2025-10-29.html
      2025-10-31.html
      2025-10-31-2.html
      ...
  HowWeFeelEmotions.example.csv
  import_journal_to_howwefeel.py
  moods.txt
  .env.example
```

## Requirements

- macOS with `python3`
- Exported How We Feel CSV (e.g., `HowWeFeelEmotions.csv`)
- `AppleJournalEntries/` folder at the same root level as the CSV
- (Optional) OpenAI key in a `.env` file

## Quickstart (copy & paste)

### 1) Go to the repository folder

```
cd /path/to/your/repo
```

### 2) (Optional) Set the OpenAI key

```
cat <<'EOF' > .env
OPENAI_API_KEY=YOUR_KEY_HERE
EOF
```

### 3) Run the script

```
python3 import_journal_to_howwefeel.py --csv "HowWeFeelEmotions.csv"
```

Done. `HowWeFeelEmotions.csv` will be updated by appending new rows.

## Useful options

- Dry run (no write):
  ```
  python3 import_journal_to_howwefeel.py --dry-run
  ```
- Disable LLM fallback:
  ```
  python3 import_journal_to_howwefeel.py --llm-off
  ```
- Change OpenAI model:
  ```
  python3 import_journal_to_howwefeel.py --llm-model gpt-4o-mini
  ```
- Custom CSV path:
  ```
  python3 import_journal_to_howwefeel.py --csv "MyFile.csv"
  ```
- Default time for `Date`:
  ```
  python3 import_journal_to_howwefeel.py --time "12:00 PM"
  ```
- LLM debug (prompt + response):
  ```
  python3 import_journal_to_howwefeel.py --llm-debug
  ```

## About `moods.txt`

`moods.txt` is the primary source of valid moods for the LLM. Edit it freely to match what your app accepts.

## Privacy

- `.env` is already in `.gitignore`.
- Replace example files with your real data before running.
- The script looks for `.env` in the script folder and the current folder.
- If `.env` is missing or `OPENAI_API_KEY` is not set, LLM fallback is skipped.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Apple or [How We Feel](https://howwefeel.org/). "Apple" and "How We Feel" are trademarks of their respective owners.

## Language note

This project was designed with Portuguese Journal exports in mind. It works with entries written in any language, and the **date header parsing supports Portuguese, English, Spanish, and French month names**. If your export uses a different locale, adjust the date parsing or month map in the script.

## License

MIT. See `LICENSE`.
