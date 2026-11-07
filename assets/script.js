// Renders the "Trade desk notes" ledger from news.json.
// news.json is refreshed automatically by .github/workflows/update-news.yml,
// which calls the Claude API on a schedule. This script only reads it.

(async function loadNews() {
  const listEl = document.getElementById('news-list');
  const updatedEl = document.getElementById('news-updated');
  if (!listEl || !updatedEl) return;

  const lang = (document.documentElement.lang || 'en').slice(0, 2);
  const base = (document.querySelector('meta[name="fcfc-base"]') || {}).content || '';
  const LOC = { en: 'en-GB', de: 'de-CH', fr: 'fr-CH', it: 'it-CH' }[lang] || 'en-GB';
  const T = ({
    en: { updated: 'Updated', recently: 'Updated recently', na: 'Notes unavailable', err: 'Trade desk notes could not be loaded right now. Please check back shortly.', none: 'No trade desk notes yet — the first automated update will appear here shortly.', src: 'Source' },
    de: { updated: 'Aktualisiert', recently: 'Kürzlich aktualisiert', na: 'Notizen nicht verfügbar', err: 'Die Trade Desk Notes konnten gerade nicht geladen werden. Bitte versuchen Sie es später erneut.', none: 'Noch keine Notizen – die erste automatische Aktualisierung erscheint in Kürze.', src: 'Quelle' },
    fr: { updated: 'Mis à jour le', recently: 'Mis à jour récemment', na: 'Notes indisponibles', err: 'Les notes n’ont pas pu être chargées pour le moment. Merci de réessayer plus tard.', none: 'Pas encore de notes — la première mise à jour automatique apparaîtra ici sous peu.', src: 'Source' },
    it: { updated: 'Aggiornato il', recently: 'Aggiornato di recente', na: 'Note non disponibili', err: 'Al momento non è stato possibile caricare le note. Riprovi più tardi.', none: 'Ancora nessuna nota — il primo aggiornamento automatico apparirà a breve.', src: 'Fonte' }
  })[lang] || null;
  const L = T || { updated: 'Updated', recently: 'Updated recently', na: 'Notes unavailable', err: 'Trade desk notes could not be loaded right now. Please check back shortly.', none: 'No trade desk notes yet.', src: 'Source' };

  try {
    const res = await fetch(base + 'news.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('news.json not found (' + res.status + ')');
    const data = await res.json();
    renderUpdated(data.generated_at);
    const items = Array.isArray(data.items) ? data.items.slice() : [];
    items.sort(function (a, b) { return (b.date || '').localeCompare(a.date || ''); });
    renderItems(items);
  } catch (err) {
    updatedEl.textContent = L.na;
    listEl.innerHTML = '<p class="ledger-empty">' + escapeHtml(L.err) + '</p>';
    console.error('[fcfc] failed to load news.json:', err);
  }

  function renderUpdated(iso) {
    const d = iso ? new Date(iso) : null;
    if (!d || isNaN(d.getTime())) { updatedEl.textContent = L.recently; return; }
    updatedEl.textContent = L.updated + ' ' + d.toLocaleDateString(LOC, { day: '2-digit', month: 'short', year: 'numeric' });
  }

  function renderItems(items) {
    if (!items.length) { listEl.innerHTML = '<p class="ledger-empty">' + escapeHtml(L.none) + '</p>'; return; }
    listEl.innerHTML = items.map(function (item) {
      const tr = (lang !== 'en' && item.i18n && item.i18n[lang]) || item;
      const headline = escapeHtml(tr.headline || item.headline || '');
      const summary = escapeHtml(tr.summary || item.summary || '');
      const url = /^https:\/\//.test(item.url || '') ? item.url : '';
      const company = item.company ? '<span class="ledger-company">' + escapeHtml(item.company) + '</span>' : '';
      const head = url
        ? '<a class="ledger-link" href="' + escapeHtml(url) + '" target="_blank" rel="noopener nofollow">' + headline + '<span class="ledger-ext" aria-hidden="true">↗</span></a>'
        : headline;
      return (
        '<div class="ledger-row">' +
          '<div class="ledger-date">' + escapeHtml(formatDate(item.date)) + '</div>' +
          '<div class="ledger-tag">' + escapeHtml(item.tag || 'NOTE') + '</div>' +
          '<div class="ledger-headline">' + company + head + '</div>' +
          '<p class="ledger-summary">' + summary + '</p>' +
        '</div>'
      );
    }).join('');
  }

  function formatDate(isoDate) {
    if (!isoDate) return '';
    const d = new Date(isoDate);
    if (isNaN(d.getTime())) return isoDate;
    return d.toLocaleDateString(LOC, { day: '2-digit', month: 'short' }).toUpperCase();
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
})();

// Renders the market ticker strip from markets.json
// (refreshed by .github/workflows/update-markets.yml).
(async function loadMarkets() {
  var listEl = document.getElementById('ticker-list');
  var srcEl = document.getElementById('ticker-src');
  var box = document.getElementById('ticker');
  if (!listEl || !box) return;

  var lang = (document.documentElement.lang || 'en').slice(0, 2);
  var T = {
    en: { gold: 'Gold', brent: 'Brent', wti: 'WTI', ecb: 'ECB reference rates', asof: 'as of', ind: 'Indicative, not for trading' },
    de: { gold: 'Gold', brent: 'Brent', wti: 'WTI', ecb: 'EZB-Referenzkurse', asof: 'Stand', ind: 'Indikativ, nicht für den Handel' },
    fr: { gold: 'Or', brent: 'Brent', wti: 'WTI', ecb: 'Taux de référence BCE', asof: 'au', ind: 'Indicatif, ne pas utiliser pour négocier' },
    it: { gold: 'Oro', brent: 'Brent', wti: 'WTI', ecb: 'Tassi di riferimento BCE', asof: 'al', ind: 'Indicativo, non per la negoziazione' }
  }[lang] || null;
  T = T || { gold: 'Gold', brent: 'Brent', wti: 'WTI', ecb: 'ECB reference rates', asof: 'as of', ind: 'Indicative, not for trading' };
  var base = (document.querySelector('meta[name="fcfc-base"]') || {}).content || '';

  try {
    var res = await fetch(base + 'markets.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('markets.json ' + res.status);
    var data = await res.json();
    var rows = [];
    (data.commodities || []).forEach(function (c) {
      rows.push(item(T[c.key] || c.key, fmt(c.value, 2), c.unit, c.change_pct));
    });
    (data.fx || []).forEach(function (f) {
      rows.push(item(f.pair, fmt(f.value, 4), '', f.change_pct));
    });
    if (!rows.length) throw new Error('empty');
    listEl.innerHTML = rows.join('');
    var fxDate = (data.fx && data.fx[0] && data.fx[0].date) || '';
    var src = T.ecb + (fxDate ? ' ' + T.asof + ' ' + niceDate(fxDate) : '');
    if (data.commodities && data.commodities.length) src += ' · ' + 'OilPriceAPI';
    srcEl.textContent = src + ' · ' + T.ind;
    box.classList.add('is-ready');
  } catch (e) {
    box.hidden = true;
    console.warn('[fcfc] markets unavailable', e);
  }

  function item(name, value, unit, ch) {
    var cls = ch == null ? '' : (ch > 0 ? ' up' : (ch < 0 ? ' down' : ''));
    var chTxt = ch == null ? '' : '<span class="tk-ch' + cls + '">' + (ch > 0 ? '▲' : (ch < 0 ? '▼' : '■')) + ' ' + Math.abs(ch).toFixed(2) + '%</span>';
    return '<li><span class="tk-name">' + esc(name) + '</span><span class="tk-val">' + esc(value) + '</span>' +
      (unit ? '<span class="tk-unit">' + esc(unit) + '</span>' : '') + chTxt + '</li>';
  }
  function fmt(v, d) { return (typeof v === 'number') ? v.toFixed(d) : String(v); }
  function niceDate(iso) {
    var d = new Date(iso + 'T00:00:00Z');
    if (isNaN(d)) return iso;
    var loc = { en: 'en-GB', de: 'de-CH', fr: 'fr-CH', it: 'it-CH' }[lang] || 'en-GB';
    return d.toLocaleDateString(loc, { day: '2-digit', month: 'short', timeZone: 'UTC' });
  }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
})();
