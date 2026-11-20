# Life Planner browser prototype

A zero-build, sample-only month calendar and selected-day agenda. The November 2026 calendar starts on Sunday, November 1. Sample plans occupy November 23–29. Click any date to inspect its plans; arrow keys move a focused date by a day or week. “Sample week” returns to the Wednesday sample (or Thursday during/after a proposed move).

Serve from the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory apps/web
```

Open http://127.0.0.1:8765. No package installation, external fonts, images, or API keys are needed.

## Supported interaction

Choose “Wednesday gym → Thursday” or type “Move Wednesday gym to Thursday.” The calendar selects Thursday and shows the proposed meal, clothing preparation and gym session alongside its existing study session. The review lists all three before/after dates and unchanged times. Wednesday still shows the original plans as pending until confirmation. Confirm applies all three local changes; cancel returns to Wednesday without changes. Reset and reload restore the fixture. Unsupported dates, times and other requests receive a clear explanation and cannot change plans.

This is a predefined local interaction, not an AI chat service or an authenticated calendar. State lives only in browser memory. No API calls, browser storage, account or provider integration occur. The Python planning core remains the shared rule authority for future integration; this UI does not claim to call it. Times are sample local wall times, not timezone conversions.

## Design

The user's requested Acloset-inspired direction is interpreted as a sparse, practical calendar: compact toolbar, simple sans serif typography, selected-day circle, small category tiles and a readable agenda. The reference was the calendar screen shown on [Acloset's official website](https://www.acloset.app/). This is an original Life Planner interface; it uses no Acloset branding, imagery or code. The former marketing hero, decorative motifs, summary cards and large assistant panel are removed.

The exact Warm Neutral Tones remain: Azure Mist `#ecf8f8`, Alabaster Grey `#eee4e1`, Almond Cream `#e7d8c9`, Almond Silk `#e6beae`, and Camel `#b2967d`. Dark brown supports readable text; category names and accessible date labels supplement color and icons. All text uses at least 14px, apart from no text-bearing icon graphics. The month fits narrow screens without a horizontally scrolling timeline; the agenda and change controls stack below it on phones.

Keyboard-operable dates and actions, explicit labels, visible focus states, a skip link, live status announcements and confirmation focus are included. Formal accessibility certification and connected product behavior remain future work.
