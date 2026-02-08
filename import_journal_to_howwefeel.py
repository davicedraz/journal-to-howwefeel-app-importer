#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser


PORTUGUESE_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

WEEKDAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def load_moods_file(path):
    moods = []
    if not path or not os.path.exists(path):
        return moods
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                moods.append(line)
    except OSError:
        return moods
    return moods


class JournalHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_body = False
        self.in_page_header = False
        self.in_title = False
        self.text_parts = []
        self.page_header = ""
        self.title = ""
        self._stack = []

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.in_body = True
        if not self.in_body:
            return

        attr_map = {k: v for k, v in attrs}
        if tag == "div" and attr_map.get("class") == "pageHeader":
            self.in_page_header = True
        if tag == "div" and attr_map.get("class") == "title":
            self.in_title = True

        if tag in ("p", "li", "br"):
            self.text_parts.append("\n")

        self._stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False
        if tag == "div":
            if self.in_page_header:
                self.in_page_header = False
            if self.in_title:
                self.in_title = False
        if self._stack:
            self._stack.pop()

    def handle_data(self, data):
        if not self.in_body:
            return
        text = html.unescape(data)
        if self.in_page_header:
            self.page_header += text
        elif self.in_title:
            self.title += text
        else:
            self.text_parts.append(text)


def parse_date_from_header(header_text):
    header_text = header_text.strip().lower()
    match = re.search(r"(\d{1,2}) de ([a-zçã]+) de (\d{4})", header_text)
    if not match:
        return None
    day = int(match.group(1))
    month_name = match.group(2).replace("ç", "c")
    month = PORTUGUESE_MONTHS.get(month_name)
    if not month:
        return None
    year = int(match.group(3))
    return dt.date(year, month, day)


def format_date_for_csv(date_obj, time_str):
    time_str = time_str.strip()
    time_obj = dt.datetime.strptime(time_str, "%I:%M %p").time()
    dt_obj = dt.datetime.combine(date_obj, time_obj)
    weekday = WEEKDAYS_EN[dt_obj.weekday()]
    return dt_obj.strftime(f"%Y {weekday} %b %-d %I:%M %p")


def normalize_text(text):
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def extract_takeaway(text):
    sentences = split_sentences(text)
    for s in sentences:
        if re.search(r"\b(quero|pretendo|vou|preciso|devo|decidi|planejo)\b", s, re.IGNORECASE):
            return s
    return ""


def load_env(paths):
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("\ufeff"):
                        line = line.lstrip("\ufeff")
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[len("export ") :].strip()
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if not key:
                        continue
                    if os.environ.get(key, "").strip() == "":
                        os.environ[key] = value
        except OSError:
            continue


def load_existing_moods(csv_path):
    moods = set()
    if not os.path.exists(csv_path):
        return moods
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if not headers:
            return moods
        for row in reader:
            if len(row) < 2:
                continue
            mood_field = row[1].strip()
            if not mood_field:
                continue
            for mood in mood_field.split(";"):
                mood = mood.strip()
                if mood:
                    moods.add(mood)
    return moods


def build_mood_pool(existing_moods, extra_moods=None):
    pool = set(existing_moods)
    if extra_moods:
        for mood in extra_moods:
            pool.add(mood)
    return pool


def choose_mood(text, mood_pool, allow_fallback=True):
    text_l = text.lower()
    mood_preferences = []

    if re.search(r"\b(ansios|ansiedade|preocupad|nervos)\b", text_l):
        mood_preferences.append(["Anxious", "Concerned", "Uneasy"])
    if re.search(r"\b(depress|morrer|suicid|hopeless|sem raz[aã]o)\b", text_l):
        mood_preferences.append(["Depressed", "Hopeless", "Miserable", "Down"])
    if re.search(r"\b(cansad|exaust|fatig)\b", text_l):
        mood_preferences.append(["Exhausted", "Tired", "Fatigued"])
    if re.search(r"\b(preso|pris[aã]o|trancad)\b", text_l):
        mood_preferences.append(["Trapped"])
    if re.search(r"\b(frustr|raiva|irrit|culpa|vergonh)\b", text_l):
        mood_preferences.append(["Frustrated", "Peeved", "Guilty", "Ashamed"])
    if re.search(r"\b(inspir|motivad|orgulh|confian)\b", text_l):
        mood_preferences.append(["Inspired", "Motivated", "Proud"])
    if re.search(r"\b(grat|feliz|bem|esperan|otimi)\b", text_l):
        mood_preferences.append(["Grateful", "Hopeful", "Optimistic", "Good", "Content"])

    chosen = []
    for prefs in mood_preferences:
        for mood in prefs:
            if mood in mood_pool and mood not in chosen:
                chosen.append(mood)
                break
        if len(chosen) >= 2:
            break

    if allow_fallback and not chosen:
        for fallback in ["Thoughtful", "Mellow", "Calm", "Neutral", "Meh", "Balanced"]:
            if fallback in mood_pool:
                chosen = [fallback]
                break

    return ";".join(chosen) if chosen else ""


