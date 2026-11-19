# Life Planner visual prototype

A zero-build browser demo with a weekly calendar, linked gym/meal/clothing preparations, a proposed-change preview, explicit confirmation, cancellation, and reset. It uses sample dates November 23–29, 2026.

Serve from the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory apps/web
```

Open http://127.0.0.1:8765. No package installation, external fonts, images, or API keys are required.

Try the “Move Wednesday gym to Thursday” quick action or type that request. The original events fade and proposed Thursday events appear; confirmation applies all three local changes, cancellation preserves the original schedule. Reset restores the fixture.

This is a predefined, local interaction—not an AI chat service or an authenticated calendar. State lives only in browser memory and resets on reload. Only the demonstrated Wednesday-to-Thursday move is supported. The Python planning core remains the shared rule authority for future integration; this UI does not claim to call it. Week times are sample local wall times, not timezone conversion.

The layout supports narrow screens through horizontal calendar scrolling, responsive panels, keyboard-operable controls, visible focus states, and live message announcements. It has not been certified for accessibility. Connect the future authenticated API before adding arbitrary scheduling actions or real accounts.

## Visual palette

Warm Neutral Tones requested by the user: Azure Mist `#ecf8f8`, Alabaster Grey `#eee4e1`, Almond Cream `#e7d8c9`, Almond Silk `#e6beae`, and Camel `#b2967d`. Creamy supporting surfaces and darker soft brown text keep labels legible; pale swatches are used for backgrounds and accents.
