'use strict';

// Deliberately local sample UI. The Python core remains the production rule source.
// This predefined move demonstrates preview/confirmation; it makes no API calls.
const originalEvents = [
  { id: 'monday-gym', day: 0, start: 9, duration: 1, title: 'Morning gym', kind: 'workout', icon: '↗' },
  { id: 'monday-focus', day: 0, start: 13, duration: 2, title: 'Deep work', kind: 'study', icon: '▤' },
  { id: 'tuesday-focus', day: 1, start: 10, duration: 2, title: 'Study session', kind: 'study', icon: '▤' },
  { id: 'wednesday-focus', day: 2, start: 10, duration: 1.5, title: 'Read & reflect', kind: 'study', icon: '▤' },
  { id: 'meal', day: 2, start: 17, duration: .5, title: 'Pre-workout meal', kind: 'meal', icon: '◒', linked: 'gym' },
  { id: 'clothes', day: 2, start: 17.75, duration: .25, title: 'Gym clothes', kind: 'clothing', icon: '◇', linked: 'gym' },
  { id: 'gym', day: 2, start: 18, duration: 1, title: 'Evening gym', kind: 'workout', icon: '↗' },
  { id: 'thursday-focus', day: 3, start: 14, duration: 2, title: 'Study session', kind: 'study', icon: '▤' },
  { id: 'friday-gym', day: 4, start: 9, duration: 1, title: 'Morning gym', kind: 'workout', icon: '↗' },
  { id: 'saturday-walk', day: 5, start: 11, duration: 1.5, title: 'A slower morning', kind: 'personal', icon: '☀' },
  { id: 'sunday-plan', day: 6, start: 16, duration: 1, title: 'Reset for the week', kind: 'personal', icon: '✧' },
];
const linkedIds = ['gym', 'meal', 'clothes'];
const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
let events = originalEvents.map(event => ({ ...event }));
let preview = false;
let applied = false;
const byId = id => document.getElementById(id);
function timeLabel(hour) {
  const whole = Math.floor(hour);
  const minutes = Math.round((hour - whole) * 60);
  return `${whole % 12 || 12}${minutes ? `:${String(minutes).padStart(2, '0')}` : ''} ${whole >= 12 ? 'PM' : 'AM'}`;
}
function eventElement(event, proposed = false, ghost = false) {
  const element = document.createElement('div');
  element.className = `event ${event.kind}${event.duration < .75 ? ' compact' : ''}${proposed ? ' proposed' : ''}${ghost ? ' source-ghost' : ''}`;
  element.style.top = `${(event.start - 9) * 44 + 2}px`;
  element.style.height = `${Math.max(event.duration * 44 - 4, event.duration < .5 ? 11 : 18)}px`;
  const fullLabel = `${event.title}, ${dayNames[event.day]} ${timeLabel(event.start)} to ${timeLabel(event.start + event.duration)}${proposed ? ', proposed change' : ''}${ghost ? ', original time, pending move' : ''}`;
  element.title = fullLabel;
  element.setAttribute('aria-label', fullLabel);
  const icon = document.createElement('span'); icon.className = 'event-icon'; icon.textContent = event.icon; icon.setAttribute('aria-hidden', 'true');
  const title = document.createElement('span'); title.className = 'event-title'; title.textContent = event.title;
  const time = document.createElement('span'); time.className = 'event-time'; time.textContent = timeLabel(event.start);
  element.append(icon, title, time);
  return element;
}
function renderCalendar() {
  const grid = byId('days-grid'); grid.replaceChildren();
  for (let day = 0; day < 7; day++) {
    const column = document.createElement('div');
    column.className = `day-column${day >= 5 ? ' weekend' : ''}${day === 2 ? ' today-column' : ''}`;
    column.setAttribute('role', 'group'); column.setAttribute('aria-label', `${dayNames[day]}, November ${23 + day}`);
    events.filter(event => event.day === day).forEach(event => column.append(eventElement(event, false, preview && linkedIds.includes(event.id))));
    if (preview && day === 3) events.filter(event => linkedIds.includes(event.id)).forEach(event => column.append(eventElement({ ...event, day: 3 }, true)));
    grid.append(column);
  }
  byId('calendar-status').replaceChildren();
  const dot = document.createElement('i'); dot.className = 'status-dot';
  byId('calendar-status').append(dot, document.createTextNode(preview ? 'Previewing 3 changes · nothing saved yet' : applied ? '3 changes confirmed in this demo' : 'Your sample plans are aligned'));
  byId('quick-move').disabled = preview || applied;
}
function appendMessage(text, type = 'response') {
  const message = document.createElement('p'); message.className = `${type}-message`; message.textContent = text;
  byId('conversation').append(message);
}
function showPreview(text) {
  if (preview) { appendMessage('Your preview is ready below. Confirm the three changes, or keep your original plans.'); return; }
  if (applied) { appendMessage('Your gym session and preparations are already on Thursday. Reset the demo to try it again.'); return; }
  appendMessage(text, 'user');
  appendMessage('Thursday evening is clear in this sample week. Here’s how your gym session and its preparations would move together.');
  preview = true;
  const list = byId('change-list'); list.replaceChildren();
  for (const id of linkedIds) {
    const event = events.find(item => item.id === id);
    const row = document.createElement('li');
    const icon = document.createElement('span'); icon.className = `change-icon ${event.kind === 'workout' ? 'green' : 'sand'}`; icon.textContent = event.icon; icon.setAttribute('aria-hidden', 'true');
    const details = document.createElement('div'); details.className = 'change-details';
    const title = document.createElement('strong'); title.textContent = event.title;
    const when = document.createElement('span'); when.textContent = `Wed → Thu · ${timeLabel(event.start)}`;
    details.append(title, when);
    const check = document.createElement('span'); check.className = 'change-check'; check.textContent = '✓'; check.setAttribute('aria-hidden', 'true');
    row.append(icon, details, check); list.append(row);
  }
  byId('proposal').hidden = false; renderCalendar();
}
byId('quick-move').addEventListener('click', () => showPreview('Move Wednesday’s gym session to Thursday.'));
byId('chat-form').addEventListener('submit', event => {
  event.preventDefault();
  const input = byId('message-input'); const text = input.value.trim();
  if (!text) { input.focus(); return; }
  input.value = '';
  const normalized = text.toLowerCase();
  const supported = /^(?:please )?(?:move|reschedule|shift) (?:(?:my|the) )?(?:wednesday(?:['’]s)? )?gym(?: session)? to thursday(?: please)?[.!]?$/.test(normalized);
  if (supported) showPreview(text);
  else {
    appendMessage(text, 'user');
    appendMessage('This local demo supports one example: “Move Wednesday gym to Thursday,” keeping the same time. Try that phrase or the quick action above. Other dates, times, and requests aren’t connected yet.');
  }
});
byId('confirm').addEventListener('click', () => {
  if (!preview) return;
  events = events.map(event => linkedIds.includes(event.id) ? { ...event, day: 3 } : event);
  preview = false; applied = true; byId('proposal').hidden = true;
  appendMessage('All set for Thursday: meal at 5 PM, gym clothes at 5:45 PM, and gym at 6 PM. Your other plans stayed put. These changes are only in this demo.');
  renderCalendar(); byId('message-input').focus();
});
byId('cancel').addEventListener('click', () => {
  preview = false; byId('proposal').hidden = true;
  appendMessage('Kept your original Wednesday plans. Nothing was changed.'); renderCalendar(); byId('quick-move').focus();
});
byId('reset').addEventListener('click', () => {
  events = originalEvents.map(event => ({ ...event })); preview = false; applied = false;
  byId('proposal').hidden = true; byId('conversation').replaceChildren(); byId('message-input').value = '';
  appendMessage('Demo reset. Your sample week is back to its original plan.'); renderCalendar();
});
renderCalendar();
