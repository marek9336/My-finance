# My-finance

<<<<<<< ours
My-finance is a self-hosted personal finance web app (FastAPI + PostgreSQL + Docker).
It focuses on:
- user accounts and authentication,
- account/transaction management,
- settings with localization (CZ/EN), timezone, appearance,
- backup/restore,
- reminder-ready architecture for future modules (garage, property, taxes, OCR, AI assistant).

## Current stack
- Backend: FastAPI
- DB: PostgreSQL (or in-memory for development)
- UI: server-hosted HTML/JS pages
- Runtime: Docker Compose

## Quick start (Docker)
1. Install Docker Desktop.
2. From repository root run:
```powershell
docker compose up --build
```
3. Open:
- `http://localhost:8000/`
- API docs: `http://localhost:8000/docs`

`/` automatically redirects:
- to `get-started` when not logged in,
- to `dashboard` when logged in.

## Non-Docker local start
Use:
- `install.ps1` for local setup,
- then run backend from project root.

## Main UI routes
- `GET /ui/get-started`
- `GET /ui/dashboard`
- `GET /ui/settings`

## Backups
- Download backup: `GET /api/v1/admin/backup/download`
- Restore backup file: `POST /api/v1/admin/backup/import-file`
- Run backup now: `POST /api/v1/admin/backup/run-now`

## Project planning
- All unfinished and planned work is tracked in `TODO.md` (local-only, ignored by git).
- Keep `README.md` and `TODO.md` updated together whenever scope changes.
=======
Ahoj! 👋

Níže je aktualizovaný návrh, jak může tvoje aplikace pro správu financí vypadat tak, aby byla:
- **maximálně flexibilní** (všechno nastavitelné),
- **moderní** (grafy, dashboard, scénáře),
- **self-hosted** (běh doma i na serveru přes web),
- **použitelná dlouhodobě** (historie změn cen, predikce, dluhy, projekty, sdílené platby).

Super doplnění — do návrhu jsem zapracoval i:
- finální nasazení přes **Docker na TrueNAS**,
- **OCR + chytré rozpoznání transakcí** z výpisů,
- volitelnou AI analytiku přes **ChatGPT API**,
- základní modul pro **české daně**,
- pojištění auta/nemovitosti s predikcí zdražení,
- **tooltipy** u složitějších nastavení,
- vícejazyčnost s prioritou **čeština + angličtina**.

## 1) Cíle aplikace

- Evidovat příjmy/výdaje a majetek napříč účty, investicemi a hotovostí.
- Spravovat **pravidelné platby** (denní/týdenní/měsíční/roční).
- Udržet **historii změn částek** (změna platí jen do budoucna).
- Evidovat **projekty** (auto, IT infrastruktura, hobby…) a jejich celkové náklady.
- Evidovat **dluhy/půjčky** + stav splácení.
- Evidovat **sdílené předplatné** s checkboxem „zaplaceno tento měsíc“.
- Napojit tržní data (krypto/akcie/FX) a zobrazit vývoj portfolia.
- Umět dělat **predikce** (konzervativní / realistický / agresivní scénář + vlastní %).

## 2) Modulární struktura

### A) Finance (základ)
- Účty: běžný účet, hotovost, společný účet, spoření.
- Kategorie příjmů: mzda, bonus, side hustle.
- Kategorie výdajů: fixní (nájem, pojištění), variabilní (jídlo, benzín), předplatná.
- Měny: CZK/EUR/USD + přepočty dle historického kurzu.

### B) Pravidelné platby
- Frekvence: denní / týdenní / měsíční / roční / vlastní interval.
- Pole `valid_from` a `valid_to` pro verze ceny.
- Příklad: Spotify 159 Kč do 31.12., od 1.1. 199 Kč (historie zůstane).
- Možnost automatického generování očekávaných plateb do kalendáře.

