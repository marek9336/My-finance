# My-finance

Ahoj! 👋

Níže je návrh, jak může tvoje aplikace pro správu financí vypadat tak, aby byla:
- **maximálně flexibilní** (všechno nastavitelné),
- **moderní** (grafy, dashboard, scénáře),
- **self-hosted** (běh doma i na serveru přes web),
- **použitelná dlouhodobě** (historie změn cen, predikce, dluhy, projekty, sdílené platby).

Aktuální doplněné požadavky:
- Finální nasazení přes Docker na TrueNAS (až v poslední fázi).
- OCR import výpisů (banka, krypto burzy, trading) + chytré rozpoznání transakcí.
- Volitelný AI asistent přes ChatGPT API pro vyhodnocení financí a pomoc se zařazením.
- Základní CZ daňový modul (přiznání k dani z příjmů, daň z nemovitosti).
- Pojištění auta/nemovitosti s historií cen a predikcí zdražení.
- Garáž modul: upozornění na výměnu oleje, STK, brzdy (datum + stav km).
- Evidence hodnoty domu + provázání s pojištěním a náklady (elektřina apod.).
- Upozornění na roční platby v aplikaci i synchronizace do Google Kalendáře.
- Lokalizace minimálně CZ + EN a tooltipy u méně jasných voleb.
- Home Assistant plugin až v úplně závěrečné fázi.

## 1) Cíle aplikace

- Evidovat příjmy/výdaje a majetek napříč účty, investicemi a hotovostí.
- Spravovat **pravidelné platby** (denní/týdenní/měsíční/roční).
- Udržet **historii změn částek** (změna platí jen do budoucna).
- Evidovat **projekty** (auto, IT infrastruktura, hobby…) a jejich celkové náklady.
- Evidovat **dluhy/půjčky** + stav splácení.
- Evidovat **sdílené předplatné** s checkboxem „zaplaceno tento měsíc“.
- Napojit tržní data (krypto/akcie/FX) a zobrazit vývoj portfolia.
- Umět dělat **predikce** (konzervativní / realistický / agresivní scénář + vlastní %).
- Spravovat **majetek domácnosti** (dům/byt, auto, motorka) včetně provozních nákladů.
- Hlídání **servisních termínů** (olej, STK, destičky, pojištění) podle data i km.
- Posílat **notifikace ročních plateb** do interního kalendáře i Google Kalendáře.

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

### E) Garáž a mobilita
- Vozidla: auto/motorka (VIN/SPZ, značka/model, datum pořízení, aktuální km).
- Servisní úkony: olej, filtry, destičky, kotouče, pneu, rozvody.
- Každý servis: datum, stav km, cena, poznámka, přílohy (faktura).
- Upozornění: časová (např. 1 rok) i kilometrová (např. +10 000 km od poslední výměny).
- STK a pojištění: termíny, částka, automatické vytvoření roční připomínky.

### F) Nemovitosti, pojištění a energie
- Nemovitost: adresa, odhadní hodnota, pořizovací cena, typ (dům/byt).
- Provázání s pojištěním: domácnost/nemovitost, historie plateb, predikce navýšení.
- Náklady na provoz: elektřina, plyn, voda, internet, fond oprav.
- Roční souhrn a projekce budoucích nákladů.

### G) Události a sezónní náklady
- Narozeniny, svátky, Vánoce, Valentýn, neplánované výdaje.
- Roční porovnání a predikce „očekávaných jednorázových nákladů“.

### H) Dluhy a mikroobchody
- Evidence dluhu (kdo komu, kolik, splatnost, stav).
- Aukro/Bazoš drobné obchody (nákup/prodej).
- Sdílené služby: checkbox každý měsíc „rodina zaplatila“ + historie.

### I) OCR, AI a daně (CZ)
- OCR import PDF/fotek výpisů a potvrzení plateb.
- Automatická klasifikace transakcí + návrhy kategorií.
- Volitelná AI vrstva (ChatGPT API) pro kontrolu rozpočtu a doporučení.
- Základní evidence daní (daň z příjmů, daň z nemovitosti, termíny podání/úhrad).

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
- `vehicles`
- `vehicle_services`
- `vehicle_service_rules`
- `properties`
- `property_costs`
- `insurances`
- `insurance_premiums`
- `ocr_documents`
- `ocr_extractions`
- `ai_classification_logs`
- `tax_obligations`
- `tax_payments`
- `calendar_integrations`
- `notification_rules`
- `notification_deliveries`

## 4) Predikce (jak to udělat prakticky)

### Základní přístup (rychlé a pochopitelné)
1. Predikce cashflow z pravidelných příjmů a výdajů.
2. Predikce investic přes scénáře ročního růstu (např. 5 %, 12 %, 25 %).
3. Simulace 12–120 měsíců dopředu.

### Pokročilejší přístup (později)
- Monte Carlo simulace (náhodné rozložení výnosů).
- Volatilita podle historických dat (hlavně krypto).
- Více scénářů inflace a kurzového rizika.

## 5) UI/UX návrh

- **Dashboard**: čisté karty + grafy (majetek, cashflow, dluhy, investice).
- **Timeline**: historie plateb a změn cen.
- **Kalendář**: nadcházející platby a sezónní události.
- **Kalendář+**: servisní termíny (STK/olej), pojištění, daňové termíny.
- **Scénáře**: slider/field na % výnosu a horizont (1/3/5/10 let).
- **Dark/Light mode**, přizpůsobitelný layout widgetů.
- **Tooltipy** u všech pokročilých voleb.
- **Lokalizace CZ/EN** (i popisy, validace a nápovědy).

