(function () {
  'use strict';
  const D = window.Wardrobe;
  const $ = id => document.getElementById(id);
  const labels = { top: 'Top', bottom: 'Bottom', 'one-piece': 'One piece', shoes: 'Shoes', layer: 'Layer' };
  const drawings = {
    top: 'M18 12 27 8l5 6 5-6 9 4 10 14-10 7-4-6v28H22V27l-4 6-10-7Z',
    bottom: 'M20 9h24l4 46H34l-2-28-2 28H16Zm0 8h24',
    'one-piece': 'M25 8h14l4 13-5 9 14 25H12l14-25-5-9Zm1 22h12',
    shoes: 'M12 20h12l9 14 18 5 4 9v6H9V32Zm-3 27h46M29 30l-6 5m12 1-6 5',
    layer: 'M24 9h16l11 10 6 31-12 3-5-23v26H24V30l-5 23-12-3 6-31Zm0 0 8 14 8-14M32 23v33'
  };
  let store, state = null, token, editing = null, outfitId = null, preview = null, stale = false, busy = false, confirmation = null;
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function error(message) { $('error').textContent = message; $('error').hidden = false; $('feedback').textContent = ''; }
  function notice(message) { $('error').hidden = true; $('feedback').textContent = message; }
  function controls() {
    const locked = !state || stale || busy || !!confirmation || !navigator.locks;
    document.querySelectorAll('#item-form input, #item-form select, #item-form button, #outfit-form input, #outfit-form select, #outfit-form button, #garments button, #outfits button, #confirm-outfit').forEach(node => { node.disabled = locked; });
    $('clear').disabled = token === undefined || stale || busy || !!confirmation || !navigator.locks;
    $('reload').disabled = busy || !!confirmation;
  }
  function confirmAction(message, label) {
    if (busy || confirmation) return Promise.resolve(false);
    const trigger = document.activeElement, expected = token, snapshot = state, wasStale = stale;
    $('confirmation-message').textContent = message;
    $('confirmation-accept').textContent = label;
    return new Promise(resolve => {
      confirmation = accepted => {
        const valid = token === expected && state === snapshot && stale === wasStale && !busy;
        confirmation = null;
        $('confirmation-dialog').close();
        controls();
        if (trigger?.isConnected && !trigger.disabled) trigger.focus();
        else $('reload').focus();
        resolve(accepted && valid);
      };
      controls();
      $('confirmation-dialog').showModal();
      $('confirmation-cancel').focus();
    });
  }
  $('confirmation-accept').addEventListener('click', () => confirmation?.(true));
  $('confirmation-cancel').addEventListener('click', () => confirmation?.(false));
  $('confirmation-dialog').addEventListener('cancel', event => { event.preventDefault(); confirmation?.(false); });
  $('confirmation-dialog').addEventListener('close', () => { if (!$('confirmation-dialog').open) confirmation?.(false); });
  function cancelPreview() { preview = null; $('outfit-preview').hidden = true; }
  function resetItem() { editing = null; $('item-form').reset(); $('item-form-title').textContent = 'Add an item'; $('cancel-edit').hidden = true; }
  function resetOutfit() { outfitId = null; $('outfit-form').reset(); $('new-outfit').hidden = true; cancelPreview(); baseFields(); }
  function baseFields() {
    const onePiece = $('outfit-base').value === 'onePiece';
    $('separates-fields').hidden = onePiece; $('one-piece-fields').hidden = !onePiece;
    cancelPreview();
  }
  function action(text, handler, label) {
    const button = el('button', text); button.type = 'button'; button.addEventListener('click', handler);
    if (label) button.setAttribute('aria-label', label);
    return button;
  }
  function silhouette(category) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 64 64'); svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS(svg.namespaceURI, 'path'); path.setAttribute('d', drawings[category]); svg.append(path); return svg;
  }
  function render() {
    $('garments').replaceChildren(); $('outfits').replaceChildren();
    $('item-count').textContent = state ? `${state.garments.length}/200` : '';
    $('outfit-count').textContent = state ? `${state.outfits.length}/100` : '';
    if (!state || !state.garments.length) {
      const empty = el('div', undefined, 'empty');
      empty.append(el('strong', state ? 'A little space for your clothes.' : 'Your saved clothes cannot be displayed.'), el('span', state ? 'Add your first item below. Only clothes you enter will appear here.' : 'See the storage message above.'));
      $('garments').append(empty);
    }
    for (const garment of state?.garments || []) {
      const card = el('article', undefined, 'garment-card');
      const art = el('div', undefined, `garment-art category-${garment.category}`); art.append(silhouette(garment.category));
      if (!garment.available) art.append(el('span', 'Unavailable', 'availability'));
      const actions = el('div', undefined, 'card-actions');
      actions.append(action('Edit', () => editItem(garment), `Edit ${garment.name}`), action('Delete', () => removeItem(garment), `Delete ${garment.name}`));
      card.append(art, el('h3', garment.name), el('p', `${garment.color} · ${labels[garment.category]}`), el('p', garment.occasion === 'any' ? 'Any occasion' : garment.occasion[0].toUpperCase() + garment.occasion.slice(1)), actions);
      $('garments').append(card);
    }
    for (const [slot, category] of Object.entries(D.SLOTS)) {
      const select = $(`outfit-${slot}`), selected = select.value;
      select.replaceChildren();
      const available = (state?.garments || []).filter(g => g.category === category && g.available);
      const option = el('option', slot === 'layer' ? 'No layer' : available.length ? `Choose ${labels[category].toLowerCase()}` : `Add available ${category === 'shoes' ? 'shoes' : 'clothes'} first`); option.value = ''; select.append(option);
      for (const g of available) { const option = el('option', `${g.name} · ${g.color}`); option.value = g.id; select.append(option); }
      if (available.some(g => g.id === selected)) select.value = selected;
    }
    if (state && !state.outfits.length) $('outfits').append(el('p', 'Your saved outfits will appear here.', 'helper'));
    for (const outfit of state?.outfits || []) {
      const card = el('article', undefined, 'saved-outfit');
      const actions = el('div', undefined, 'card-actions');
      actions.append(action('Open', () => openOutfit(outfit), `Open ${outfit.name}`), action('Delete', () => removeOutfit(outfit), `Delete outfit ${outfit.name}`));
      card.append(el('h3', outfit.name), el('p', Object.values(outfit.items).map(id => state.garments.find(g => g.id === id).name).join(' · ')), actions);
      $('outfits').append(card);
    }
    controls();
  }
  function load() {
    stale = false; token = undefined;
    try {
      if (!store) store = D.createStore(window.localStorage);
      const saved = store.read(); state = saved.state; token = saved.token;
      notice('');
      if (!navigator.locks) error('This browser cannot safely coordinate device storage. Use a current browser over localhost or HTTPS to save items.');
    } catch (e) { state = null; token = e.token; error(e.message); }
    resetItem(); resetOutfit(); render();
  }
  async function mutate(transform, message, expected = token) {
    if (!state || stale || busy || confirmation || expected !== token || !navigator.locks) return;
    busy = true; controls();
    try {
      const next = transform(state);
      const saved = await navigator.locks.request(D.KEY, () => store.write(expected, next));
      state = saved.state; token = saved.token; resetItem(); resetOutfit(); render(); notice(message);
    } catch (e) { error(e.message); cancelPreview(); }
    finally { busy = false; controls(); if (document.activeElement === document.body && !$('item-name').disabled) $('item-name').focus(); }
  }
  function editItem(g) {
    editing = g.id; $('item-name').value = g.name; $('item-category').value = g.category; $('item-color').value = g.color; $('item-occasion').value = g.occasion; $('item-available').checked = g.available;
    $('item-form-title').textContent = 'Edit item'; $('cancel-edit').hidden = false; $('item-name').focus();
  }
  async function removeItem(g) {
    if (!state || stale || busy || confirmation) return;
    const expected = token;
    const count = state.outfits.filter(o => Object.values(o.items).includes(g.id)).length;
    if (await confirmAction(`Delete “${g.name}”?${count ? ` This also removes ${count} saved outfit(s) that use it.` : ''}`, 'Delete item')) await mutate(s => D.deleteGarment(s, g.id), 'Item deleted. Any outfits using it were removed.', expected);
  }
  function openOutfit(o) {
    resetOutfit(); outfitId = o.id; $('outfit-name').value = o.name; $('outfit-base').value = o.items.onePiece ? 'onePiece' : 'separates'; baseFields();
    for (const slot of Object.keys(D.SLOTS)) $(`outfit-${slot}`).value = o.items[slot] || '';
    $('new-outfit').hidden = false; $('outfit-name').focus(); notice('Outfit opened. Changes are saved only after preview and confirmation.');
  }
  async function removeOutfit(o) {
    if (!state || stale || busy || confirmation) return;
    const expected = token;
    if (await confirmAction(`Delete outfit “${o.name}”? Your clothes will stay in your wardrobe.`, 'Delete outfit')) await mutate(s => ({ ...s, outfits: s.outfits.filter(item => item.id !== o.id) }), 'Outfit deleted.', expected);
  }
  $('item-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (!state || stale || busy || confirmation) return;
    try {
      const garment = { id: editing || crypto.randomUUID(), name: $('item-name').value.trim(), category: $('item-category').value, color: $('item-color').value.trim(), occasion: $('item-occasion').value, available: $('item-available').checked };
      const expected = token;
      const next = D.updateGarment(state, garment), removed = state.outfits.length - next.outfits.length;
      if (removed && !await confirmAction(`This change makes ${removed} saved outfit(s) unavailable and will remove them. Save this item change?`, 'Save item change')) return;
      await mutate(() => next, removed ? `Item saved. ${removed} unavailable outfit(s) removed.` : 'Item saved on this device.', expected);
    } catch (e) { error(e.message); }
  });
  $('outfit-form').addEventListener('submit', event => {
    event.preventDefault();
    if (!state || stale || busy || confirmation) return;
    try {
      const slots = $('outfit-base').value === 'onePiece' ? ['onePiece', 'shoes', 'layer'] : ['top', 'bottom', 'shoes', 'layer'];
      const items = Object.fromEntries(slots.filter(slot => $(`outfit-${slot}`).value).map(slot => [slot, $(`outfit-${slot}`).value]));
      preview = D.validateOutfit({ id: outfitId || crypto.randomUUID(), name: $('outfit-name').value.trim(), items }, state.garments);
      $('preview-title').textContent = preview.name; $('preview-items').replaceChildren();
      for (const id of Object.values(items)) { const g = state.garments.find(g => g.id === id); $('preview-items').append(el('li', `${g.name} · ${g.color}`)); }
      $('outfit-preview').hidden = false; notice('Preview ready. This outfit has not been saved.'); $('confirm-outfit').focus();
    } catch (e) { cancelPreview(); error(e.message); }
  });
  $('outfit-form').addEventListener('input', cancelPreview);
  $('outfit-form').addEventListener('change', cancelPreview);
  $('outfit-base').addEventListener('change', baseFields);
  $('confirm-outfit').addEventListener('click', () => { if (preview) { const outfit = preview; mutate(s => D.saveOutfit(s, outfit), 'Outfit saved on this device.'); } });
  $('cancel-preview').addEventListener('click', () => { cancelPreview(); $('outfit-name').focus(); });
  $('cancel-edit').addEventListener('click', resetItem);
  $('new-outfit').addEventListener('click', resetOutfit);
  $('reload').addEventListener('click', async () => { if (await confirmAction('Reload saved items? Unsaved form changes and previews will be discarded.', 'Reload saved items')) load(); });
  $('clear').addEventListener('click', async () => {
    if (busy || confirmation || stale || token === undefined || !navigator.locks) return;
    const expected = token;
    if (!await confirmAction('Permanently clear all clothes and outfits saved in this wardrobe on this device? This cannot be undone. Other site data will not be cleared.', 'Clear this wardrobe')) return;
    if (busy || stale || token !== expected) return;
    busy = true; controls();
    try { await navigator.locks.request(D.KEY, () => store.clear(expected)); load(); notice('This device’s wardrobe has been cleared.'); } catch (e) { error(e.message); }
    finally { busy = false; controls(); }
  });
  window.addEventListener('storage', event => {
    if (event.key === D.KEY || event.key === null) {
      stale = true; confirmation?.(false); cancelPreview(); error('Your wardrobe changed in another tab. Use “Reload saved items” below to load it. Unsaved forms will be discarded when you reload.'); controls();
    }
  });
  load();
})();
