# AGENTS.md

Context for agents to help maintain this repository.

## Project goal

Transform exports from the iOS Journal app into a CSV compatible with import in How We Feel.

## Key files

- `import_journal_to_howwefeel.py`: main script.
- `AppleJournalEntries/Entries/`: exported HTMLs (anonymized examples).
- `HowWeFeelEmotions.example.csv`: example CSV (user should use their real CSV).
- `moods.txt`: list of valid moods (one per line).
- `.env.example`: example `OPENAI_API_KEY`.
- `README.md`: single source of usage and options.

## How the script works (high level)

- Reads HTMLs in `AppleJournalEntries/Entries`.
- Extracts the date from the Portuguese header and the body text.
- Builds rows in the How We Feel CSV format.
- Deduplicates by date + snippets of `Notes` and `Reflections` (use `--force` to bypass).
- Selects `Mood` deterministically; if no match, uses OpenAI fallback.
- The valid mood list comes from `moods.txt` (plus moods already present in the CSV).
- The script reads `.env` in the script folder and the current folder.

## How to run (copy & paste)

```
cd /path/to/your/repo
cat <<'EOF' > .env
OPENAI_API_KEY=YOUR_KEY_HERE
EOF
python3 import_journal_to_howwefeel.py --csv "HowWeFeelEmotions.csv"
```

## Useful options

- `--dry-run`: do not write to the CSV.
- `--llm-off`: disable LLM fallback.
- `--llm-model gpt-4o-mini`: change OpenAI model.
- `--llm-debug`: print LLM prompt and response.
- `--moods-file moods.txt`: specify another mood list.
- `--time "12:00 PM"`: default time for the `Date` field.

## Privacy and public repo

- Do not commit `.env` or real CSV files.
- The repository contains only example data with lorem ipsum.
- If any personal text appears, replace it with lorem ipsum before publishing.

## Maintenance notes

- If `OPENAI_API_KEY not found`, check for BOM in `.env` and confirm the file location.
- If the LLM keeps returning empty, verify the list in `moods.txt`.
- If the example CSV changes, keep the header structure intact.
