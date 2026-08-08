// Renders the "Trade desk notes" ledger from news.json.
// news.json is refreshed automatically by .github/workflows/update-news.yml,
// which calls the Claude API on a schedule. This script only reads it.

(async function loadNews() {
  const listEl = document.getElementById('news-list');
  const updatedEl = document.getElementById('news-updated');

  try {
    const res = await fetch('news.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('news.json not found (' + res.status + ')');
    const data = await res.json();

    renderUpdated(data.generated_at);
    renderItems(Array.isArray(data.items) ? data.items : []);
  } catch (err) {
    updatedEl.textContent = 'Notes unavailable';
    listEl.innerHTML = '<p class="ledger-empty">Trade desk notes could not be loaded right now. Please check back shortly.</p>';
    console.error('[fcfc] failed to load news.json:', err);
  }

  function renderUpdated(iso) {
    if (!iso) { updatedEl.textContent = 'Updated recently'; return; }
    const d = new Date(iso);
    if (isNaN(d.getTime())) { updatedEl.textContent = 'Updated recently'; return; }
    updatedEl.textContent = 'Updated ' + d.toLocaleDateString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  }

  function renderItems(items) {
    if (!items.length) {
      listEl.innerHTML = '<p class="ledger-empty">No trade desk notes yet — the first automated update will appear here shortly.</p>';
      return;
    }

    listEl.innerHTML = items.map(function (item) {
      const date = escapeHtml(formatDate(item.date));
      const tag = escapeHtml(item.tag || 'NOTE');
      const headline = escapeHtml(item.headline || '');
      const summary = escapeHtml(item.summary || '');

      return (
        '<div class="ledger-row">' +
          '<div class="ledger-date">' + date + '</div>' +
          '<div class="ledger-tag">' + tag + '</div>' +
          '<div class="ledger-headline">' + headline + '</div>' +
          '<p class="ledger-summary">' + summary + '</p>' +
        '</div>'
      );
    }).join('');
  }

  function formatDate(isoDate) {
    if (!isoDate) return '';
    const d = new Date(isoDate);
    if (isNaN(d.getTime())) return isoDate;
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }).toUpperCase();
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
})();
