(function () {
  'use strict';
  const D = window.CalendarDomain;
  const $ = id => document.getElementById(id);
  const kinds = { workout: 'Workout', study: 'Focus', meal: 'Meal', clothing: 'Clothing', personal: 'Personal' };
  const icons = {
    workout: 'M6 6v12m-3-9v6m15-9v12m3-9v6M6 12h12',
    study: 'M12 5v15M3 4h5a4 4 0 0 1 4 2 4 4 0 0 1 4-2h5v15h-5a5 5 0 0 0-4 1 5 5 0 0 0-4-1H3Z',
    meal: 'M4 3v7a3 3 0 0 0 6 0V3M7 3v18m12-18c-4 3-4 8 0 9V3Zm0 9v9',
    clothing: 'm8 3-5 3-2 5 5 2v8h12v-8l5-2-2-5-5-3a4 4 0 0 1-8 0Z',
    personal: 'm4 19 5-6 4 3 7-10m-6 0h6v6'
  };
  let state = null, token, store, stale = false, busy = false, editing = null, review = null;
  const today = new Date(); today.setHours(12, 0, 0, 0);
  let selected = bounded(today), month = new Date(selected.getFullYear(), selected.getMonth(), 1, 12);
  function bounded(date) { return new Date(Math.max(new Date(2000, 0, 1, 12).getTime(), Math.min(new Date(2100, 11, 31, 12).getTime(), date.getTime()))); }
  function el(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
  function key(date) { return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`; }
  function dateLabel(date) { return new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' }).format(date); }
  function instantLabel(value) { return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(value)); }
  function icon(kind) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS(svg.namespaceURI, 'path'); path.setAttribute('d', icons[kind]); svg.append(path); return svg;
  }
  function message(text) { $('calendar-error').hidden = true; $('calendar-status').textContent = text; }
  function error(text) {
    $('calendar-status').textContent = ''; $('calendar-error').replaceChildren(el('span', text)); $('calendar-error').hidden = false;
    const reload = el('button', 'Reload saved plans'); reload.type = 'button'; reload.addEventListener('click', reviewReload); $('calendar-error').append(reload);
  }
  function controls() {
    const locked = !state || stale || busy || !!review || !navigator.locks;
    document.querySelectorAll('#plan-form input, #plan-form select, #plan-form button, #agenda-list button, #add-plan').forEach(node => { node.disabled = locked; });
    $('reload-plans').disabled = busy || !!review;
    $('review-confirm').disabled = busy; $('review-cancel').disabled = busy;
    document.querySelectorAll('#calendar-error button').forEach(node => { node.disabled = busy || !!review; });
    $('previous-month').disabled = month.getFullYear() === 2000 && month.getMonth() === 0;
    $('next-month').disabled = month.getFullYear() === 2100 && month.getMonth() === 11;
    // A fixed event must first be unlocked with its existing interval unchanged.
    const fixed = state?.events.find(item => item.id === editing)?.fixed;
    $('plan-start').readOnly = !!fixed; $('plan-end').readOnly = !!fixed;
  }
  function eventsOn(date) {
    const start = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
    const end = new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1).getTime();
    return (state?.events || []).filter(item => Date.parse(item.start) < end && Date.parse(item.end) > start).sort((a, b) => Date.parse(a.start) - Date.parse(b.start));
  }
  function chooseDate(date, focus = false) {
    selected = bounded(date); month = new Date(selected.getFullYear(), selected.getMonth(), 1, 12); render();
    if (focus) $(`date-${key(selected)}`)?.focus();
  }
  function shiftMonth(delta, focus = false) {
    const target = new Date(month.getFullYear(), month.getMonth() + delta, 1, 12);
    target.setDate(Math.min(selected.getDate(), new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate())); chooseDate(target, focus);
  }
  function render() {
    const grid = $('days-grid'); grid.replaceChildren();
    const heading = new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(month);
    $('week-title').textContent = heading; grid.setAttribute('aria-label', `${heading} dates`);
    const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
    const offset = new Date(month.getFullYear(), month.getMonth(), 1).getDay();
    for (let cell = 0; cell < Math.ceil((days + offset) / 7) * 7; cell++) {
      const day = cell - offset + 1;
      if (day < 1 || day > days) { const blank = el('div', undefined, 'empty-cell'); blank.setAttribute('aria-hidden', 'true'); grid.append(blank); continue; }
      const date = new Date(month.getFullYear(), month.getMonth(), day, 12), items = eventsOn(date);
      const button = el('button', undefined, 'calendar-day'); button.type = 'button'; button.id = `date-${key(date)}`;
      button.tabIndex = key(date) === key(selected) ? 0 : -1; button.setAttribute('aria-pressed', String(key(date) === key(selected)));
      if (key(date) === key(today)) button.setAttribute('aria-current', 'date');
      button.setAttribute('aria-label', `${dateLabel(date)}. ${state ? `${items.length} ${items.length === 1 ? 'plan' : 'plans'}` : 'Saved plans unavailable'}`);
      const tiles = el('span', undefined, 'date-tiles'); tiles.setAttribute('aria-hidden', 'true');
      for (const item of items.slice(0, items.length > 2 ? 1 : 2)) { const tile = el('span', undefined, `mini-tile ${item.kind}`); tile.append(icon(item.kind)); tiles.append(tile); }
      if (items.length > 2) tiles.append(el('span', `+${items.length - 1}`, 'tile-overflow'));
      button.append(el('span', String(day), 'day-number'), tiles); button.addEventListener('click', () => chooseDate(date, true));
      button.addEventListener('keydown', event => {
        const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7, Home: -date.getDay(), End: 6 - date.getDay() }[event.key];
        if (delta !== undefined) { event.preventDefault(); chooseDate(new Date(date.getFullYear(), date.getMonth(), day + delta, 12), true); }
        else if (event.key === 'PageUp' || event.key === 'PageDown') { event.preventDefault(); shiftMonth(event.key === 'PageUp' ? -1 : 1, true); }
      }); grid.append(button);
    }
    renderAgenda(); $('event-count').textContent = state ? `${state.events.length} / 500 saved plans` : 'Saved plans unavailable'; controls();
  }
  function action(text, handler, label) { const button = el('button', text); button.type = 'button'; button.addEventListener('click', handler); button.setAttribute('aria-label', label); return button; }
  function renderAgenda() {
    const items = eventsOn(selected), list = $('agenda-list'); list.replaceChildren(); $('day-title').textContent = dateLabel(selected);
    $('day-count').textContent = state ? `${items.length} ${items.length === 1 ? 'plan' : 'plans'}` : '';
    if (!items.length) list.append(el('p', state ? 'Nothing planned. Add a plan to make this day yours.' : 'Your saved plans could not be loaded. See the storage message above.', 'empty-agenda'));
    for (const item of items) {
      const row = el('article', undefined, 'agenda-item'), tile = el('div', undefined, `agenda-icon ${item.kind}`); tile.append(icon(item.kind));
      const details = el('div', undefined, 'agenda-details'); details.append(el('h3', item.title), el('p', `${instantLabel(item.start)} – ${instantLabel(item.end)}`));
      if (item.fixed) details.append(el('span', 'Fixed time', 'fixed-tag'));
      const actions = el('div', undefined, 'event-actions'); actions.append(action('Edit / move', () => editEvent(item), `Edit or move ${item.title}`), action('Delete', () => reviewOperation({ type: 'delete', id: item.id }), `Delete ${item.title}`)); row.append(tile, details, actions); list.append(row);
    }
  }
  function resetForm(focus = false) {
    editing = null; $('plan-form').reset(); $('editor-title').textContent = 'Add a plan'; $('preview-plan').textContent = 'Review new plan'; $('cancel-edit').hidden = true;
    $('plan-start').value = `${key(selected)}T09:00`; $('plan-end').value = `${key(selected)}T10:00`; controls();
    if (focus) $('plan-title').focus();
  }
  function editEvent(item) {
    if (!state || stale || busy || review) return;
    editing = item.id; $('plan-title').value = item.title; $('plan-kind').value = item.kind; $('plan-start').value = D.isoToLocal(item.start); $('plan-end').value = D.isoToLocal(item.end); $('plan-fixed').checked = item.fixed;
    $('editor-title').textContent = 'Edit or move plan'; $('preview-plan').textContent = 'Review changes'; $('cancel-edit').hidden = false; controls(); $('plan-title').focus();
  }
  function version(label, item) {
    const section = el('section', undefined, 'review-version'); section.append(el('h3', label));
    if (!item) section.append(el('p', label === 'Before' ? 'No plan yet' : 'Plan will be removed'));
    else section.append(el('strong', item.title), el('p', `${instantLabel(item.start)} – ${instantLabel(item.end)}`), el('p', `${kinds[item.kind]} · ${item.fixed ? 'Fixed time' : 'Flexible time'}`));
    return section;
  }
  function openReview(details, title, note, label) {
    review = { ...details, token, snapshot: state, wasStale: stale, trigger: document.activeElement };
    $('review-title').textContent = title; $('review-note').textContent = note; $('review-confirm').textContent = label; $('review-error').hidden = true;
    controls(); $('review-dialog').showModal(); $('review-cancel').focus();
  }
  function reviewOperation(operation) {
    if (!state || stale || busy || review || !navigator.locks) return;
    try {
      const proposal = D.propose(state, operation), before = state.events.find(item => item.id === (operation.id || operation.event.id));
      $('review-diff').replaceChildren(version('Before', before), version('After', operation.type === 'delete' ? null : operation.event));
      openReview({ proposal, operation }, operation.type === 'delete' ? 'Delete this plan?' : operation.type === 'create' ? 'Add this plan?' : 'Save these changes?', 'Nothing changes until you confirm. All times use your browser’s timezone.', operation.type === 'delete' ? 'Confirm deletion' : 'Confirm and save');
    } catch (e) { error(e.message); }
  }
  function closeReview() {
    if (!review || busy) return;
    const trigger = review.trigger; review = null; $('review-dialog').close(); controls();
    if (trigger?.isConnected && !trigger.disabled) trigger.focus(); else $('reload-plans').focus();
  }
  function reviewReload() {
    if (busy || review) return;
    $('review-diff').replaceChildren(); openReview({ reload: true }, 'Reload saved plans?', 'Unsaved form changes will be discarded. Saved plans will not be deleted.', 'Reload saved plans');
  }
  function load() {
    stale = false; state = null; token = undefined;
    try { store ||= D.createStore(window.localStorage); const saved = store.load(); state = saved.state; token = saved.token; message('Your plans are saved on this device.'); }
    catch (e) { error(e.message); }
    if (!navigator.locks && state) error('This browser cannot safely coordinate device saving. Use a current browser over localhost or HTTPS. Your saved plans remain readable.');
    resetForm(); render();
  }
  $('plan-form').addEventListener('submit', event => {
    event.preventDefault(); if (!state || stale || busy || review) return;
    try {
      // Preserve exact instants of fixed events while explicitly unlocking them.
      const existing = state.events.find(item => item.id === editing);
      const next = { id: editing || crypto.randomUUID(), title: $('plan-title').value.trim(), kind: $('plan-kind').value, start: existing?.fixed ? existing.start : D.localToISO($('plan-start').value), end: existing?.fixed ? existing.end : D.localToISO($('plan-end').value), fixed: $('plan-fixed').checked };
      reviewOperation({ type: editing ? 'update' : 'create', event: next });
    } catch (e) { error(e.message); }
  });
  $('review-confirm').addEventListener('click', async () => {
    if (!review || busy) return;
    const pending = review;
    if (pending.token !== token || pending.snapshot !== state || pending.wasStale !== stale) { closeReview(); error('Your saved plans changed. Reload them and review a fresh change.'); return; }
    if (pending.reload) { closeReview(); load(); $('plan-title').focus(); return; }
    if (!state || stale || !navigator.locks) return;
    busy = true; controls();
    try {
      const next = D.apply(state, pending.proposal);
      const saved = await navigator.locks.request(D.KEY, () => store.save(next, pending.token));
      state = saved.state; token = saved.token; busy = false; closeReview();
      if (pending.operation.type !== 'delete') { const start = new Date(pending.operation.event.start); selected = bounded(new Date(start.getFullYear(), start.getMonth(), start.getDate(), 12)); month = new Date(selected.getFullYear(), selected.getMonth(), 1, 12); }
      resetForm(); render(); message(pending.operation.type === 'delete' ? 'Plan deleted from this device.' : 'Plan saved on this device.'); $('plan-title').focus();
    } catch (e) { $('review-error').textContent = `${e.message} Cancel to return to your calendar.`; $('review-error').hidden = false; }
    finally { busy = false; controls(); }
  });
  $('review-cancel').addEventListener('click', closeReview);
  $('review-dialog').addEventListener('cancel', event => { event.preventDefault(); closeReview(); });
  $('review-dialog').addEventListener('close', () => { if (!$('review-dialog').open && review && !busy) closeReview(); });
  $('add-plan').addEventListener('click', () => resetForm(true)); $('cancel-edit').addEventListener('click', () => resetForm(true));
  $('previous-month').addEventListener('click', () => shiftMonth(-1)); $('next-month').addEventListener('click', () => shiftMonth(1)); $('today').addEventListener('click', () => chooseDate(today, true)); $('reload-plans').addEventListener('click', reviewReload);
  window.addEventListener('storage', event => {
    if (event.key !== D.KEY && event.key !== null) return;
    stale = true; if (!busy) closeReview(); error('Your calendar changed in another tab. Reload saved plans to continue. Your unsaved form stays here until you choose to reload.'); controls();
  });
  $('timezone-label').textContent = `Times shown in ${D.localTimeZone()}. Supported dates: 2000–2100.`;
  load();
})();