## 6) Technologie pro self-hosting

Doporučený stack:
- Frontend: **Next.js + TypeScript + Tailwind + shadcn/ui + Recharts**
- Backend: **NestJS** nebo **FastAPI**
- Databáze: **PostgreSQL**
- Background jobs: **Redis + worker** (např. aktualizace kurzů)
- Nasazení: **Docker Compose**
- Auth: lokální účet + volitelně OAuth
- Notifikace: in-app + e-mail + Google Calendar API (sync připomínek)

## 7) Integrace dat

- Ceny krypto: CoinGecko/CoinMarketCap API.
- Ceny akcií/ETF: Alpha Vantage / Twelve Data / Polygon (dle budgetu).
- FX kurzy: ECB nebo exchangerate.host.
- Import CSV z banky/burzy.
- OCR pipeline: Tesseract / cloud OCR dle přesnosti a nákladů.
- Kalendář: Google Calendar API (vytváření/aktualizace ročních událostí).

> Poznámka: API limity, caching a fallback jsou důležité, aby appka fungovala stabilně.

## 8) Roadmapa po etapách

### Etapa 1 — MVP (2–4 týdny)
- Účty, transakce, kategorie, pravidelné platby.
- Základní dashboard a měsíční přehled.
- Historie změn částek u opakovaných plateb.

### Etapa 2 — Investice + projekty + majetek
- Portfolio, ruční nákupy/prodeje, jednoduché grafy.
- Projekty (auto/PC/IT) a sumáře nákladů.
- Nemovitost, pojištění a provozní náklady (elektřina atd.).

### Etapa 3 — Predikce + upozornění
- Scénáře vývoje cashflow a investic.
- Porovnání scénářů + export do PDF/CSV.
- Upozornění na roční platby, STK, servisní intervaly (datum + km).
- Google Calendar synchronizace.

### Etapa 4 — OCR + AI + daně
- Dluhy, sdílené předplatné, sezónní rozpočty.
- Automatické kurzy aktiv a pokročilé simulace.
- OCR import výpisů + automatické párování transakcí.
- Volitelný ChatGPT API asistent.
- Základní CZ daňové povinnosti a termíny.

### Etapa 5 — Produkční nasazení
- Hardening, zálohování, monitoring.
- Docker deployment na TrueNAS.

### Etapa 6 — Integrace Home Assistant (až nakonec)
- Plugin/integrace pro Home Assistant (notifikace, vybrané entity, automatizace).

## 9) Co bych doporučil upravit hned teď

- Začni s **MVP**, ne se „vším najednou“.
- Definuj si 5–10 klíčových obrazovek, které chceš používat každý den.
- U predikcí drž nejdřív jednoduchý model (fixní %), ať je to pochopitelné.
- Vyřeš důsledně práci s historií (`valid_from/valid_to`) — to je kritická část.
- U servisů vozidel drž i historii km při úkonu, nejen datum.
- U kalendářových upozornění řeš idempotenci (nezakládat duplicitní eventy v Google Kalendáři).

## 10) Další krok (pokud chceš)

Můžeme navázat konkrétně:
1. připravím přesný návrh DB tabulek,
2. navrhnu API endpointy,
3. sestavím první sprint backlog (user stories),
4. můžeme rovnou scaffoldnout projekt (frontend + backend + docker).

Detailní návrh pro garáž/nemovitosti/notifikace/Google Kalendář:
- `docs/db-schema-garage-properties-notifications.md`
- `docs/api-contract-garage-properties-notifications.md`
- `backend/` (FastAPI kostra endpointů + validace + testy)
- `docs/translation-contributing.md` (jak přidat vlastní překlad přes Git/PR)

Nastavení (kalendář, registrace, jazyk) je navrženo přes GUI v aplikaci:
- backend endpointy `GET/PUT /api/v1/settings/app`
- i18n endpointy `GET /api/v1/i18n/locales`, `GET /api/v1/i18n/{locale}`, `PUT /api/v1/i18n/{locale}/custom`, `POST /api/v1/i18n/{locale}/custom/publish`
- GUI stránky `GET /ui/settings`, `GET /ui/translations`, `GET /ui/backup`, `GET /ui/get-started`

Start testování financí:
- otevři `GET /ui/get-started`
- nastav jazyk, timezone, vzhled (light/dark/system)
- volitelně obnov data přes restore JSON
- registrace / login
- po přihlášení automatický přechod na `GET /ui/dashboard` (účty + transakce)

Jednoduchá migrace na jiný stroj (backup/restore):
- export: `GET /api/v1/admin/backup/download` (JSON soubor)
- import: `POST /api/v1/admin/backup/import-file` (upload JSON)
- stejné funkce jsou dostupné i přes GUI stránku Backup & Restore
- automatické zálohy: nastavitelné v GUI Settings (`autoBackupEnabled`, interval, retence)

User-friendly instalace:
- `install.ps1` (automaticky vytvoří venv a stáhne závislosti; volitelně `-UsePostgres` spustí SQL migrace)
- `docker-compose.yml` (spuštění API přes Docker bez ruční instalace)
- po změnách kódu používej `docker compose up --build`, aby se načetla nová image

Persistence režimy backendu:
- `STORAGE_BACKEND=memory` (výchozí, rychlý vývoj)
- `STORAGE_BACKEND=postgres` + `DATABASE_URL=...` (perzistentní data přes PostgreSQL)