### C) Investice
- Ruční záznam nákupů/prodejů (BTC, ETH, ETF, akcie přes Trading212 apod.).
- Burzy/poskytovatelé jako metadata (Anycoin, Binance, Coinbase…).
- Napojení na ceny aktiv + převod do základní měny.
- Přehled: vklad, aktuální hodnota, zisk/ztráta, alokace portfolia.

### D) Projekty a majetek
- Projekty: auto, PC, domácí síť, hobby.
- Každý náklad se dá přiřadit do projektu.
- Souhrn: pořizovací cena, průběžné náklady, ROI (volitelně).

### E) Události a sezónní náklady
- Narozeniny, svátky, Vánoce, Valentýn, neplánované výdaje.
- Roční porovnání a predikce „očekávaných jednorázových nákladů“.

### F) Dluhy a mikroobchody
- Evidence dluhu (kdo komu, kolik, splatnost, stav).
- Aukro/Bazoš drobné obchody (nákup/prodej).
- Sdílené služby: checkbox každý měsíc „rodina zaplatila“ + historie.

### G) OCR a chytré třídění transakcí
- Import PDF/JPG/PNG výpisů z banky, kryptoburz a trading platforem.
- OCR pipeline: extrakce textu → normalizace → návrh kategorií/transakcí.
- Pravidla + AI klasifikace: „co se děje“ podle textu (např. nákup BTC, poplatek, předplatné).
- Schvalovací režim: aplikace navrhne, uživatel potvrdí/upraví (kvůli přesnosti).

### H) AI asistent (volitelný)
- Napojení přes ChatGPT API pouze pokud uživatel aktivuje a vloží API klíč.
- Funkce: měsíční shrnutí, varování před rozpočtovým rizikem, návrhy na lepší zařazení transakcí.
- Důraz na soukromí: maskování citlivých polí a audit log volání modelu.

### I) Daně (CZ základ)
- Evidovat podklady pro daň z příjmů (fyzická osoba), přehled příjmů/výdajů dle kategorií.
- Evidence podkladů k dani z nemovitosti (nemovitost, sazby, termíny).
- Daňový kalendář: připomínky termínů podání a plateb.
- Odhad budoucí daňové povinnosti podle historie a plánovaných změn.

### J) Pojištění auta a nemovitosti
- Samostatné smlouvy: cena, období, spoluúčast, poskytovatel.
- Historie zdražení pojištění mezi roky.
- Predikce příštího roku (např. konzervativně +5 %, realisticky +10 %, agresivně +20 %).

## 3) Datový model (MVP návrh)

Doporučené entity:
- `users`
- `accounts`
- `transactions`
- `categories`
- `recurring_templates`
- `recurring_template_versions`
- `assets` (krypto, akcie, ETF, FX)
- `positions` (držené pozice)
- `market_prices`
- `projects`
- `project_expenses`
- `debts`
- `shared_subscriptions`
- `shared_subscription_checks`
- `budgets`
- `forecast_scenarios`
- `insurance_policies`
- `insurance_policy_versions`
- `tax_profiles`
- `tax_events`
- `ocr_imports`
- `ocr_extracted_items`
- `ai_classification_suggestions`
- `locales`

## 4) Predikce (jak to udělat prakticky)

### Základní přístup (rychlé a pochopitelné)
1. Predikce cashflow z pravidelných příjmů a výdajů.
2. Predikce investic přes scénáře ročního růstu (např. 5 %, 12 %, 25 %).
3. Simulace 12–120 měsíců dopředu.

### Pokročilejší přístup (později)
- Monte Carlo simulace (náhodné rozložení výnosů).
- Volatilita podle historických dat (hlavně krypto).
- Více scénářů inflace a kurzového rizika.

### Predikce pojištění a daní
- Predikce pojistných smluv z historických navýšení.
- Predikce ročních daňových odvodů dle trendu příjmů a majetku.

## 5) UI/UX návrh

