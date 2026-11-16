# Alerte Telegram pentru joburi noi în Florești (angajat.md)

Script care verifică **în fiecare zi la ora 12:00** [angajat.md](https://angajat.md/jobOffers)
pentru **joburi noi în raionul Florești** și îți trimite un **raport zilnic** pe Telegram:

- dacă au apărut joburi noi → raportul zilnic + câte un mesaj pentru fiecare job nou
- dacă **nu** a apărut nimic → primești oricum mesajul
  „❌ Astăzi nu au apărut joburi noi. Acum sunt 57 de joburi în zona."

- Fără login, fără chei de API — folosește API-ul public al site-ului.
- Doar biblioteca standard Python — **nu e nevoie de `pip install`**.
- Rulează în cloud pe **GitHub Actions** (gratuit), nu depinde de calculatorul tău.

---

## 1. Creează botul Telegram (~1 minut)

1. Deschide Telegram și caută **@BotFather**.
2. Trimite `/newbot`.
3. Îți cere un **nume de afișare** (orice, ex. `Alerte Floresti`), apoi un
   **nume de utilizator** care **trebuie să se termine cu `bot`**
   (ex. `floresti_joburi_bot`).
4. BotFather îți dă **token-ul** — arată ca
   `123456789:AAE...xyz`. **Copiază-l**, îl vei folosi la pasul 3.

> Dacă username-ul e deja luat, BotFather îți cere altul. Alege altul.

## 2. Află chat_id-ul

1. **Trimite orice mesaj botului tău** (ex. `salut`) — astfel Telegram știe
   să-ți livreze mesaje.
2. Deschide în browser, înlocuind `<TOKEN>` cu token-ul tău:

   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

3. Caută în răspuns `"chat":{"id":123456789, ...}` — **acel număr este
   `TELEGRAM_CHAT_ID`** (poate fi negativ pentru un grup).

> Alternativă: scrie-mi token-ul aici și îți iau eu chat_id-ul.

## 3. Punerea pe GitHub

În folderul acesta rulează:

```powershell
git init -b main
git add .
git commit -m "Alerte joburi Floresti"
```

Apoi creezi repo-ul pe [github.com/new](https://github.com/new) (poate fi
**private**) și:
```powershell
git remote add origin https://github.com/<user>/angajat-floresti-alerte.git
git push -u origin main
```

## 4. Adaugă cele 2 secrete

În repo: **Settings → Secrets and variables → Actions → New repository secret**

| Nume | Valoare |
|---|---|
| `TELEGRAM_BOT_TOKEN` | token-ul de la BotFather (pasul 1) |
| `TELEGRAM_CHAT_ID` | chat_id-ul din pasul 2 |

## 5. Testează

Tab-ul **Actions → Alerta joburi Floresti → Run workflow → Run workflow**.

La **prima** rulare primești un singur mesaj de confirmare:
> ✅ Monitorizare pornita pentru Floresti. Acum sunt 57 de joburi in zona.

Restul de 57 de joburi existente **nu** se trimit.

**De atunci, în fiecare zi la 12:00** primești raportul. Când **nu** e nimic nou:

```
📋 Raport zilic Floresti — 17.11.2026

❌ Astazi nu au aparut joburi noi.
Acum sunt 57 de joburi in zona.
```

Când **sunt** joburi noi, întâi vine raportul, apoi câte un mesaj per job:

```
📋 Raport zilic Floresti — 17.11.2026

🆕 2 joburi noi astazi.
Acum sunt 57 de joburi in zona.
```

```
🆕 Job nou in Floresti

Lăcătuş auto
🏢 SRL EDIL-AUTONORD
📍 FLOREŞTI, FLOREŞTI
💰 6 000 MDL
📅 Publicat: 2025-10-10

👉 https://angajat.md/jobPosition/4e7e22e2-...
```

---

## Ce monitorizează

**Tot raionul Florești** (57 de joburi la momentul scrierii), adică și orașul
Florești, și satele din raion: Căprioara, Gura Camencii, Ștefănești,
Vertiujeni, Ciripcau, Gvozdova, Bobulești, Mărculești, Cunicea, Prodanesti,
Temeleuți, Cosernița, Japca, Domulgeni, Seirova, Ghindești etc.

Filtrul se face pe server, prin id-ul raionului:

```json
{"elasticFilterType":0, "key":"regionId", "values":["69a5b001-6152-4734-b2b3-d70bf923defe"]}
```

Dacă vrei **doar orașul Florești**, adaugă în `floresti_jobs.py`, în
`fetch_jobs()`, pe linia cu verificarea finală, un filtru suplimentar:

```python
# doar orasul Floresti
if str(j.get("childRegionNameRo") or "").strip().upper() != "FLORESTI":
    continue
```

## Cum schimbi ora

În `.github/workflows/alerte-floresti.yml`:

```yaml
schedule:
  - cron: '0 10 * * *'   # 10:00 UTC = 12:00 ora Moldovei
```

Formatul e `minutul ora * * *` și e în **UTC**. Moldova e UTC+2 iarna,
UTC+3 vara, așa că:

| Vrei ora locală | iarnă (UTC+2) | vara (UTC+3) |
|---|---|---|
| 08:00 | `0 6 * * *` | `0 5 * * *` |
| **12:00** ← acum | `0 10 * * *` | `0 9 * * *` |
| 20:00 | `0 18 * * *` | `0 17 * * *` |

⚠️ **Trecerea la ora de vară** (ultima duminică din martie) face ca
`0 10 * * *` să trimită la 13:00 local. Schimbă `10` cu `9` atunci și pune
`10` înapoi la ultima duminică din octombrie. Restul nu se atinge.

Poți pune și mai des — ex. `0 */6 * * *` = de 4 ori pe zi. GitHub poate
întârzia rularea programată cu câteva minute în zilele aglomerate.

**Contorizare minute GitHub** (repo privat: 2.000 min/lună gratuit):
o rulare pe zi ≈ **30 min/lună**, deci ești departe de limită.

Notificările se pornesc doar pe **branch-ul implicit** (`main`).

## Rulare locală (opțional)

```powershell
python floresti_jobs.py --dry-run   # vezi ce s-ar trimite, nu trimite nimic
python floresti_jobs.py --test      # mesaj de test pe Telegram
python floresti_jobs.py             # rulare reală
```

Pentru rularea reală ai nevoie de variabilele de mediu:

```powershell
$env:TELEGRAM_BOT_TOKEN = "123456789:AAE..."
$env:TELEGRAM_CHAT_ID   = "123456789"
```

## Fișiere

| Fișier | Rol |
|---|---|
| `floresti_jobs.py` | scriptul: interoghează API-ul, compară, trimite raportul |
| `.github/workflows/alerte-floresti.yml` | programarea zilnică la 12:00 + salvarea stării |
| `state/seen.json` | id-urile joburilor deja anunțate (se creează singur) |
| `ia-chat-id.ps1` | îți afișează `TELEGRAM_CHAT_ID` (doar pentru configurare) |
| `verifica-telegram.ps1` | testează tokenul + chat_id-ul (doar pentru configurare) |

## Note

- Joburile preluate de pe **Rabota.md** (marcate cu „Sursa: Rabota.md") trimit
  direct către linkul lor original, nu către angajat.md.
- Dacă API-ul pică sau Telegram-ul refuză un mesaj, rularea eșuează, **starea
  nu se strică** și mesajele nesmise se retrimite la următoarea rulare.
- Datele sunt citite de pe `api.angajat.md` (API-ul public al portalului
  Agenției Naționale pentru Ocuparea Forței de Muncă).
