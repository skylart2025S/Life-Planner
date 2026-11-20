'use strict';

// Local sample only: the production rule authority remains the Python planner.
const originalEvents = [
  { id: 'monday-gym', day: 0, start: 9, duration: 1, title: 'Morning gym', kind: 'workout' },
  { id: 'monday-focus', day: 0, start: 13, duration: 2, title: 'Deep work', kind: 'study' },
  { id: 'tuesday-focus', day: 1, start: 10, duration: 2, title: 'Study session', kind: 'study' },
  { id: 'wednesday-focus', day: 2, start: 10, duration: 1.5, title: 'Read & reflect', kind: 'study' },
  { id: 'meal', day: 2, start: 17, duration: .5, title: 'Pre-workout meal', kind: 'meal', linked: 'gym' },
  { id: 'clothes', day: 2, start: 17.75, duration: .25, title: 'Gym clothes', kind: 'clothing', linked: 'gym' },
  { id: 'gym', day: 2, start: 18, duration: 1, title: 'Evening gym', kind: 'workout' },
  { id: 'thursday-focus', day: 3, start: 14, duration: 2, title: 'Study session', kind: 'study' },
  { id: 'friday-gym', day: 4, start: 9, duration: 1, title: 'Morning gym', kind: 'workout' },
  { id: 'saturday-walk', day: 5, start: 11, duration: 1.5, title: 'Morning walk', kind: 'personal' },
  { id: 'sunday-plan', day: 6, start: 16, duration: 1, title: 'Plan next week', kind: 'personal' },
];
const linkedIds = ['meal', 'clothes', 'gym'];
const byId = id => document.getElementById(id);
let events = originalEvents.map(event => ({ ...event }));
let preview = false;
let applied = false;
let selectedDate = 25;
const iconPaths = {
  workout: ['M6 6v12m-3-9v6m15-9v12m3-9v6M6 12h12'],
  study: ['M12 5v15M3 4h5a4 4 0 0 1 4 2 4 4 0 0 1 4-2h5v15h-5a5 5 0 0 0-4 1 5 5 0 0 0-4-1H3Z'],
  meal: ['M4 3v7a3 3 0 0 0 6 0V3M7 3v18m12-18c-4 3-4 8 0 9V3Zm0 9v9'],
  clothing: ['m8 3-5 3-2 5 5 2v8h12v-8l5-2-2-5-5-3a4 4 0 0 1-8 0Z'],
  personal: ['m4 19 5-6 4 3 7-10m-6 0h6v6'],
};
function icon(kind) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('aria-hidden', 'true');
  for (const d of iconPaths[kind]) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', d); svg.append(path);
  }
  return svg;
}
function timeLabel(hour) {
  const whole = Math.floor(hour); const minutes = Math.round((hour - whole) * 60);
  return `${whole % 12 || 12}${minutes ? `:${String(minutes).padStart(2, '0')}` : ''} ${whole >= 12 ? 'PM' : 'AM'}`;
}
function dateLabel(date) {
  return new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'short', day: 'numeric', timeZone: 'UTC' }).format(new Date(Date.UTC(2026, 10, date)));
}
function visibleEvents(date) {
  const current = events.filter(event => event.day + 23 === date).map(event => ({ ...event, pending: preview && linkedIds.includes(event.id) }));
  if (preview && date === 26) current.push(...events.filter(event => linkedIds.includes(event.id)).map(event => ({ ...event, day: 3, proposed: true })));
  return current.sort((a, b) => a.start - b.start);
}
function selectDate(date, focus = false) {
  selectedDate = date; renderCalendar();
  if (focus) byId(`date-${date}`).focus();
}
function renderCalendar() {
  const grid = byId('days-grid'); grid.replaceChildren();
  // November 1, 2026 is a Sunday; five complete rows cover the month.
  for (let date = 1; date <= 35; date++) {
    if (date > 30) { const blank = document.createElement('div'); blank.className = 'empty-cell'; blank.setAttribute('aria-hidden', 'true'); grid.append(blank); continue; }
    const items = visibleEvents(date);
    const button = document.createElement('button'); button.type = 'button'; button.id = `date-${date}`;
    button.className = 'calendar-day'; button.setAttribute('aria-pressed', String(date === selectedDate));
    button.setAttribute('aria-label', `${dateLabel(date)}, 2026. ${items.length ? items.map(item => `${item.title} at ${timeLabel(item.start)}${item.proposed ? ', proposed' : item.pending ? ', pending move' : ''}`).join('; ') : 'No sample plans'}`);
    const number = document.createElement('span'); number.className = 'day-number'; number.textContent = date;
    const tiles = document.createElement('span'); tiles.className = 'date-tiles'; tiles.setAttribute('aria-hidden', 'true');
    for (const item of items.slice(0, items.length > 2 ? 1 : 2)) {
      const tile = document.createElement('span'); tile.className = `mini-tile ${item.kind}${item.proposed ? ' proposed' : item.pending ? ' pending' : ''}`;
      tile.append(icon(item.kind)); tiles.append(tile);
    }
    if (items.length > 2) { const more = document.createElement('span'); more.className = 'tile-overflow'; more.textContent = `+${items.length - 1}`; tiles.append(more); }
    button.append(number, tiles); button.addEventListener('click', () => selectDate(date, true));
    button.addEventListener('keydown', event => {
      const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
      if (delta) { event.preventDefault(); selectDate(Math.max(1, Math.min(30, date + delta)), true); }
    });
    grid.append(button);
  }
  renderAgenda();
  byId('calendar-status').textContent = preview ? 'Previewing 3 changes · not confirmed' : applied ? '3 changes confirmed in this sample' : 'Sample schedule · nothing saved';
  byId('quick-move').disabled = preview || applied;
}
function renderAgenda() {
  const items = visibleEvents(selectedDate);
  byId('day-title').textContent = dateLabel(selectedDate);
  byId('day-count').textContent = `${items.length} ${items.length === 1 ? 'plan' : 'plans'}`;
  const note = byId('agenda-note'); note.hidden = !(preview && (selectedDate === 25 || selectedDate === 26));
  note.textContent = selectedDate === 26 ? 'Preview · 3 plans would move here' : 'Preview · 3 plans would move to Thursday';
  const list = byId('agenda-list'); list.replaceChildren();
  if (!items.length) { const empty = document.createElement('p'); empty.className = 'empty-agenda'; empty.textContent = 'No sample plans for this day.'; list.append(empty); }
  for (const item of items) {
    const row = document.createElement('article'); row.className = `agenda-item${item.proposed ? ' proposed' : item.pending ? ' pending' : ''}`;
    const tile = document.createElement('div'); tile.className = `agenda-icon ${item.kind}`; tile.append(icon(item.kind));
    const details = document.createElement('div'); details.className = 'agenda-details';
    const title = document.createElement('h3'); title.textContent = item.title;
    const time = document.createElement('p'); time.textContent = `${timeLabel(item.start)} – ${timeLabel(item.start + item.duration)}`;
    details.append(title, time);
    if (item.proposed || item.pending) { const state = document.createElement('span'); state.className = 'event-state'; state.textContent = item.proposed ? 'Proposed · from Wednesday' : 'Pending move to Thursday'; details.append(state); }
    row.append(tile, details); list.append(row);
  }
}
function appendMessage(text) {
  // A concise status replaces prior requests; no transcript or private data is stored.
  const message = document.createElement('p'); message.className = 'response-message'; message.textContent = text;
  byId('conversation').replaceChildren(message);
}
function showPreview() {
  if (preview) { appendMessage('Review the three changes below, then confirm or keep Wednesday’s plans.'); return; }
  if (applied) { appendMessage('These plans are already on Thursday. Reset the sample to try again.'); return; }
  preview = true; selectedDate = 26;
  appendMessage('Nothing has changed yet. Thursday shows the proposed schedule.');
  const list = byId('change-list'); list.replaceChildren();
  for (const id of linkedIds) {
    const event = events.find(item => item.id === id);
    const row = document.createElement('li');
    const tile = document.createElement('span'); tile.className = `change-icon ${event.kind}`; tile.append(icon(event.kind));
    const details = document.createElement('div'); details.className = 'change-details';
    const title = document.createElement('strong'); title.textContent = event.title;
    const when = document.createElement('span'); when.textContent = `Wed 25 → Thu 26 · ${timeLabel(event.start)}`;
    details.append(title, when); row.append(tile, details); list.append(row);
  }
  byId('proposal').hidden = false; renderCalendar(); byId('confirm').focus();
}
byId('quick-move').addEventListener('click', showPreview);
byId('sample-week').addEventListener('click', () => selectDate(applied || preview ? 26 : 25, true));
byId('chat-form').addEventListener('submit', event => {
  event.preventDefault(); const input = byId('message-input'); const text = input.value.trim();
  if (!text) { input.focus(); return; }
  input.value = '';
  const supported = /^(?:please )?(?:move|reschedule|shift) (?:(?:my|the) )?(?:wednesday(?:['’]s)? )?gym(?: session)? to thursday(?: please)?[.!]?$/.test(text.toLowerCase());
  if (supported) showPreview();
  else appendMessage('This sample supports “Move Wednesday gym to Thursday” at the same time. Other dates, times, and requests are not connected yet.');
});
byId('confirm').addEventListener('click', () => {
  if (!preview) return;
  events = events.map(event => linkedIds.includes(event.id) ? { ...event, day: 3 } : event);
  preview = false; applied = true; selectedDate = 26; byId('proposal').hidden = true;
  appendMessage('Moved to Thursday: meal at 5 PM, clothes at 5:45 PM, gym at 6 PM. Changes are only in this sample.');
  renderCalendar(); byId('message-input').focus();
});
byId('cancel').addEventListener('click', () => {
  preview = false; selectedDate = 25; byId('proposal').hidden = true;
  appendMessage('Kept your Wednesday plans. Nothing changed.'); renderCalendar(); byId('quick-move').focus();
});
byId('reset').addEventListener('click', () => {
  events = originalEvents.map(event => ({ ...event })); preview = false; applied = false; selectedDate = 25;
  byId('proposal').hidden = true; byId('message-input').value = '';
  appendMessage('Sample reset. Your original Wednesday plans are restored.'); renderCalendar();
});
renderCalendar();