- **Dashboard**: čisté karty + grafy (majetek, cashflow, dluhy, investice).
- **Timeline**: historie plateb a změn cen.
- **Kalendář**: nadcházející platby a sezónní události.
- **Scénáře**: slider/field na % výnosu a horizont (1/3/5/10 let).
- **Dark/Light mode**, přizpůsobitelný layout widgetů.
- **Tooltipy (bubliny s vysvětlivkou)** u každého pokročilého pole.
- Lokalizace UI: výchozí **CZ**, přepínání na **EN**.

## 6) Technologie pro self-hosting

Doporučený stack:
- Frontend: **Next.js + TypeScript + Tailwind + shadcn/ui + Recharts**
- Backend: **NestJS** nebo **FastAPI**
- Databáze: **PostgreSQL**
- Background jobs: **Redis + worker** (např. aktualizace kurzů)
- Nasazení: **Docker Compose**
- Auth: lokální účet + volitelně OAuth
- OCR: **Tesseract** + předzpracování obrazu (OpenCV) nebo cloud OCR provider
- AI vrstva: interní service pro volitelná volání ChatGPT API

### Self-hosting poznámka (TrueNAS)
- Cílové produkční nasazení jako poslední fáze: **Docker na TrueNAS SCALE**.
- Doporučení: oddělené volumes pro DB, zálohy, importy OCR a logy.
- Připravit healthchecke, restart policy a jednoduchý update postup přes compose.

## 7) Integrace dat

- Ceny krypto: CoinGecko/CoinMarketCap API.
- Ceny akcií/ETF: Alpha Vantage / Twelve Data / Polygon (dle budgetu).
- FX kurzy: ECB nebo exchangerate.host.
- Import CSV z banky/burzy.
- OCR import dokumentů: PDF/JPG/PNG + mapování na transakce.

> Poznámka: API limity, caching a fallback jsou důležité, aby appka fungovala stabilně.

## 8) Roadmapa po etapách

### Etapa 1 — MVP (2–4 týdny)
- Účty, transakce, kategorie, pravidelné platby.
- Základní dashboard a měsíční přehled.
- Historie změn částek u opakovaných plateb.

### Etapa 2 — Investice + projekty
- Portfolio, ruční nákupy/prodeje, jednoduché grafy.
- Projekty (auto/PC/IT) a sumáře nákladů.

### Etapa 3 — Predikce
- Scénáře vývoje cashflow a investic.
- Porovnání scénářů + export do PDF/CSV.

### Etapa 4 — Pokročilé funkce
- Dluhy, sdílené předplatné, sezónní rozpočty.
- Automatické kurzy aktiv a pokročilé simulace.

### Etapa 5 — OCR + AI + Daně
- OCR import výpisů a poloautomatické párování transakcí.
- Volitelný ChatGPT asistent pro analýzu a kategorizaci.
- Daňový modul (CZ základ), pojištění a jejich predikce.

### Etapa 6 — Produkční nasazení
- Hardened Docker deployment na TrueNAS.
- Monitoring, alerting, zálohování a disaster recovery postup.

## 9) Co bych doporučil upravit hned teď

- Začni s **MVP**, ne se „vším najednou“.
- Definuj si 5–10 klíčových obrazovek, které chceš používat každý den.
- U predikcí drž nejdřív jednoduchý model (fixní %), ať je to pochopitelné.
- Vyřeš důsledně práci s historií (`valid_from/valid_to`) — to je kritická část.
- OCR a AI dělej „human-in-the-loop“ (nejdřív návrh, pak potvrzení uživatelem).
- Daňový modul drž jako odhadový/plánovací + možnost exportu podkladů pro účetní.

## 10) Další krok (pokud chceš)

Můžeme navázat konkrétně:
1. připravím přesný návrh DB tabulek,
2. navrhnu API endpointy (včetně OCR/AI/tax),
3. sestavím první sprint backlog (user stories),
4. připravím Docker Compose pro lokální vývoj,
5. ve finální fázi uděláme produkční variantu pro TrueNAS.
>>>>>>> theirs
