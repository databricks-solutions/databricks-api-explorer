/**
 * Patch the Dash debug bar:
 *  - Remove the "Plotly Cloud" button (no id, unlike Errors/Callbacks)
 *  - Inject a "databricks.com" link and the current workspace URL link in its place
 *
 * Workspace host is read from #host-display and re-injected on connection change.
 */
(function () {
  'use strict';

  var DB_COM_ID  = 'db-debug-databricks-link';
  var WS_LINK_ID = 'db-debug-workspace-link';
  var SEP_ID     = 'db-debug-sep';

  function getHost() {
    var el = document.getElementById('host-display');
    if (!el) return null;
    var text = (el.textContent || el.innerText || '').trim();
    return (text && text !== '(not connected)') ? text : null;
  }

  function removeCloudButton(menu) {
    menu.querySelectorAll('button.dash-debug-menu__button:not([id])').forEach(function (btn) {
      btn.parentNode && btn.parentNode.removeChild(btn);
    });
  }

  function removeInjected() {
    [DB_COM_ID, WS_LINK_ID, SEP_ID].forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.parentNode) el.parentNode.removeChild(el);
    });
  }

  function makeLink(id, href, label, title) {
    var a = document.createElement('a');
    a.id = id;
    a.href = href;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    if (title) a.title = title;
    a.style.cssText = [
      'color:#7f4bc4',
      'text-decoration:none',
      'font-size:11px',
      'font-family:Verdana,sans-serif',
      'padding:0 8px',
      'white-space:nowrap',
      'cursor:pointer',
      'transition:color 0.2s ease',
      'display:inline-flex',
      'align-items:center',
      'box-shadow:0 1px #d3dae6',
    ].join(';');
    a.textContent = label;
    a.addEventListener('mouseenter', function () { a.style.color = '#5806c4'; });
    a.addEventListener('mouseleave', function () { a.style.color = '#7f4bc4'; });
    return a;
  }

  function makeSep(id) {
    var s = document.createElement('span');
    s.id = id;
    s.textContent = '|';
    s.style.cssText = 'color:#d3dae6;font-size:11px;user-select:none;';
    return s;
  }

  function injectLinks(menu) {
    if (document.getElementById(DB_COM_ID)) return;

    var host = getHost();

    /* databricks.com link */
    var dbLink = makeLink(DB_COM_ID, 'https://www.databricks.com', 'databricks.com');

    /* separator */
    var sep = makeSep(SEP_ID);

    /* workspace URL link — only if we have a host */
    var wsLink = host
      ? makeLink(
          WS_LINK_ID,
          host.startsWith('http') ? host : 'https://' + host,
          host.replace(/^https?:\/\//, ''),
          host.startsWith('http') ? host : 'https://' + host
        )
      : null;

    /* Insert at the very beginning of the debug menu */
    var ref = menu.firstChild;
    menu.insertBefore(sep,    ref);
    if (wsLink) menu.insertBefore(wsLink, sep);
    menu.insertBefore(dbLink, wsLink || sep);
  }

  function patch() {
    var menu = document.querySelector('.dash-debug-menu__content');
    if (!menu) return;
    removeCloudButton(menu);
    injectLinks(menu);
  }

  /* Re-inject when workspace URL changes */
  function watchHostDisplay() {
    var hostEl = document.getElementById('host-display');
    if (!hostEl) return;
    new MutationObserver(function () {
      removeInjected();
      patch();
    }).observe(hostEl, { childList: true, subtree: true, characterData: true });
  }

  /* Watch for debug menu to appear */
  new MutationObserver(function () {
    if (document.querySelector('.dash-debug-menu__content')) patch();
  }).observe(document.documentElement, { childList: true, subtree: true });

  function init() {
    patch();
    setTimeout(patch, 500);
    setTimeout(patch, 1500);
    setTimeout(watchHostDisplay, 2000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

/* ── Side-panel resize handle ──────────────────────────────────────────── */
(function () {
  var LS_KEY = 'sp-width';

  function clampWidth(w, container) {
    var total = container.offsetWidth;
    return Math.min(total * 0.8, Math.max(total * 0.2, w));
  }

  function applyStoredWidth() {
    var panel = document.getElementById('side-panel');
    if (!panel || panel.classList.contains('sp-collapsed')) return;
    var saved = parseFloat(localStorage.getItem(LS_KEY));
    if (!saved) return;
    var container = panel.parentElement;
    if (!container) return;
    panel.style.width = clampWidth(saved, container) + 'px';
  }

  document.addEventListener('mousedown', function (e) {
    if (!e.target || !e.target.classList.contains('sp-resize-handle')) return;
    e.preventDefault();
    var panel = document.getElementById('side-panel');
    if (!panel) return;
    var container = panel.parentElement;
    if (!container) return;

    var handle = e.target;
    handle.classList.add('dragging');
    document.body.style.userSelect = 'none';
    /* disable transition during drag so it tracks the mouse directly */
    panel.style.transition = 'none';

    var startX = e.clientX;
    var startW = panel.offsetWidth;

    function onMove(e) {
      /* handle is on LEFT edge: drag left → wider, drag right → narrower */
      var w = clampWidth(startW + (startX - e.clientX), container);
      panel.style.width = w + 'px';
    }
    function onUp() {
      handle.classList.remove('dragging');
      document.body.style.userSelect = '';
      panel.style.transition = '';
      var w = parseFloat(panel.style.width);
      if (w) localStorage.setItem(LS_KEY, w);
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    }
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });

  /* Restore saved width whenever a new side-panel is injected by Dash */
  new MutationObserver(function (mutations) {
    for (var i = 0; i < mutations.length; i++) {
      var nodes = mutations[i].addedNodes;
      for (var j = 0; j < nodes.length; j++) {
        if (nodes[j].id === 'side-panel' ||
            (nodes[j].querySelector && nodes[j].querySelector('#side-panel'))) {
          applyStoredWidth();
          return;
        }
      }
    }
  }).observe(document.body, { childList: true, subtree: true });
})();