def llm_choose_mood(text, existing_moods, model, api_key, max_moods=2, debug_label=None, debug=False):
    if not api_key:
        return ""
    if not existing_moods:
        return ""

    moods_sorted = sorted(existing_moods)
    moods_lower_map = {m.lower(): m for m in moods_sorted}

    snippet = text[:2000]
    prompt = (
        "Escolha até {max_moods} moods da lista e responda APENAS com os nomes "
        "separados por ';'. Se nenhum servir, responda vazio.\n\n"
        "Lista de moods:\n{moods}\n\n"
        "Texto:\n{snippet}\n"
    ).format(max_moods=max_moods, moods=", ".join(moods_sorted), snippet=snippet)

    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                ],
            }
        ],
        "temperature": 0.2,
        "max_output_tokens": 50,
    }

    if debug:
        label = f"[LLM] {debug_label}" if debug_label else "[LLM]"
        print(f"{label} prompt:\\n{prompt}\\n")

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return ""

    raw_text = ""
    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    raw_text += content.get("text", "")

    raw_text = raw_text.strip()
    if debug:
        label = f"[LLM] {debug_label}" if debug_label else "[LLM]"
        print(f"{label} output: {raw_text}\\n")
    if not raw_text:
        return ""

    chosen = []
    for part in raw_text.split(";"):
        mood = part.strip()
        if not mood:
            continue
        normalized = moods_lower_map.get(mood.lower())
        if normalized and normalized not in chosen:
            chosen.append(normalized)
        if len(chosen) >= max_moods:
            break

    return ";".join(chosen)


def parse_existing_keys(csv_path):
    keys = set()
    if not os.path.exists(csv_path):
        return keys
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if not headers:
            return keys
        for row in reader:
            if len(row) < 1:
                continue
            date_str = row[0].strip()
            notes = (row[15].strip() if len(row) > 15 else "")
            reflections = (row[16].strip() if len(row) > 16 else "")
            key = (date_str[:10], notes[:40], reflections[:40])
            keys.add(key)
    return keys


def process_html_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    parser = JournalHTMLParser()
    parser.feed(content)

    body_text = " ".join(parser.text_parts)
    body_text = re.sub(r"\s*•\s*", " - ", body_text)
    body_text = normalize_text(body_text)

    title = normalize_text(parser.title)
    date_obj = parse_date_from_header(parser.page_header)

    return date_obj, title, body_text


def build_row(date_str, mood, notes, reflections, takeaways):
    return [
        date_str,
        mood,
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        notes,
        reflections,
        takeaways,
    ]


def main():
    parser = argparse.ArgumentParser(description="Importa registros do Diário para HowWeFeel CSV.")
    parser.add_argument("--csv", default="HowWeFeelEmotions.example.csv", help="Caminho do CSV de saída/entrada.")
    parser.add_argument("--entries", default="AppleJournalEntries/Entries", help="Diretório dos HTMLs do Diário.")
    parser.add_argument("--time", default="12:00 PM", help="Horário padrão para o campo Date (ex.: 12:00 PM).")
    parser.add_argument("--dry-run", action="store_true", help="Não escreve no CSV, apenas mostra resumo.")
    parser.add_argument("--force", action="store_true", help="Não tenta deduplicar entradas.")
    parser.add_argument("--llm-model", default="gpt-4o-mini", help="Modelo OpenAI para fallback de Mood.")
    parser.add_argument("--llm-off", action="store_true", help="Desativa fallback com LLM.")
    parser.add_argument("--llm-debug", action="store_true", help="Mostra prompt e resposta da LLM.")
    parser.add_argument("--moods-file", default="moods.txt", help="Arquivo com moods (um por linha).")
    args = parser.parse_args()

    csv_path = args.csv
    entries_dir = args.entries
    script_dir = os.path.dirname(os.path.abspath(__file__))
    load_env([os.path.join(script_dir, ".env"), ".env"])

    existing_moods = load_existing_moods(csv_path)
    if not existing_moods:
        print("Não encontrei moods existentes no CSV. Verifique o arquivo.")
        return
    extra_moods = load_moods_file(os.path.join(script_dir, args.moods_file))
    mood_pool = build_mood_pool(existing_moods, extra_moods=extra_moods)

    existing_keys = parse_existing_keys(csv_path)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not args.llm_off and not api_key:
        print("OPENAI_API_KEY não encontrado; fallback com LLM será ignorado.")

    new_rows = []
    for filename in sorted(os.listdir(entries_dir)):
        if not filename.endswith(".html"):
            continue
        path = os.path.join(entries_dir, filename)
        date_obj, title, body = process_html_file(path)
        if not date_obj or not body:
            continue

        date_str = format_date_for_csv(date_obj, args.time)
        notes = title if title else (split_sentences(body)[0] if split_sentences(body) else body)
        reflections = body
        takeaways = extract_takeaway(body)

        mood = choose_mood(f"{title} {body}", mood_pool, allow_fallback=args.llm_off)
        if not mood and not args.llm_off:
            mood = llm_choose_mood(
                f"{title} {body}",
                mood_pool,
                args.llm_model,
                api_key,
                debug_label=filename,
                debug=args.llm_debug,
            )

        key = (date_str[:10], notes[:40], reflections[:40])
        if not args.force and key in existing_keys:
            continue

        new_rows.append(build_row(date_str, mood, notes, reflections, takeaways))

    if args.dry_run:
        print(f"Novas linhas: {len(new_rows)}")
        return

    if not os.path.exists(csv_path):
        print("CSV não encontrado. Crie/posicione o arquivo e rode novamente.")
        return

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in new_rows:
            writer.writerow(row)

    print(f"Linhas adicionadas: {len(new_rows)}")


if __name__ == "__main__":
    main()
