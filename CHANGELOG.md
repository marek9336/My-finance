# Changelog

Vsechny dulezite zmeny v projektu se zapisuji sem.
Starsi zaznamy se bez vyzvy nemazou, pouze se pridavaji nove.

## [0.0.3] - 2026-02-15
### Added
- Rozsireny plan modulu o nove stranky:
  - Sporeni a investice,
  - Kurzy,
  - Jine investice / sbirky,
  - Sluzby,
  - Poznamky,
  - Garaz,
  - Nemovitosti,
  - Zarizeni,
  - Kalkulacky,
  - Zdravi a Cviceni.
- Specifikace vazeb mezi transakcemi, ucty a moduly (navazovani transakci na entity).
- Pozadavky na centralizaci prekladu a uzivatelske preklady.
- Pozadavky na jednotne UX akce (editace/smazani), autosave s odpoctem a moznosti vratit zmeny.
- Pravidla pro verzovani a vedeni changelogu.

### Changed
- Zprehlednena priorizace roadmapy do vice kroku s jasnym poradi implementace.

## [0.0.4] - 2026-02-15
### Added
- Nove UI routy v backendu pro stranky:
  - `/ui/transactions`
  - `/ui/services`
  - `/ui/savings-investments`
  - `/ui/rates`
  - `/ui/collections`
  - `/ui/garage`
  - `/ui/properties`
  - `/ui/devices`
  - `/ui/notes`
  - `/ui/calculators`
  - `/ui/health`
  - `/ui/exercise`
- Nova stranka `backend/ui/transactions.html` (sprava uctu, transakci, prevodu, kategorii a sekce dle uctu).
- Nove skeleton stranky pro moduly z backlogu:
  - `backend/ui/services.html`
  - `backend/ui/savings-investments.html`
  - `backend/ui/collections.html`
  - `backend/ui/garage.html`
  - `backend/ui/properties.html`
  - `backend/ui/devices.html`
  - `backend/ui/notes.html`
  - `backend/ui/calculators.html`
  - `backend/ui/health.html`
  - `backend/ui/exercise.html`
- Nova stranka `backend/ui/rates.html` (watchlist + manualni snapshot kurzu v local storage).

### Changed
- `backend/ui/dashboard.html` predelano na cisty prehled:
  - rychly financni souhrn,
  - hlavni graf celku + rozbalitelne grafy uctu,
  - statisticke tabulky,
  - sekce zavazku/pohledavek a splatkovych sluzeb,
  - kurzovy snapshot,
  - odstranena operativni cast vytvareni/editace z prehledu.

## [0.2.0] - 2026-02-15
### Added
- Centralizovane i18n klice pro dashboard, transakce, kurzy a spolecne UI texty.
- Upraveny CZ preklad pro nove stranky a navigaci (odstraneni mixu CZ/EN v hlavnim UI).
- Sjednocene menu napric hlavnimi strankami:
  - `/ui/dashboard`
  - `/ui/transactions`
  - `/ui/rates`
  - `/ui/settings`
- Rozsirena navigace v Nastaveni o odkazy na dalsi stranky aplikace.

### Changed
- `backend/ui/dashboard.html`:
  - opravene period filtry grafu (`7d`, `30d`, `90d`, `365d`, `all`),
  - doplnene body transakci do grafu,
  - lepsi vykresleni casove rady podle zvoleneho obdobi.
- `backend/ui/transactions.html`:
  - zachovana operativa pro stabilni financni jadro (ucty, transakce, prevody),
  - jednotny shell a prekladatelne texty.
- `backend/ui/rates.html`:
  - jednotny shell, prekladatelne texty, watchlist + manualni snapshot.
- `backend/ui/settings.html`:
  - doplnena volba sirky layoutu (full/limited) s aplikaci napric strankami,
  - doplnene odkazy na dalsi stranky v horni navigaci.
- `i18n/locales/en.json` a `i18n/locales/cs.json`:
  - doplneny nove klice pro hlavni UI sekce a akce.

## [0.2.1] - 2026-02-15
### Added
- Centralni UI assets:
  - `backend/ui/common.css`
  - `backend/ui/common.js`
- Nove routy pro sdilene UI assets:
  - `/ui/common.css`
  - `/ui/common.js`
- Doplneny i18n klice pro vsechny skeleton stranky a sdileny text.

### Changed
- `backend/ui/dashboard.html`:
  - odstranena horni tlacitka `Refresh` a `Open Transactions`,
  - odhlaseni presunuto pod uzivatelske menu,
  - automaticke obnovovani dat (periodicky + pri navratu do tabu),
  - zachovan a opraven graf s period filtry a body transakci.
- `backend/ui/settings.html`:
  - odstraneny lokalni fallback slovnik, preklad pres centralni i18n,
  - sjednocene menu a vzhled podle sdileneho template.
- `backend/ui/transactions.html`:
  - sjednoceny vzhled a i18n pres centralni assets,
  - zachovane opakovane transakce a inline edit uctu.
- `backend/ui/rates.html`:
  - sjednoceny vzhled a i18n pres centralni assets.
