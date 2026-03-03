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
      'color:#00d4ff',
      'text-decoration:none',
      'font-size:11px',
      'font-family:JetBrains Mono,Fira Code,monospace',
      'padding:0 8px',
      'opacity:0.75',
      'white-space:nowrap',
      'cursor:pointer',
      'transition:opacity 0.15s ease',
      'display:inline-flex',
      'align-items:center',
    ].join(';');
    a.textContent = label;
    a.addEventListener('mouseenter', function () { a.style.opacity = '1'; });
    a.addEventListener('mouseleave', function () { a.style.opacity = '0.75'; });
    return a;
  }

  function makeSep(id) {
    var s = document.createElement('span');
    s.id = id;
    s.textContent = '|';
    s.style.cssText = 'color:#4b5563;font-size:11px;user-select:none;';
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
