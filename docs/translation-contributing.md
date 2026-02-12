# Translation Contribution Guide

This project supports community translations through Git.

## How to add a new language

1. Create a new file in `i18n/locales/`:
   - Example: `i18n/locales/de.json`
2. Copy keys from `i18n/locales/en.json`.
3. Translate values only.
4. Open a pull request with your changes.

## Rules

- Keep all keys in English (`settings.calendar`, `auth.login`, ...).
- Do not remove existing keys.
- Use UTF-8 JSON files.
- Keep wording short and UI-friendly.

## Optional custom override

For local/private overrides, add files to `i18n/custom/`.
Example: `i18n/custom/en.private.json`.

If you want to share the custom translation with the project, move it to `i18n/locales/` and open a PR.