- Sjednocene skeleton stranky (`services`, `savings-investments`, `collections`, `garage`, `properties`, `devices`, `notes`, `calculators`, `health`, `exercise`) na spolecny template.

## [0.2.2] - 2026-02-15
### Changed
- Opraveno nacitani locale souboru v backendu (`backend/app/store.py`) pro lokalni i Docker layout:
  - aplikace nyni korektne nacte plne `i18n/locales/*.json` misto minimalni fallback sady.
- Opravena synchronizace jazyka ve frontend bootstrapu (`backend/ui/common.js`):
  - `mf_lang` se nyni vzdy synchronizuje podle `defaultLocale` ze serveroveho nastaveni.
- Doplnena lokalizace beznych backend error hlasek v shared UI helperu (`backend/ui/common.js`).
- `backend/ui/transactions.html`:
  - odstraneno tlacitko `Refresh`,
  - doplneno automaticke obnovovani dat (periodicky + pri navratu do tabu),
  - preklad smeru transakci v tabulce.
- `backend/ui/dashboard.html`:
  - preklad smeru transakci a typu uctu v tabulkach/kartach.

## [0.2.3] - 2026-02-15
### Changed
- Globalni UI:
  - odstraneno kratke bliknuti anglictiny pri nacitani stranky (`backend/ui/common.css`, `backend/ui/common.js`),
  - sjednocen globalni spacing/padding mezi bloky a formulary napric strankami.
- `backend/ui/dashboard.html`:
  - opravena konstrukce hlavni casove rady (konec grafu odpovida aktualnimu souctu v ramci zvoleneho obdobi),
  - doplnene metriky minima a maxima,
  - doplnen tooltip nad body s detailem transakce,
  - mini-grafy uctu se nyni prepocitaji pri zmene obdobi (`7d/30d/90d/365d/all`).
- `backend/ui/transactions.html`:
  - ucet: pole `Nazev uctu`, `Pocatecni castka`, `Datum zalozeni uctu`,
  - vytvoreni uctu zaklada pocatecni transakci dle castky a data,
  - transakce: pridano denni opakovani (`daily`) a datum transakce,
  - volba `Sledovat...` zkracena na `Sdilena sluzba` + tooltip napovedy,
  - prevod mezi ucty: pridano datum prevodu,
  - sekce Ucty: akce pres ikony `💾` a `❌` s potvrzenim mazani,
  - sekce Transakce: ikona `✏️` otevre modal editace, ulozeni `✅`, zruseni `❌`.
- `i18n/locales/cs.json`, `i18n/locales/en.json`:
  - doplneny nove klice pro graf a rozsirene funkce stranky Transakce.

## [0.3.0] - 2026-02-15
### Added
- Nove backend API pro kurzy:
  - `GET /api/v1/rates` (stav watchlistu + snapshotu),
  - `PUT /api/v1/rates/watchlist` (ulozeni watchlistu),
  - `POST /api/v1/rates/snapshot` (manualni ulozeni ceny),
  - `DELETE /api/v1/rates/watchlist/{symbol}` (odebrani symbolu),
  - `POST /api/v1/rates/refresh` (serverovy refresh cen z verejnych API).
- Datove modely pro rates v `backend/app/schemas.py`.
- Persistence vrstvy pro rates v memory i postgres backendu (`backend/app/persistence.py`).
- Ukladani rates dat do in-memory store (`backend/app/store.py`).

### Changed
- `backend/ui/rates.html`:
  - odstraneno ukladani do `localStorage`,
  - stranka je plne napojena na backend rates API,
  - pridano tlacitko serveroveho refreshe kurzu.
- `backend/ui/dashboard.html`:
  - sekce kurzoveho snapshotu cte data z backend rates API misto `localStorage`.
- Backup/export/import rozsireno o rates watchlist a snapshot data.

## [0.3.1] - 2026-02-15
### Changed
- Navigace:
  - prejmenovano `Transakce` na `Transakce a ucty`.
- Rozpracovane sekce:
  - doplnen indikator `⚠️` s tooltipem o stavu vyvoje na strankach `Sporeni a investice`, `Kurzy`, `Sluzby`,
  - v `Nastaveni` oznaceny jako rozpracovane: `Poskytovatel kalendare`, `Synchronizace kalendare`, `SMTP`.
- `backend/ui/rates.html`:
  - odebrano manualni tlacitko refresh,
  - pridano automaticke obnoveni kurzu po nacteni stranky a periodicky kazdych 15 minut.
- `backend/ui/settings.html`:
  - pridana pole `Vychozi mena` a `Sekundarni mena`,
  - ulozeni men do app settings backendu.
- `backend/ui/rates.html` a `backend/ui/dashboard.html`:
  - prepocet cen do vychozi meny uzivatele,
  - volitelne zobrazeni i v sekundarni mene.
- `backend/app/schemas.py`, `backend/app/store.py`, `backend/app/persistence.py`:
  - rozsireni app settings o `defaultDisplayCurrency` a `secondaryDisplayCurrency`.
