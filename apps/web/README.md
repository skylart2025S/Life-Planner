# Life Planner browser prototype

A zero-build personal calendar and manual wardrobe. Serve the repository's apps/web directory on localhost using the command in the main README. No package installation or API key is needed.

## Calendar

Starts empty on the current month. Select a day, choose Add event, enter a title/category/start/end and review the proposed event. Confirm saves on this browser/device. The agenda supports edits and removal; all changes require preview and explicit confirmation. Cancel never writes. Month navigation, Today and keyboard date selection use real dates.

Times use the browser's displayed timezone and are stored as UTC instants. Invalid local times and ambiguous daylight-saving times are rejected rather than silently shifted. Events cannot overlap; adjacent times are allowed. A fixed event must first be explicitly unlocked at its existing time before moving or removing it. There is no recurrence or automatic movement of linked meal/outfit preparation in this local slice.

Saved records survive refresh. Writes use Web Locks and optimistic revision/token checks; another tab changing the calendar disables stale changes until explicit reload. Corrupt/unavailable storage is surfaced and never silently replaced. Device storage is not an authenticated account, cloud sync or backup. The UI does not call the API or a language model. No sample requests are presented as AI.

## Design

The user's requested Acloset-inspired direction is interpreted as a sparse, practical calendar: compact toolbar, simple sans serif typography, selected-day circle, small category tiles and a readable agenda. The reference was the calendar screen shown on [Acloset's official website](https://www.acloset.app/). This is an original Life Planner interface; it uses no Acloset branding, imagery or code. The former marketing hero, decorative motifs, summary cards and large assistant panel are removed.

The exact Warm Neutral Tones remain: Azure Mist `#ecf8f8`, Alabaster Grey `#eee4e1`, Almond Cream `#e7d8c9`, Almond Silk `#e6beae`, and Camel `#b2967d`. Dark brown supports readable text; category names and accessible date labels supplement color and icons. Calendar text uses at least 14px; the wardrobe has smaller secondary labels. The month fits narrow screens without a horizontally scrolling timeline; the agenda and change controls stack below it on phones.

Keyboard-operable dates and actions, explicit labels, visible focus states, a skip link, live status announcements and confirmation focus are included. Formal accessibility certification and connected product behavior remain future work.

## Manual wardrobe and outfits

Open Wardrobe from the header. Add clothes and availability, then preview and save a named outfit from available items. Wardrobe and calendar use separate storage keys. No account isolation, cloud backup, AI suggestions, weather, photos or event outfit assignments are provided. Future migration must require explicit destination-account confirmation.

## Validation

Run `node --test tests/web/*.test.js`. These behavior tests run in CI alongside the full Python/PostgreSQL suite. Browser accessibility and responsive checks are documented in dated reports; automated domain tests are not a full browser audit. See docs/DELIVERY_PLAN.md for unclosed account, AI and release gates.
