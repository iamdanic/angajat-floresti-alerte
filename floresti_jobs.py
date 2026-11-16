#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitorizare joburi noi in raionul Floresti (angajat.md) -> notificare Telegram.

Foloseste doar biblioteca standard Python (nu necesita pip install).
Rulat automat de GitHub Actions la fiecare 30 de minute.

Variante de rulare locala:
    python floresti_jobs.py --dry-run   # arata joburile noi, nu trimite nimic
    python floresti_jobs.py --test      # trimite un mesaj de test pe Telegram
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

# --------------------------------------------------------------------------
# Configurare
# --------------------------------------------------------------------------
API_URL = "https://api.angajat.md/Search/GetJobOffers"

# Raionul Floresti, luat din GET https://api.angajat.md/api/Lookup/GetParentRegions
REGION_ID = "69a5b001-6152-4734-b2b3-d70bf923defe"
REGION_NAME = "FLORESTI"

BASE_URL = "https://angajat.md/jobPosition/"
PAGE_SIZE = 500
MAX_OFFSET = 5000  # protectie impotriva unui eventual loop infinit
SEND_DELAY = 0.4   # secunde intre mesaje (limitele Telegram)

STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "state", "seen.json"
)
USER_AGENT = "floresti-job-alert/1.0"


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def post_json(url, payload, timeout=60):
    """POST JSON, intoarce dict-ul raspuns."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def telegram_api(method, payload):
    """Apel la API-ul Telegram; ridica exceptie daca nu reuseste."""
    url = "https://api.telegram.org/bot{}/{}".format(
        os.environ["TELEGRAM_BOT_TOKEN"].strip(), method
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError("Telegram HTTP {}: {}".format(exc.code, detail))

    if not body.get("ok"):
        raise RuntimeError(
            "Telegram a refuzat mesajul: {}".format(
                body.get("description", "fara detalii")
            )
        )
    return body


# --------------------------------------------------------------------------
# Preluare date de pe angajat.md
# --------------------------------------------------------------------------
def fetch_jobs():
    """Toate ofertele active din raionul Floresti (paginare dupa offset)."""
    jobs = []
    offset = 0
    while True:
        payload = {
            "pageFrom": offset,
            "pageSize": PAGE_SIZE,
            "elasticFilters": [
                {"elasticFilterType": 0, "key": "status", "values": [1]},
                {
                    "elasticFilterType": 0,
                    "key": "regionId",
                    "values": [REGION_ID],
                },
            ],
        }
        data = post_json(API_URL, payload)
        batch = data.get("results") or []
        jobs.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > MAX_OFFSET:
            break

    # Verificare pe client, ca sa nu iasa vreun job din alt raion.
    return [
        j
        for j in jobs
        if str(j.get("regionId") or "").upper() == REGION_ID.upper()
        or str(j.get("regionNameRo") or "").strip().upper() == REGION_NAME
    ]


# --------------------------------------------------------------------------
# Stare (joburile deja anuntate)
# --------------------------------------------------------------------------
def load_state():
    """Intoarce setul de id-uri deja vazute, sau None daca nu exista inca."""
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return set(data.get("seen") or [])


def save_state(seen_ids):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    payload = {
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "region": REGION_NAME,
        "seen": sorted(seen_ids),
    }
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


# --------------------------------------------------------------------------
# Formatare mesaj
# --------------------------------------------------------------------------
def escape_html(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def job_link(job):
    link = job.get("jobOfferLink")
    if link:
        return str(link)
    return BASE_URL + str(job.get("id") or "")


def format_salary(job):
    """Replica logicii de afisare de pe site (JobOfferService)."""
    minimum = job.get("minSalary") or 0
    if minimum > 0:
        return "{:,.0f} MDL".format(minimum).replace(",", " ")
    if job.get("byAgreement"):
        return "la negociere"
    return "negociabil"


def build_message(job):
    title = escape_html(job.get("occupationName") or "Fara titlu")
    lines = ["🆕 <b>Job nou in Floresti</b>", "", "<b>{}</b>".format(title)]

    company = job.get("companyName")
    if company:
        lines.append("🏢 {}".format(escape_html(company)))

    place = ", ".join(
        str(p).strip()
        for p in (job.get("childRegionNameRo"), job.get("regionNameRo"))
        if p and str(p).strip()
    )
    if place:
        lines.append("📍 {}".format(escape_html(place)))

    salary = format_salary(job)
    if salary:
        lines.append("💰 {}".format(escape_html(salary)))

    count = job.get("numberOfJobs") or 0
    if count > 1:
        lines.append("👥 {} posturi".format(count))

    published = str(job.get("publishedDate") or "")[:10]
    if published:
        lines.append("📅 Publicat: {}".format(escape_html(published)))

    external = job.get("externalSystemName")
    if external:
        lines.append("🔗 Sursa: {}".format(escape_html(external)))

    lines.append("")
    lines.append("👉 {}".format(escape_html(job_link(job))))
    return "\n".join(lines)


def build_report(total_jobs, new_count):
    """Raportul zilnic - se trimite mereu, chiar daca nu e nimic nou."""
    date_str = time.strftime("%d.%m.%Y", time.gmtime())
    lines = ["📋 <b>Raport zilic Floresti</b> — {}".format(escape_html(date_str)), ""]
    if new_count == 0:
        lines.append("❌ Astazi nu au aparut joburi noi.")
    else:
        lines.append(
            "🆕 <b>{} joburi noi</b> astazi.".format(new_count)
        )
    lines.append("Acum sunt <b>{}</b> de joburi in zona.".format(total_jobs))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Rulare
# --------------------------------------------------------------------------
def main():
    # Consola Windows are adesea cp1252; nu vrem sa pice la afisarea emoji.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    dry_run = "--dry-run" in sys.argv
    test_only = "--test" in sys.argv

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if test_only:
        if not token or not chat_id:
            print("EROARE: lipsesc TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID.",
                  file=sys.stderr)
            return 1
        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "🧪 Test reusit - alertele de joburi din Floresti "
                "functioneaza.",
                "disable_web_page_preview": True,
            },
        )
        print("Mesaj de test trimis.")
        return 0

    if not dry_run and (not token or not chat_id):
        print(
            "EROARE: lipsesc TELEGRAM_BOT_TOKEN sau TELEGRAM_CHAT_ID.",
            file=sys.stderr,
        )
        return 1

    jobs = fetch_jobs()
    print("Joburi gasite in Floresti: {}".format(len(jobs)))

    seen = load_state()

    # Prima rulare: nu trimitem tot istoricul, doar semnalizam startul.
    if seen is None:
        current = {str(j["id"]) for j in jobs if j.get("id")}
        print("Prima rulare - {} joburi in zona.".format(len(current)))
        if dry_run:
            print("Mod dry-run: nu s-a salvat si nu s-a trimis nimic.")
            return 0
        save_state(current)
        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": "✅ Monitorizare pornita pentru <b>Floresti</b>.\n"
                "Acum sunt <b>{}</b> de joburi in zona. "
                "Iti scriu aici cand apare ceva nou.".format(len(current)),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        print("Mesaj de confirmare trimis.")
        return 0

    new_jobs = [j for j in jobs if str(j.get("id") or "") not in seen]
    # Cele mai noi primele.
    new_jobs.sort(key=lambda j: str(j.get("publishedDate") or ""), reverse=True)
    print("Joburi noi de anuntat: {}".format(len(new_jobs)))

    report = build_report(len(jobs), len(new_jobs))

    if dry_run:
        print("=" * 60)
        print(report)
        for job in new_jobs:
            print("-" * 60)
            print(build_message(job))
        print("Mod dry-run: nu s-a trimis si nu s-a salvat nimic.")
        return 0

    # Raportul se trimite MEREU, chiar si cand nu e nimic nou.
    telegram_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": report,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )
    print("Raport trimis.")

    for job in new_jobs:
        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": build_message(job),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        # Marcam vazut imediat dupa trimitere, ca o eroare ulterioara
        # sa nu duca la re-trimiterea mesajelor deja livrate.
        seen.add(str(job["id"]))
        save_state(seen)
        time.sleep(SEND_DELAY)
        print("Trimis: {}".format(job.get("occupationName")))

    return 0


if __name__ == "__main__":
    sys.exit(main())
