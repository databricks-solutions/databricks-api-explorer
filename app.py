"""Databricks API Explorer -- main Dash application.

This single module defines the complete UI layout (sidebar, topbar,
response viewer, connection panel) and all server- / client-side
callbacks that drive the explorer.

Run modes:
    Local:
        Auth via Databricks CLI profile (SSO / OAuth / PAT) or a
        manually entered workspace URL + token.
    Databricks App:
        Auth via On-Behalf-Of (OBO) using the
        ``x-forwarded-access-token`` header injected by the Databricks
        Apps proxy.

Key internal data flows are documented in the *Architecture* and
*Key Patterns* sections of ``CLAUDE.md``.
"""

import json
import os
import subprocess
import threading
import time

import requests
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, dcc, html, no_update
from flask import request as flask_request

from api_catalog import (
    ACCOUNT_API_CATALOG,
    API_CATALOG,
    ENDPOINT_MAP,
    TOTAL_ACCOUNT_CATEGORIES,
    TOTAL_ACCOUNT_ENDPOINTS,
    TOTAL_CATEGORIES,
    TOTAL_ENDPOINTS,
    extract_chips,
    get_endpoint_by_id,
)
from auth import (
    DATABRICKS_PROFILE,
    IS_DATABRICKS_APP,
    _get_local_config,
    get_account_id,
    get_cli_profiles,
    get_current_user_info,
    get_host,
    get_metastore_name,
    get_workspace_name,
    make_api_call,
    resolve_account_connection,
    resolve_local_connection,
)
from version import VERSION

# ── Dash init ─────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
    title="Databricks API Explorer",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server

app.index_string = '''<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 331'><path d='M283.923 136.449L150.144 213.624L6.88995 131.168L0 134.982V194.844L150.144 281.115L283.923 204.234V235.926L150.144 313.1L6.88995 230.644L0 234.458V244.729L150.144 331L300 244.729V184.867L293.11 181.052L150.144 263.215L16.0766 186.334V154.643L150.144 231.524L300 145.253V86.2713L292.536 81.8697L150.144 163.739L22.9665 90.9663L150.144 17.8998L254.641 78.055L263.828 72.773V65.4371L150.144 0L0 86.2713V95.6613L150.144 181.933L283.923 104.758V136.449Z' fill='%23FF3621'/></svg>">
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>'''

# Default connection config
_DEFAULT_CONN = {"mode": "profile", "profile": DATABRICKS_PROFILE}


# ── JSON Syntax Highlighter ───────────────────────────────────────────────────
# ── Pagination helpers ────────────────────────────────────────────────────────
_SKIP_LIST_KEYS = frozenset({"schemas"})

# Server-side state for background "Load All" pagination
_load_all_state: Dict[str, Any] = {
    "running": False,
    "pages": 0,
    "total_items": 0,
    "items": [],
    "done": False,
    "error": None,
    "list_key": None,
    "initial_data": {},
    "last_req": {},
    "elapsed_ms": 0,
}


def _detect_next_page_token(data: Any) -> Optional[str]:
    """Extract a ``next_page_token`` from a paginated API response.

    Args:
        data: Parsed JSON response body.

    Returns:
        The token string when more pages exist, otherwise ``None``.
    """
    if not isinstance(data, dict):
        return None
    token = data.get("next_page_token")
    return token if token and isinstance(token, str) else None


def _find_list_key(data: dict) -> Optional[str]:
    """Identify the top-level key that holds the item array in a response.

    Skips keys in :data:`_SKIP_LIST_KEYS` (e.g. ``"schemas"``) to
    avoid false positives.

    Args:
        data: A parsed JSON response dict.

    Returns:
        The first key whose value is a ``list``, or ``None``.
    """
    for k, v in data.items():
        if isinstance(v, list) and k not in _SKIP_LIST_KEYS:
            return k
    return None


# ── JSON Tree Viewer ──────────────────────────────────────────────────────────
_TREE_CSS = (
    "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');"
    "html{margin:0;padding:0;background:#050810;height:100%;overflow:hidden;}"
    "body{margin:0;padding:0;background:#050810;height:100%;overflow:auto;}"
    "body{font-family:'JetBrains Mono','Fira Code',ui-monospace,monospace;"
    "font-size:12px;line-height:1.7;color:#94a3b8;}"
    "#toolbar{position:sticky;top:0;background:#050810;border-bottom:1px solid rgba(255,255,255,.07);"
    "padding:5px 14px;display:flex;align-items:center;gap:6px;z-index:10;}"
    "#depth-label{color:#475569;font-size:11px;font-style:italic;flex:1;}"
    ".depth-btn{background:rgba(0,212,255,.07);border:1px solid rgba(0,212,255,.2);color:#00d4ff;"
    "border-radius:4px;width:22px;height:22px;font-size:15px;line-height:1;cursor:pointer;"
    "display:inline-flex;align-items:center;justify-content:center;padding:0;flex-shrink:0;}"
    ".depth-btn:hover{background:rgba(0,212,255,.18);border-color:rgba(0,212,255,.45);}"
    ".depth-btn:disabled{opacity:.3;cursor:default;}"
    "#root{padding:10px 14px;}"
    ".tree-node{display:block;}"
    ".node-header{display:block;}"
    ".toggle{display:inline-block;width:14px;text-align:center;cursor:pointer;"
    "user-select:none;color:#475569;transition:color .1s;}"
    ".toggle:hover{color:#00d4ff;}"
    ".preview{color:#475569;font-style:italic;}"
    ".tree-node:not(.collapsed)>.node-header>.preview{display:none;}"
    ".children{margin-left:20px;display:block;}"
    ".close-line{display:block;}"
    ".tree-node.collapsed>.children,.tree-node.collapsed>.close-line{display:none;}"
    ".kv,.item{display:block;}"
    ".jk{color:#60a5fa}.jv{color:#86efac}.jn{color:#fbbf24}"
    ".jb{color:#c084fc}.jbn{color:#94a3b8}.jp{color:#64748b}"
    ".id-link{cursor:pointer;border-bottom:1px dashed currentColor;}"
    ".id-link:hover{color:#00d4ff!important;border-bottom-color:#00d4ff;"
    "text-shadow:0 0 6px rgba(0,212,255,.5);}"
    ".jts{position:relative;cursor:default;border-bottom:1px dotted #fbbf24;}"
    ".jts:hover .ts-tip{visibility:visible;opacity:1;}"
    ".ts-tip{visibility:hidden;opacity:0;position:absolute;bottom:calc(100% + 4px);left:50%;"
    "transform:translateX(-50%);background:#1e293b;color:#e2e8f0;font-size:11px;"
    "padding:3px 8px;border-radius:4px;white-space:nowrap;pointer-events:none;"
    "border:1px solid rgba(0,212,255,.25);z-index:100;"
    "transition:opacity .15s;}"
    "::-webkit-scrollbar{width:6px;height:6px}"
    "::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:3px}"
    "::-webkit-scrollbar-track{background:transparent}"
    "*{scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.12) transparent}"
    "#search-box{flex:1;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);"
    "color:#e2e8f0;border-radius:4px;padding:2px 8px;font-family:inherit;font-size:11px;"
    "outline:none;min-width:80px;}"
    "#search-box:focus{border-color:rgba(0,212,255,.4);background:rgba(0,212,255,.05);}"
    "#search-box::placeholder{color:#475569;}"
    "#sc{color:#94a3b8;font-size:11px;white-space:nowrap;flex-shrink:0;min-width:44px;text-align:center;}"
    "mark.sh{background:#7c3aed;color:#fff;border-radius:2px;padding:0 1px;}"
    "mark.sh.cur{background:#f59e0b;color:#050810;}"
    ".sep{width:1px;height:16px;background:rgba(255,255,255,.12);flex-shrink:0;}"
)

# Raw string — no Python escape processing; JS unicode escapes work as-is in browser.
_TREE_JS = r"""
var currentDepth=INITIAL_DEPTH;
function mkEl(tag,cls,txt){var e=document.createElement(tag);if(cls)e.className=cls;if(txt!==undefined)e.textContent=txt;return e;}
function idLink(cls,display,gid,par,val,ext){var e=mkEl('span','id-link '+cls,display);e.dataset.gid=gid;e.dataset.par=par;e.dataset.val=val;if(ext)e.dataset.ext=JSON.stringify(ext);e.onclick=function(){var msg={type:'id-link',gid:e.dataset.gid,par:e.dataset.par,val:e.dataset.val};if(e.dataset.ext)msg.ext=JSON.parse(e.dataset.ext);window.parent.postMessage(msg,'*');};return e;}
var TS_KEYS=/time$|_at$|timestamp$|_date$|expiration$|expired$|created$|updated$|deleted$|started$|finished$|modified$|deadline$|_ts$|start_time|end_time|creation_time|last_active_time|expiry_time/i;
function isEpoch(val,pKey){if(typeof val!=='number'||!pKey||!TS_KEYS.test(pKey))return false;if(val>1e12&&val<2e13)return val;if(val>1e9&&val<2e10)return val*1000;return false;}
function tsSpan(cls,display,ms){var w=mkEl('span','jts '+cls);w.textContent=display;var tip=mkEl('span','ts-tip');tip.textContent=new Date(ms).toLocaleString();w.appendChild(tip);return w;}
function renderValue(val,pKey,depth){
  if(val===null)return mkEl('span','jbn','null');
  var t=typeof val;
  if(t==='boolean')return mkEl('span','jb',String(val));
  if(t==='number'){var ms=isEpoch(val,pKey);if(ms)return tsSpan('jn',String(val),ms);var c=pKey&&LOOKUP[pKey]&&LOOKUP[pKey][String(val)];return c?idLink('jn',String(val),c.gid,c.par,String(val),c.ext):mkEl('span','jn',String(val));}
  if(t==='string'){var c2=pKey&&LOOKUP[pKey]&&LOOKUP[pKey][val];return c2?idLink('jv','"'+val+'"',c2.gid,c2.par,val,c2.ext):mkEl('span','jv','"'+val+'"');}
  if(Array.isArray(val))return renderArray(val,depth);
  if(t==='object')return renderObject(val,depth);
  return mkEl('span','jbn',String(val));
}
function fillObj(container,obj,depth){Object.keys(obj).forEach(function(k,i,arr){var kv=mkEl('div','kv');kv.appendChild(mkEl('span','jk','"'+k+'"'));kv.appendChild(mkEl('span','jp',': '));kv.appendChild(renderValue(obj[k],k,depth+1));if(i<arr.length-1)kv.appendChild(mkEl('span','jp',','));container.appendChild(kv);});}
function fillArr(container,arr,depth){arr.forEach(function(v,i,a){var item=mkEl('div','item');item.appendChild(renderValue(v,null,depth+1));if(i<a.length-1)item.appendChild(mkEl('span','jp',','));container.appendChild(item);});}
function buildNode(openCh,closeCh,label,data,depth,isObj){
  var collapsed=depth>=currentDepth;
  var node=mkEl('div',collapsed?'tree-node collapsed':'tree-node');
  node.dataset.depth=depth;
  var hdr=mkEl('div','node-header');
  var btn=mkEl('span','toggle',collapsed?'\u25b8':'\u25be');
  hdr.appendChild(btn);hdr.appendChild(mkEl('span','jp',openCh));hdr.appendChild(mkEl('span','preview jp',' '+label+' '+closeCh));
  node.appendChild(hdr);
  var rendered=false;
  function ensure(){if(rendered)return;rendered=true;var ch=mkEl('div','children');isObj?fillObj(ch,data,depth):fillArr(ch,data,depth);var cl=mkEl('div','close-line');cl.appendChild(mkEl('span','jp',closeCh));node.appendChild(ch);node.appendChild(cl);}
  if(!collapsed)ensure();
  node._ensure=ensure;
  btn.onclick=function(){if(node.classList.contains('collapsed'))ensure();node.classList.toggle('collapsed');btn.textContent=node.classList.contains('collapsed')?'\u25b8':'\u25be';};
  return node;
}
function renderObject(obj,depth){var k=Object.keys(obj);if(!k.length)return mkEl('span','jp','{}');return buildNode('{','}',k.length+(k.length===1?' key':' keys'),obj,depth,true);}
function renderArray(arr,depth){if(!arr.length)return mkEl('span','jp','[]');return buildNode('[',']',arr.length+' items',arr,depth,false);}
function applyCollapseLevel(newDepth){
  currentDepth=newDepth;
  document.querySelectorAll('.tree-node').forEach(function(node){
    var d=parseInt(node.dataset.depth);
    var btn=node.querySelector(':scope > .node-header > .toggle');
    if(d>=currentDepth){
      node.classList.add('collapsed');
      if(btn)btn.textContent='\u25b8';
    } else if(node.classList.contains('collapsed')){
      if(node._ensure)node._ensure();
      node.classList.remove('collapsed');
      if(btn)btn.textContent='\u25be';
    }
  });
  var lbl=document.getElementById('depth-label');
  if(lbl)lbl.textContent='Collapse at depth \u2265 '+currentDepth;
  var btnMinus=document.getElementById('btn-minus');
  if(btnMinus)btnMinus.disabled=(currentDepth<=1);
}
function changeDepth(delta){applyCollapseLevel(Math.max(1,currentDepth+delta));}
var searchMatches=[];var searchIdx=-1;
function clearHighlights(){
  document.querySelectorAll('mark.sh').forEach(function(m){
    var p=m.parentNode;if(!p)return;
    p.replaceChild(document.createTextNode(m.textContent),m);
    p.normalize();
  });
  searchMatches=[];searchIdx=-1;
}
function doSearch(q){
  clearHighlights();
  var sc=document.getElementById('sc');
  if(!q){if(sc)sc.textContent='';return;}
  q=q.toLowerCase();
  document.querySelectorAll('.tree-node.collapsed').forEach(function(nd){
    if(nd._ensure)nd._ensure();
    nd.classList.remove('collapsed');
    var btn=nd.querySelector(':scope > .node-header > .toggle');
    if(btn)btn.textContent='\u25be';
  });
  var root=document.getElementById('root');
  var tw=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null,false);
  var toProc=[];var nd;
  while((nd=tw.nextNode())){if(nd.textContent.toLowerCase().indexOf(q)!==-1)toProc.push(nd);}
  toProc.forEach(function(tn){
    var txt=tn.textContent;var low=txt.toLowerCase();
    var frag=document.createDocumentFragment();var last=0;var i;
    while((i=low.indexOf(q,last))!==-1){
      if(i>last)frag.appendChild(document.createTextNode(txt.slice(last,i)));
      var mk=document.createElement('mark');mk.className='sh';mk.textContent=txt.slice(i,i+q.length);
      frag.appendChild(mk);searchMatches.push(mk);last=i+q.length;
    }
    if(last<txt.length)frag.appendChild(document.createTextNode(txt.slice(last)));
    tn.parentNode.replaceChild(frag,tn);
  });
  if(searchMatches.length>0){searchIdx=0;activateMatch(0);}
  updateCounter();
}
function activateMatch(i){
  searchMatches.forEach(function(m,j){m.classList.toggle('cur',j===i);});
  if(searchMatches[i])searchMatches[i].scrollIntoView({behavior:'smooth',block:'center'});
}
function updateCounter(){
  var c=document.getElementById('sc');if(!c)return;
  c.textContent=searchMatches.length>0?(searchIdx+1)+'\u2009/\u2009'+searchMatches.length:'';
}
function searchNav(d){
  if(!searchMatches.length)return;
  searchIdx=(searchIdx+d+searchMatches.length)%searchMatches.length;
  activateMatch(searchIdx);updateCounter();
}
document.addEventListener('DOMContentLoaded',function(){
  document.getElementById('root').appendChild(renderValue(DATA,null,0));
  applyCollapseLevel(currentDepth);
});
"""


def _build_json_tree_html(data: Any, chips: Optional[List[Dict]] = None) -> str:
    """Build a self-contained HTML document with a collapsible JSON tree.

    The tree is rendered entirely in vanilla JavaScript (no React /
    Dash).  Nodes at depth >= 3 are auto-collapsed and children are
    lazy-rendered on first expand for performance with large payloads.

    If *chips* are provided, matching field values become clickable
    inline links that post a ``window.parent.postMessage`` event
    consumed by callback 16 (``handle_iframe_link_click``).

    Args:
        data: Any JSON-serialisable value to render.
        chips: Optional list of chip dicts (from
            :func:`api_catalog.extract_chips`) used to build the
            ``LOOKUP`` table that drives inline ID links.

    Returns:
        A complete ``<!DOCTYPE html>`` string suitable for use as the
        ``srcDoc`` of an ``<iframe>``.
    """
    link_lookup: Dict[str, Dict[str, Dict]] = {}
    if chips:
        for chip in chips:
            field = chip["id_field"]
            if field not in link_lookup:
                link_lookup[field] = {}
            entry: Dict[str, Any] = {
                "gid": chip["get_id"],
                "par": chip["param"],
            }
            if chip.get("extras"):
                entry["ext"] = chip["extras"]
            link_lookup[field][str(chip["value"])] = entry
    data_js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</script>", r"<\/script>")
    lookup_js = json.dumps(link_lookup, ensure_ascii=False).replace("</script>", r"<\/script>")
    return "".join([
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<style>", _TREE_CSS, "</style>",
        "</head><body>",
        "<div id='toolbar'>",
        "<button class='depth-btn' id='btn-minus' onclick='changeDepth(-1)' title='Collapse one level more'>\u2212</button>",
        "<button class='depth-btn' onclick='changeDepth(+1)' title='Expand one level more'>+</button>",
        "<span id='depth-label'></span>",
        "<div class='sep'></div>",
        "<input id='search-box' type='text' placeholder='\U0001f50d\u2009Search\u2026' "
        "oninput='doSearch(this.value)' "
        "onkeydown='if(event.key===\"Enter\"){searchNav(event.shiftKey?-1:1);event.preventDefault();}' />",
        "<span id='sc'></span>",
        "<button class='depth-btn' onclick='searchNav(-1)' title='Previous match (Shift+Enter)'>\u2191</button>",
        "<button class='depth-btn' onclick='searchNav(1)' title='Next match (Enter)'>\u2193</button>",
        "</div>",
        "<div id='root'></div><script>",
        "const DATA=", data_js, ";",
        "const LOOKUP=", lookup_js, ";",
        "const INITIAL_DEPTH=3;",
        _TREE_JS,
        "</script></body></html>",
    ])


# ── UI Helpers ────────────────────────────────────────────────────────────────
METHOD_COLORS = {"GET": "info", "POST": "warning", "PUT": "primary", "DELETE": "danger", "PATCH": "success"}


def method_badge(method: str) -> dbc.Badge:
    """Return a colour-coded Bootstrap badge for an HTTP method.

    Args:
        method: HTTP verb (e.g. ``"GET"``, ``"POST"``).

    Returns:
        A :class:`dbc.Badge` component.
    """
    return dbc.Badge(method, color=METHOD_COLORS.get(method, "secondary"), className="method-badge")


_TOKEN_CACHE_PATH = os.path.expanduser("~/.databricks/token-cache.json")


def _load_token_cache() -> dict:
    """Load the Databricks CLI token cache from disk.

    Returns:
        A dict with ``version`` and ``tokens`` keys.  Returns a fresh
        empty cache if the file does not exist.
    """
    if not os.path.exists(_TOKEN_CACHE_PATH):
        return {"version": 1, "tokens": {}}
    with open(_TOKEN_CACHE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save_token_cache(cache: dict) -> None:
    """Persist the token cache dict back to disk.

    Args:
        cache: The full cache dict (must contain ``version`` and
            ``tokens``).
    """
    with open(_TOKEN_CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2)


def _find_cache_entry(tokens: dict, host: str) -> Optional[dict]:
    """Find a token-cache entry matching *host*.

    Looks up by exact key first, then falls back to decoding the JWT
    ``iss`` claim of each cached token.

    Args:
        tokens: The ``tokens`` sub-dict from the token cache.
        host: Workspace URL to match (with or without trailing ``/``).

    Returns:
        The matching cache entry dict, or ``None``.
    """
    import base64 as _b64
    h = host.rstrip("/")
    entry = tokens.get(h) or tokens.get(h + "/")
    if entry:
        return entry
    for _v in tokens.values():
        try:
            payload = _v["access_token"].split(".")[1]
            payload += "=" * (-len(payload) % 4)
            iss = json.loads(_b64.urlsafe_b64decode(payload)).get("iss", "")
            if h in iss:
                return _v
        except Exception:
            pass
    return None


def _is_token_expired(entry: dict) -> bool:
    """Check whether a cached token has expired.

    Args:
        entry: A single token-cache entry containing an ``expiry``
            ISO-8601 timestamp string.

    Returns:
        ``True`` if the token is expired or the expiry cannot be
        parsed.
    """
    from datetime import datetime, timezone
    s = entry.get("expiry", "")
    if not s:
        return True
    try:
        exp = datetime.fromisoformat(s)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp <= datetime.now(timezone.utc)
    except Exception:
        return True


def _try_token_refresh(entry: dict, host: str) -> Optional[str]:
    """Attempt a silent OAuth token refresh using the stored refresh token.

    On success the *entry* dict is mutated in place and the updated
    token cache is persisted to disk.

    Args:
        entry: A token-cache entry that must contain
            ``refresh_token``.
        host: Workspace URL used to discover the OIDC token endpoint.

    Returns:
        The new access token string, or ``None`` on failure.
    """
    from datetime import datetime, timezone, timedelta
    rt = entry.get("refresh_token", "")
    if not rt:
        return None
    try:
        oidc = requests.get(
            f"{host}/oidc/.well-known/oauth-authorization-server", timeout=10
        ).json()
        tr = requests.post(oidc["token_endpoint"], data={
            "grant_type": "refresh_token",
            "client_id": "databricks-cli",
            "refresh_token": rt,
        }, timeout=30)
        if not tr.ok:
            return None
        d = tr.json()
        token = d.get("access_token", "")
        if token:
            entry["access_token"] = token
            entry["refresh_token"] = d.get("refresh_token", rt)
            entry["expiry"] = (
                datetime.now(timezone.utc) + timedelta(seconds=d.get("expires_in", 3600))
            ).isoformat()
            cache = _load_token_cache()
            cache["tokens"][host.rstrip("/")] = entry
            _save_token_cache(cache)
        return token or None
    except Exception:
        return None


def _sso_try_cached(host: str) -> Optional[str]:
    """Return a valid token from the local cache, refreshing if needed.

    Args:
        host: Workspace URL to look up.

    Returns:
        A valid access token string, or ``None`` when no usable token
        is available.
    """
    cache = _load_token_cache()
    entry = _find_cache_entry(cache.get("tokens", {}), host)
    if not entry:
        return None
    if not _is_token_expired(entry):
        return entry["access_token"]
    return _try_token_refresh(entry, host)


# ── Background SSO browser flow ──────────────────────────────────────

_sso_result: Dict[str, Any] = {}  # host → {"token": ..., "error": ..., "done": bool}
_sso_lock = threading.Lock()


def _sso_browser_flow(host: str) -> None:
    """Run the blocking browser-based OAuth flow in a background thread.

    Opens the system browser for SSO login, waits for the redirect
    callback on ``localhost:8020``, and stores the resulting token (or
    error) in :data:`_sso_result` under ``host``.

    Args:
        host: Workspace URL to authenticate against.
    """
    from databricks.sdk.oauth import OAuthClient
    from datetime import datetime, timezone, timedelta
    import signal
    try:
        # databricks-cli client only allows http://localhost:8020 as redirect
        port = 8020
        # Kill any leftover listener on this port
        try:
            for pid in subprocess.check_output(
                ["lsof", "-ti", f":{port}"], stderr=subprocess.DEVNULL
            ).decode().split():
                os.kill(int(pid.strip()), signal.SIGTERM)
            time.sleep(0.3)
        except Exception:
            pass
        redirect_url = f"http://localhost:{port}"
        client = OAuthClient.from_host(
            host=host, client_id="databricks-cli",
            redirect_url=redirect_url,
            scopes=["all-apis", "offline_access"],
        )
        consent = client.initiate_consent()
        if not consent:
            with _sso_lock:
                _sso_result[host] = {"token": None, "error": "Could not initiate OAuth.", "done": True}
            return
        creds = consent.launch_external_browser()
        tok_obj = creds.token()
        token = tok_obj.access_token
        if token:
            cache = _load_token_cache()
            expiry = tok_obj.expiry or (datetime.now(timezone.utc) + timedelta(seconds=3600))
            cache["tokens"][host.rstrip("/")] = {
                "access_token": token,
                "token_type": "Bearer",
                "refresh_token": tok_obj.refresh_token or "",
                "expiry": expiry.isoformat(),
                "expires_in": 3600,
            }
            _save_token_cache(cache)
        with _sso_lock:
            _sso_result[host] = {"token": token, "error": None, "done": True}
    except Exception as e:
        with _sso_lock:
            _sso_result[host] = {"token": None, "error": str(e), "done": True}


def _resolve_conn(
    conn_config: Optional[Dict],
) -> tuple:
    """Return ``(host, token)`` for the current runtime mode.

    In Databricks App mode the host and token come from environment
    variables and request headers; in local mode they are resolved via
    :func:`auth.resolve_local_connection`.

    Args:
        conn_config: The ``conn-config`` Dash store value.

    Returns:
        A ``(host, token)`` tuple.
    """
    if IS_DATABRICKS_APP:
        return get_host(), flask_request.headers.get("x-forwarded-access-token")
    return resolve_local_connection(conn_config or _DEFAULT_CONN)


def _accounts_host(workspace_host: str) -> str:
    """Derive the Databricks accounts console URL from a workspace host.

    Args:
        workspace_host: The workspace URL (e.g.
            ``https://adb-123.azuredatabricks.net``).

    Returns:
        The accounts console URL (e.g.
        ``https://accounts.azuredatabricks.net`` for Azure or
        ``https://accounts.cloud.databricks.com`` for AWS/GCP).
    """
    h = (workspace_host or "").lower()
    if "azuredatabricks" in h:
        return "https://accounts.azuredatabricks.net"
    if ".gcp.databricks.com" in h:
        return "https://accounts.gcp.databricks.com"
    return "https://accounts.cloud.databricks.com"


def build_response_panel(
    result: Dict[str, Any],
    chips: Optional[List[Dict]] = None,
) -> html.Div:
    """Assemble the full response viewer panel for an API call result.

    Includes a status badge, timing label, item count, the JSON tree
    iframe, and an optional side panel of clickable chip items.

    Args:
        result: Normalised result dict from :func:`auth.make_api_call`.
        chips: Optional chip list from :func:`api_catalog.extract_chips`
            for rendering the side panel and inline ID links.

    Returns:
        A Dash ``html.Div`` component tree.
    """
    code, ms, data = result["status_code"], result["elapsed_ms"], result["data"]
    if 200 <= code < 300:
        status_color, icon = "success", "bi-check-circle-fill"
    elif code == 0:
        status_color, icon = "danger", "bi-x-octagon-fill"
    elif 400 <= code < 500:
        status_color, icon = "danger", "bi-x-circle-fill"
    else:
        status_color, icon = "warning", "bi-exclamation-circle-fill"

    item_count = ""
    if isinstance(data, list):
        item_count = f" · {len(data)} items"
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                item_count = f" · {len(v)} items"
                break

    # CSV response: render as a scrollable HTML table
    csv_text = result.get("_csv")
    if csv_text:
        import csv as _csv_mod
        import io
        reader = _csv_mod.reader(io.StringIO(csv_text))
        rows = list(reader)
        if rows:
            headers = rows[0]
            table_header = html.Thead(html.Tr([html.Th(h) for h in headers]))
            table_body = html.Tbody([
                html.Tr([html.Td(cell) for cell in row])
                for row in rows[1:]
            ])
            item_count = f" · {len(rows) - 1} rows"
            viewer = html.Div([
                html.Table([table_header, table_body], className="csv-table"),
            ], className="csv-viewer")
        else:
            viewer = html.Iframe(
                srcDoc=_build_json_tree_html(data, chips),
                style={"width": "100%", "height": "100%", "border": "none", "display": "block"},
            )
    else:
        viewer = html.Iframe(
            srcDoc=_build_json_tree_html(data, chips),
            style={"width": "100%", "height": "100%", "border": "none", "display": "block"},
        )
    wrapper_cls = "json-viewer-wrapper json-viewer-iframe"

    # Build side panel with chip items
    if chips:
        sp_items = []
        for i, chip in enumerate(chips):
            has_label = chip["label"] != chip["title"]
            name_text = chip["label"]
            id_text = chip["title"] if has_label else ""
            text_children = [html.Span(name_text, className="sp-name")]
            if id_text:
                text_children.append(html.Span(id_text, className="sp-id"))
            item_children = [
                html.Button(
                    text_children,
                    id={"type": "sp-item", "index": i},
                    n_clicks=0,
                    className="sp-item-main",
                    title=f"{chip['label']} · {chip['title']}",
                ),
            ]
            for j, action in enumerate(chip.get("actions") or []):
                item_children.append(html.Button(
                    html.I(className=f"bi {action['icon']}"),
                    id={"type": "sp-action", "index": i, "action": j},
                    n_clicks=0,
                    className="sp-action-btn",
                    title=action["title"],
                ))
            sp_items.append(html.Div(item_children, className="sp-item"))
        header_children = [
            html.Button(
                html.I(className="bi bi-layout-sidebar-reverse"),
                id="sp-toggle-btn",
                className="sp-toggle",
                n_clicks=0,
                title="Collapse/expand panel",
            ),
            html.Span(f"{len(chips)} items", className="sp-header-text"),
        ]
        side_panel = html.Div([
            html.Div(className="sp-resize-handle"),
            html.Div(header_children, className="sp-header"),
            html.Div(sp_items, className="sp-list"),
        ], id="side-panel", className="side-panel")
    else:
        side_panel = None

    body_children = [html.Div(viewer, className=wrapper_cls)]
    if side_panel:
        body_children.append(side_panel)

    return html.Div([
        html.Div([
            dbc.Badge([html.I(className=f"bi {icon} me-1"), str(code) if code else "Error"],
                      color=status_color, className="status-badge"),
            html.Span(f"{ms:,}ms", className="timing-label font-mono ms-2"),
            html.Span(item_count, className="timing-label") if item_count else None,
            html.Span(result.get("url", ""), className="response-url ms-auto"),
        ], className="response-meta"),
        html.Div(body_children, className="response-body"),
    ], className="response-container")


def build_error_panel(message: str) -> html.Div:
    """Build a styled error message panel.

    Args:
        message: Plain-text error description.

    Returns:
        A Dash ``html.Div`` with the error layout.
    """
    return html.Div([
        html.Div([
            html.I(className="bi bi-exclamation-triangle-fill me-2 text-danger"),
            html.Span(message, className="text-danger"),
        ], className="error-panel"),
    ], className="response-container")


def build_param_form(
    endpoint: Dict[str, Any],
    prefill: Optional[Dict[str, str]] = None,
) -> html.Div:
    """Generate the parameter input form for an endpoint.

    Renders type-aware input fields for each declared parameter
    (text vs. number), plus a JSON body textarea for ``POST``
    endpoints.

    Args:
        endpoint: Endpoint definition dict from
            :data:`api_catalog.API_CATALOG`.
        prefill: Optional mapping of ``{param_name: value}`` used to
            pre-populate fields when navigating via an inline ID link.

    Returns:
        A Dash ``html.Div`` containing the form rows.
    """
    params: List[Dict] = endpoint.get("params", [])
    method: str = endpoint.get("method", "GET")
    body_template: Optional[str] = endpoint.get("body")
    prefill = prefill or {}
    rows = []

    for p in params:
        label_row = html.Div([
            html.Span(p["name"], className="param-name"),
            dbc.Badge("required", color="danger", className="param-badge") if p.get("required")
            else dbc.Badge("optional", color="secondary", className="param-badge"),
        ], className="param-label")
        inp = dbc.Input(
            id={"type": "param-input", "name": p["name"]},
            type="number" if p["type"] == "integer" else "text",
            placeholder=p.get("description", ""),
            value=str(prefill[p["name"]]) if p["name"] in prefill else (p.get("default", "") or ""),
            className="param-input font-mono",
        )
        rows.append(html.Div([label_row, html.Div(p.get("description", ""), className="param-desc"), inp], className="param-row"))

    if not params and not body_template:
        rows.append(html.Div([
            html.I(className="bi bi-check-circle-fill me-2 text-success"),
            "No parameters required — click Execute to call this endpoint.",
        ], className="no-params"))

    show_body = body_template is not None or method == "POST"
    if show_body:
        body_value = body_template or "{}"
        if prefill and body_value:
            try:
                body_obj = json.loads(body_value)
                for k, v in prefill.items():
                    if k in body_obj:
                        body_obj[k] = v
                body_value = json.dumps(body_obj, indent=2)
            except (json.JSONDecodeError, TypeError):
                pass
        rows.append(html.Hr(className="divider"))
        rows.append(html.Div([
            html.Div([
                html.Span("Request Body", className="param-name"),
                dbc.Badge("JSON", color="info", className="param-badge ms-2"),
            ], className="param-label mb-1"),
            dbc.Textarea(id="body-textarea", value=body_value, className="body-textarea font-mono mt-1", rows=8),
        ], className="param-row"))
    else:
        rows.append(dbc.Textarea(id="body-textarea", value="", style={"display": "none"}))

    return html.Div(rows, className="param-form")


# ── Sidebar ───────────────────────────────────────────────────────────────────
def _build_accordion_items(catalog: Dict[str, Any]) -> list:
    """Build accordion items for a given API catalog.

    Args:
        catalog: Either :data:`API_CATALOG` or
            :data:`ACCOUNT_API_CATALOG`.

    Returns:
        A list of :class:`dbc.AccordionItem` components.
    """
    items = []
    for cat_name, cat in catalog.items():
        btns = [
            html.Button(
                [html.Span(ep["method"], className=f"ep-method ep-{ep['method'].lower()}"),
                 html.Span(ep["name"], className="ep-name")],
                id={"type": "endpoint-btn", "id": ep["id"]},
                n_clicks=0,
                className="endpoint-btn",
                title=ep.get("description", ""),
            )
            for ep in cat["endpoints"]
        ]
        title_el = html.Span([
            html.I(className=f"bi {cat['icon']} me-2", style={"color": cat["color"]}),
            cat_name,
            dbc.Badge(str(len(cat["endpoints"])), color="secondary", className="ms-auto endpoint-count"),
        ], className="cat-header d-flex align-items-center w-100")
        items.append(dbc.AccordionItem(html.Div(btns, className="endpoint-list"), title=title_el))
    return items


def build_sidebar() -> html.Div:
    """Build the left sidebar with scope switcher and categorised endpoint buttons.

    A toggle at the top switches between Workspace APIs and Account
    APIs.  Each category becomes a collapsible accordion item.  A
    search input filters the visible buttons (callback 13).

    Returns:
        A Dash ``html.Div`` containing the sidebar layout.
    """
    scope_switcher = html.Div([
        html.Button(
            [html.I(className="bi bi-pc-display me-1"), "Workspace"],
            id="scope-workspace-btn",
            n_clicks=0,
            className="scope-btn scope-btn-active",
        ),
        html.Button(
            [html.I(className="bi bi-globe me-1"), "Account"],
            id="scope-account-btn",
            n_clicks=0,
            className="scope-btn",
        ),
    ], className="scope-switcher")

    return html.Div([
        scope_switcher,
        html.Div([
            html.I(className="bi bi-search"),
            dbc.Input(id="search-input", placeholder="Search APIs…", type="text", className="sidebar-search"),
        ], className="search-wrapper"),
        dbc.Accordion(
            _build_accordion_items(API_CATALOG),
            start_collapsed=True,
            id="api-accordion",
            className="api-accordion",
        ),
    ], id="sidebar", className="sidebar")


# ── Top Bar ───────────────────────────────────────────────────────────────────
_MODE_BADGE = html.Button(
    dbc.Badge(
        [html.I(className="bi bi-cloud-fill me-1"), "Databricks App"] if IS_DATABRICKS_APP
        else [html.I(className="bi bi-laptop me-1"), "Local Mode"],
        color="info" if IS_DATABRICKS_APP else "warning",
        className="mode-badge",
    ),
    id="mode-badge-btn", n_clicks=0,
    className="mode-badge-btn",
)

# ── Theme definitions ────────────────────────────────────────────────────────
_THEMES = {
    "midnight": {"label": "Midnight", "dark": True, "icon": "bi-moon-stars-fill",
                 "bg-void": "#050810", "bg-dark": "#080c18", "bg-panel": "#0d1225",
                 "bg-card": "rgba(255,255,255,0.028)", "bg-hover": "rgba(255,255,255,0.055)",
                 "bg-active": "rgba(0,212,255,0.09)", "border": "rgba(255,255,255,0.07)",
                 "border-hi": "rgba(0,212,255,0.45)", "text-hi": "#f8fafc",
                 "text-1": "#e2e8f0", "text-2": "#94a3b8", "text-3": "#4b5563",
                 "accent": "#00d4ff", "card-bg": "#1a1d23"},
    "obsidian": {"label": "Obsidian", "dark": True, "icon": "bi-gem",
                 "bg-void": "#0a0a0a", "bg-dark": "#111111", "bg-panel": "#181818",
                 "bg-card": "rgba(255,255,255,0.035)", "bg-hover": "rgba(255,255,255,0.06)",
                 "bg-active": "rgba(168,85,247,0.1)", "border": "rgba(255,255,255,0.08)",
                 "border-hi": "rgba(168,85,247,0.5)", "text-hi": "#fafafa",
                 "text-1": "#e0e0e0", "text-2": "#9e9e9e", "text-3": "#555555",
                 "accent": "#a855f7", "card-bg": "#1e1e1e"},
    "deep-ocean": {"label": "Deep Ocean", "dark": True, "icon": "bi-water",
                   "bg-void": "#020617", "bg-dark": "#0f172a", "bg-panel": "#1e293b",
                   "bg-card": "rgba(255,255,255,0.03)", "bg-hover": "rgba(255,255,255,0.05)",
                   "bg-active": "rgba(56,189,248,0.1)", "border": "rgba(255,255,255,0.06)",
                   "border-hi": "rgba(56,189,248,0.5)", "text-hi": "#f8fafc",
                   "text-1": "#cbd5e1", "text-2": "#64748b", "text-3": "#475569",
                   "accent": "#38bdf8", "card-bg": "#1e293b"},
    "aurora": {"label": "Aurora", "dark": True, "icon": "bi-stars",
               "bg-void": "#030712", "bg-dark": "#0c1427", "bg-panel": "#162032",
               "bg-card": "rgba(255,255,255,0.03)", "bg-hover": "rgba(255,255,255,0.055)",
               "bg-active": "rgba(16,185,129,0.1)", "border": "rgba(255,255,255,0.07)",
               "border-hi": "rgba(16,185,129,0.5)", "text-hi": "#ecfdf5",
               "text-1": "#d1fae5", "text-2": "#6ee7b7", "text-3": "#34d399",
               "accent": "#10b981", "card-bg": "#1a2332"},
    "snowlight": {"label": "Snowlight", "dark": False, "icon": "bi-sun-fill",
                  "bg-void": "#f8fafc", "bg-dark": "#f1f5f9", "bg-panel": "#ffffff",
                  "bg-card": "rgba(0,0,0,0.03)", "bg-hover": "rgba(0,0,0,0.05)",
                  "bg-active": "rgba(99,102,241,0.08)", "border": "rgba(0,0,0,0.1)",
                  "border-hi": "rgba(99,102,241,0.5)", "text-hi": "#0f172a",
                  "text-1": "#1e293b", "text-2": "#64748b", "text-3": "#94a3b8",
                  "accent": "#6366f1", "card-bg": "#ffffff"},
    "paper": {"label": "Paper", "dark": False, "icon": "bi-file-earmark-text",
              "bg-void": "#fafaf9", "bg-dark": "#f5f5f4", "bg-panel": "#ffffff",
              "bg-card": "rgba(0,0,0,0.025)", "bg-hover": "rgba(0,0,0,0.04)",
              "bg-active": "rgba(234,88,12,0.08)", "border": "rgba(0,0,0,0.08)",
              "border-hi": "rgba(234,88,12,0.45)", "text-hi": "#1c1917",
              "text-1": "#292524", "text-2": "#78716c", "text-3": "#a8a29e",
              "accent": "#ea580c", "card-bg": "#ffffff"},
    "cloud": {"label": "Cloud", "dark": False, "icon": "bi-cloud-sun-fill",
              "bg-void": "#f0f9ff", "bg-dark": "#e0f2fe", "bg-panel": "#ffffff",
              "bg-card": "rgba(0,0,0,0.02)", "bg-hover": "rgba(0,0,0,0.04)",
              "bg-active": "rgba(14,165,233,0.08)", "border": "rgba(0,0,0,0.08)",
              "border-hi": "rgba(14,165,233,0.45)", "text-hi": "#0c4a6e",
              "text-1": "#0e7490", "text-2": "#64748b", "text-3": "#94a3b8",
              "accent": "#0ea5e9", "card-bg": "#ffffff"},
}

_LANGUAGES = [
    {"label": "English", "value": "en"},
    {"label": "Deutsch", "value": "de"},
    {"label": "Francais", "value": "fr"},
    {"label": "Espanol", "value": "es"},
    {"label": "Italiano", "value": "it"},
    {"label": "Portugues", "value": "pt"},
    {"label": "Nederlands", "value": "nl"},
    {"label": "Japanese", "value": "ja"},
    {"label": "Korean", "value": "ko"},
    {"label": "Chinese (Simplified)", "value": "zh"},
]

# ── Settings Modal ───────────────────────────────────────────────────────────
_dark_themes = [t for t in _THEMES.values() if t["dark"]]
_light_themes = [t for t in _THEMES.values() if not t["dark"]]

def _theme_card(tid: str, t: dict) -> html.Div:
    """Build a clickable theme preview card."""
    return html.Button([
        html.Div([
            html.Div(className="theme-swatch-bar", style={"background": t["accent"]}),
            html.Div(className="theme-swatch-bg", style={"background": t["bg-void"]}),
        ], className="theme-swatch"),
        html.Div([
            html.I(className=f"bi {t['icon']} me-1"),
            t["label"],
        ], className="theme-card-label"),
    ], id={"type": "theme-card", "idx": tid}, className="theme-card", n_clicks=0,
       **{"data-theme": tid})

_SETTINGS_MODAL = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle([
        html.I(className="bi bi-gear-fill me-2"),
        "Settings",
    ])),
    dbc.ModalBody([
        # ── Timezone ──────────────────────────
        html.Div([
            html.Label([html.I(className="bi bi-globe2 me-2"), "Timezone"],
                       className="settings-label"),
            dbc.Select(
                id="settings-timezone",
                options=[
                    {"label": "(UTC-12:00) Baker Island", "value": "Etc/GMT+12"},
                    {"label": "(UTC-11:00) Pago Pago", "value": "Pacific/Pago_Pago"},
                    {"label": "(UTC-10:00) Honolulu", "value": "Pacific/Honolulu"},
                    {"label": "(UTC-09:00) Anchorage", "value": "America/Anchorage"},
                    {"label": "(UTC-08:00) Los Angeles", "value": "America/Los_Angeles"},
                    {"label": "(UTC-07:00) Denver", "value": "America/Denver"},
                    {"label": "(UTC-06:00) Chicago", "value": "America/Chicago"},
                    {"label": "(UTC-05:00) New York", "value": "America/New_York"},
                    {"label": "(UTC-04:00) Santiago", "value": "America/Santiago"},
                    {"label": "(UTC-03:00) Sao Paulo", "value": "America/Sao_Paulo"},
                    {"label": "(UTC-02:00) South Georgia", "value": "Atlantic/South_Georgia"},
                    {"label": "(UTC-01:00) Azores", "value": "Atlantic/Azores"},
                    {"label": "(UTC+00:00) London / UTC", "value": "Europe/London"},
                    {"label": "(UTC+01:00) Berlin / Paris", "value": "Europe/Berlin"},
                    {"label": "(UTC+02:00) Helsinki / Cairo", "value": "Europe/Helsinki"},
                    {"label": "(UTC+03:00) Moscow / Istanbul", "value": "Europe/Moscow"},
                    {"label": "(UTC+04:00) Dubai", "value": "Asia/Dubai"},
                    {"label": "(UTC+05:00) Karachi", "value": "Asia/Karachi"},
                    {"label": "(UTC+05:30) Mumbai", "value": "Asia/Kolkata"},
                    {"label": "(UTC+06:00) Dhaka", "value": "Asia/Dhaka"},
                    {"label": "(UTC+07:00) Bangkok", "value": "Asia/Bangkok"},
                    {"label": "(UTC+08:00) Singapore / Shanghai", "value": "Asia/Singapore"},
                    {"label": "(UTC+09:00) Tokyo / Seoul", "value": "Asia/Tokyo"},
                    {"label": "(UTC+10:00) Sydney", "value": "Australia/Sydney"},
                    {"label": "(UTC+11:00) Noumea", "value": "Pacific/Noumea"},
                    {"label": "(UTC+12:00) Auckland", "value": "Pacific/Auckland"},
                ],
                value="Europe/Berlin",
                className="settings-select",
            ),
        ], className="settings-group"),

        # ── Language ──────────────────────────
        html.Div([
            html.Label([html.I(className="bi bi-translate me-2"), "Language"],
                       className="settings-label"),
            dbc.Select(
                id="settings-language",
                options=_LANGUAGES,
                value="en",
                className="settings-select",
            ),
        ], className="settings-group"),

        # ── Theme ─────────────────────────────
        html.Div([
            html.Label([html.I(className="bi bi-palette-fill me-2"), "Theme"],
                       className="settings-label"),

            html.Div("Dark", className="theme-section-label"),
            html.Div(
                [_theme_card(tid, t) for tid, t in _THEMES.items() if t["dark"]],
                className="theme-grid",
            ),
            html.Div("Light", className="theme-section-label mt-3"),
            html.Div(
                [_theme_card(tid, t) for tid, t in _THEMES.items() if not t["dark"]],
                className="theme-grid",
            ),
        ], className="settings-group"),
    ]),
], id="settings-modal", is_open=False, centered=True, className="settings-modal")

_DEPLOY_MODAL = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle([
        html.I(className="bi bi-rocket-takeoff me-2"),
        "Deploy API Explorer",
    ])),
    dbc.ModalBody([
        html.H6([html.I(className="bi bi-laptop me-2"), "Local Development"], className="deploy-section-title"),
        html.P("Run the app locally with Databricks CLI authentication:", className="text-muted small mb-2"),
        html.Pre(
            "# Install dependencies\n"
            "pip install -r requirements.txt\n\n"
            "# Authenticate to your workspace\n"
            "databricks auth login --host https://<workspace-url>\n\n"
            "# Start the app\n"
            "python app.py\n\n"
            "# Open http://localhost:8050",
            className="deploy-code",
        ),
        html.P([
            "The app reads CLI profiles from ",
            html.Code("~/.databrickscfg"),
            " and lets you switch between workspaces in the UI.",
        ], className="text-muted small mb-4"),

        html.Hr(className="divider"),

        html.H6([html.I(className="bi bi-cloud-fill me-2"), "Databricks App Deployment"], className="deploy-section-title"),
        html.P("Deploy as a managed Databricks App with On-Behalf-Of (OBO) authentication:", className="text-muted small mb-2"),

        html.Div([html.Span("Option A", className="deploy-option-label"), " — Asset Bundles (recommended)"], className="deploy-option-title"),
        html.Pre(
            "# Deploy via Databricks Asset Bundles\n"
            "databricks bundle deploy\n\n"
            "# Start the app\n"
            "databricks bundle run api_explorer",
            className="deploy-code",
        ),

        html.Div([html.Span("Option B", className="deploy-option-label"), " — Direct CLI"], className="deploy-option-title"),
        html.Pre(
            "# Deploy directly\n"
            "databricks apps deploy databricks-api-explorer \\\n"
            "  --source-code-path . \\\n"
            "  --profile <your-profile>",
            className="deploy-code",
        ),

        html.P([
            "When running as a Databricks App, authentication is automatic — "
            "the user's identity is forwarded via the ",
            html.Code("x-forwarded-access-token"),
            " header. No token configuration needed.",
        ], className="text-muted small mb-2"),

        html.Div([
            html.Span("View logs: ", className="text-muted small"),
            html.Code("databricks apps logs databricks-api-explorer --profile <your-profile>", className="small"),
        ]),
    ]),
], id="deploy-modal", is_open=False, size="lg", centered=True, className="deploy-modal")

_ABOUT_MODAL = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle([
        html.Img(src="/assets/databricks.svg", style={"height": "24px"}, className="me-2"),
        "Databricks API Explorer",
    ])),
    dbc.ModalBody([
        html.P([
            "An interactive REST API explorer for Databricks workspaces. "
            "Browse, execute, and inspect API calls across 15 categories and 45+ endpoints."
        ], className="mb-3"),

        html.Div([
            html.Div([
                html.I(className="bi bi-github me-2"),
                html.A(
                    "github.com/guido-oswald_data/DatabricksAPIexplorer",
                    href="https://github.com/guido-oswald_data/DatabricksAPIexplorer",
                    target="_blank", rel="noopener noreferrer",
                    className="about-link",
                ),
            ], className="about-row mb-2"),
            html.Div([
                html.I(className="bi bi-envelope me-2"),
                html.A(
                    "guido@databricks.com",
                    href="mailto:guido@databricks.com",
                    className="about-link",
                ),
            ], className="about-row mb-2"),
        ]),

        html.Hr(className="divider"),
        html.Div([
            html.Span(VERSION, className="version-badge me-2"),
            html.Span("Built with Dash + Databricks SDK", className="text-muted small"),
        ], className="d-flex align-items-center"),
    ]),
], id="about-modal", is_open=False, centered=True, className="deploy-modal")

TOPBAR = dbc.Navbar(
    dbc.Container([
        html.Div([
            html.Button([
                html.Img(src="/assets/databricks.svg", className="brand-logo me-2"),
                html.Span("Databricks", className="brand-db"),
                html.Span(" API Explorer", className="brand-rest"),
            ], id="about-btn", n_clicks=0, className="navbar-brand d-flex align-items-center text-decoration-none about-brand-btn"),
            html.Span(id="topbar-spinner", className="topbar-spinner topbar-spinner-hidden"),
        ], className="d-flex align-items-center"),
        html.Div([
            html.Span(VERSION, className="version-badge me-2"),
            _MODE_BADGE,
            html.Div([
                html.Span(id="workspace-name-display", className="workspace-name"),
                html.Div([
                    html.Span(id="host-display", className="host-display"),
                    html.Span(id="metastore-display", className="metastore-display"),
                ], className="workspace-info-row"),
            ], className="workspace-info ms-3"),
            html.Button(
                html.I(className="bi bi-gear-fill"),
                id="settings-btn",
                n_clicks=0,
                className="settings-btn ms-3",
                title="Settings",
            ),
            html.Button(
                html.Span(id="user-display"),
                id="user-btn",
                n_clicks=0,
                className="user-btn-trigger ms-3",
                title="Connection & identity",
            ),
        ], className="d-flex align-items-center"),
    ], fluid=True),
    color="dark", dark=True, className="topbar",
)


# ── User Dropdown Panel ───────────────────────────────────────────────────────
# Always in DOM, shown/hidden via style. Positioned fixed below topbar right edge.

def _profile_section() -> html.Div:
    """Build the CLI-profile connection sub-section of the dropdown.

    The ``<select>`` options are populated dynamically via the
    ``populate_dropdown`` callback each time the panel opens.
    """
    # Options are populated dynamically via toggle_dropdown callback on each open
    return html.Div([
        html.Label("Profile", className="conn-label"),
        dbc.Select(
            id="profile-select",
            options=[],
            value="",
            className="conn-select",
        ),
        html.Div(id="profile-auth-type", className="conn-hint mt-1"),
        html.Button(
            [html.I(className="bi bi-arrow-repeat me-2"), "Re-authenticate with SSO"],
            id="reauth-btn",
            n_clicks=0,
            className="reauth-btn mt-2",
        ),
        html.Div(id="reauth-status", className="mt-2 small"),
    ], id="profile-section")


def _sso_section() -> html.Div:
    """Build the SSO-login connection sub-section of the dropdown."""
    return html.Div([
        html.Label("Workspace URL", className="conn-label"),
        dbc.Input(
            id="sso-host-input",
            type="url",
            placeholder="https://adb-xxxx.azuredatabricks.net",
            className="conn-input font-mono",
        ),
        html.Div("Opens your browser for SSO authentication", className="conn-hint mt-1 text-muted small"),
    ], id="sso-section", style={"display": "none"})


def _custom_section() -> html.Div:
    """Build the manual URL + token connection sub-section."""
    return html.Div([
        html.Label("Workspace URL", className="conn-label"),
        dbc.Input(
            id="custom-host-input",
            type="url",
            placeholder="https://adb-xxxx.azuredatabricks.net",
            className="conn-input font-mono",
        ),
        html.Label("Personal Access Token", className="conn-label mt-2"),
        dbc.Input(
            id="custom-token-input",
            type="password",
            placeholder="dapi…",
            className="conn-input font-mono",
        ),
    ], id="custom-section", style={"display": "none"})


USER_DROPDOWN = html.Div([
    # ── Identity section ──────────────────────────────────────
    html.Div([
        html.Div(id="popup-avatar", className="auth-avatar"),
        html.Div([
            html.Div(id="popup-name", className="auth-display-name"),
            html.Div(id="popup-username", className="auth-username"),
            html.Div(id="popup-status"),
        ]),
    ], className="auth-profile-header px-4 pt-3 pb-2"),

    html.Div(id="popup-auth-details", className="px-4 pb-2"),

    html.Hr(className="divider mx-3"),

    # ── Connection section ────────────────────────────────────
    html.Div([
        html.Div("Connection", className="auth-section-title mb-2"),
        dbc.RadioItems(
            id="conn-mode-radio",
            options=[
                {"label": "CLI Profile", "value": "profile"},
                {"label": "SSO Login", "value": "sso"},
                {"label": "URL + Token", "value": "custom"},
            ],
            value="profile",
            inline=True,
            className="conn-mode-radio mb-3",
            input_class_name="conn-radio-input",
            label_class_name="conn-radio-label",
        ),
        _profile_section(),
        _sso_section(),
        _custom_section(),
        html.Button(
            [html.I(className="bi bi-plug-fill me-2"), "Connect"],
            id="apply-conn-btn",
            n_clicks=0,
            className="apply-btn mt-3",
        ),
        html.Div(id="conn-status", className="mt-2 small"),
    ], className="px-4 pb-3"),

    html.Hr(className="divider mx-3"),

    # ── Groups section ────────────────────────────────────────
    html.Div([
        html.Div("Groups", className="auth-section-title mb-2"),
        html.Div(id="popup-groups"),
    ], className="px-4 pb-4"),

], id="user-dropdown", style={"display": "none"}, className="user-dropdown")

# Transparent overlay behind dropdown — click to close
_DROPDOWN_OVERLAY = html.Div(
    id="dropdown-overlay",
    n_clicks=0,
    style={"display": "none"},
    className="dropdown-overlay",
)


# ── Welcome Panel ─────────────────────────────────────────────────────────────
_ALL_ENDPOINTS = TOTAL_ENDPOINTS + TOTAL_ACCOUNT_ENDPOINTS
_ALL_CATEGORIES = TOTAL_CATEGORIES + TOTAL_ACCOUNT_CATEGORIES

WELCOME = html.Div([
    html.Div([
        html.Div("◈", className="welcome-icon"),
        html.H3("Select an API Endpoint", className="welcome-title"),
        html.P(
            "Choose a category from the sidebar, then click any endpoint to explore "
            "Databricks workspace and account APIs in real-time.",
            className="welcome-subtitle",
        ),
        html.Hr(className="welcome-divider"),
        html.Div([
            html.Div([html.I(className="bi bi-lightning-fill me-2", style={"color": "#00d4ff"}), f"{_ALL_ENDPOINTS} endpoints"], className="stat-pill"),
            html.Div([html.I(className="bi bi-collection-fill me-2", style={"color": "#00d4ff"}), f"{_ALL_CATEGORIES} categories"], className="stat-pill"),
            html.Div([html.I(className="bi bi-shield-check-fill me-2", style={"color": "#00d4ff"}), "OBO + SSO auth"], className="stat-pill"),
        ], className="welcome-stats"),
    ], className="welcome-content"),
], className="welcome-panel")


# ── App Layout ────────────────────────────────────────────────────────────────
_RESPONSE_EMPTY = html.Div([
    html.I(className="bi bi-terminal"),
    html.Div("Select an endpoint and click Execute"),
], className="response-empty")

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="selected-endpoint"),
    dcc.Store(id="conn-config", data=_DEFAULT_CONN),
    dcc.Store(id="last-request", data=None),
    dcc.Store(id="page-trigger", data={}),          # written only by start_pagination
    dcc.Store(id="page-state", data={"running": False}),  # written only by tick_fetch (primary)
    dcc.Store(id="spinner-off", data=0),            # written by execute_api_call to signal done
    dcc.Store(id="iframe-link-click", data=None),  # written by postMessage from large-JSON iframe
    dcc.Store(id="chips-store", data=None),         # written by execute_api_call, read by sp-item callback
    dcc.Store(id="sp-dummy", data=None),            # dummy output for side-panel toggle clientside CB
    dcc.Store(id="curl-dummy", data=None),          # dummy output for curl copy clientside CB
    dcc.Store(id="settings-theme-dummy", data=None), # dummy output for theme apply clientside CB
    dcc.Store(id="sso-pending", data=None),          # {"host": "..."} while browser OAuth is running
    dcc.Interval(id="sso-poller", interval=1000, disabled=True, n_intervals=0),
    dcc.Interval(id="page-ticker", interval=500, disabled=True, n_intervals=0),
    dcc.Interval(id="load-all-ticker", interval=600, disabled=True, n_intervals=0),

    dcc.Store(id="dropdown-open", data=False),       # tracks dropdown visibility
    dcc.Store(id="response-cache", data={}),         # {endpoint_id: {result, chips}} — cached API responses
    dcc.Store(id="api-scope", data="workspace"),     # "workspace" or "account"

    TOPBAR,
    _DROPDOWN_OVERLAY,
    USER_DROPDOWN,  # fixed dropdown, outside normal flow
    _DEPLOY_MODAL,
    _ABOUT_MODAL,
    _SETTINGS_MODAL,
    dcc.Store(id="settings-store", data={"timezone": "Europe/Berlin", "language": "en", "theme": "midnight"}, storage_type="local"),

    html.Div([
        build_sidebar(),
        html.Div([
            html.Div(WELCOME, id="endpoint-detail", className="form-panel"),
            html.Div([
                html.Div(id="fetch-status-bar", className="fetch-status-bar"),
                html.Div(_RESPONSE_EMPTY, id="response-container", className="response-container"),
                html.Button(
                    [html.I(className="bi bi-cloud-download me-1"), "Load All"],
                    id="sp-load-all-btn",
                    n_clicks=0,
                    className="sp-load-all-btn",
                    title="Fetch all remaining pages",
                    style={"display": "none"},
                ),
                html.Button(
                    [html.I(className="bi bi-x-lg me-1"), "Abort"],
                    id="load-all-abort-btn",
                    n_clicks=0,
                    className="load-all-abort-btn",
                    title="Cancel loading",
                    style={"display": "none"},
                ),
            ], className="response-panel"),
        ], className="main-content"),
    ], className="app-body"),
], className="app-root")


# ── Callbacks ─────────────────────────────────────────────────────────────────

# 0a. Scope switcher — toggle between Workspace and Account APIs
app.clientside_callback(
    """
    function(wsClicks, acctClicks) {
        var triggered = dash_clientside.callback_context.triggered;
        if (!triggered || !triggered.length) return dash_clientside.no_update;
        var tid = triggered[0].prop_id;
        return tid.indexOf("scope-account") !== -1 ? "account" : "workspace";
    }
    """,
    Output("api-scope", "data"),
    Input("scope-workspace-btn", "n_clicks"),
    Input("scope-account-btn", "n_clicks"),
    prevent_initial_call=True,
)


# 0b. Rebuild the accordion and highlight the active scope button
@app.callback(
    Output("api-accordion", "children"),
    Output("scope-workspace-btn", "className"),
    Output("scope-account-btn", "className"),
    Input("api-scope", "data"),
)
def rebuild_sidebar_for_scope(scope):
    """Callback 0b: Rebuild the accordion items when the API scope changes."""
    if scope == "account":
        items = _build_accordion_items(ACCOUNT_API_CATALOG)
        return items, "scope-btn", "scope-btn scope-btn-active"
    items = _build_accordion_items(API_CATALOG)
    return items, "scope-btn scope-btn-active", "scope-btn"


# 1. Init: populate topbar on page load or connection change
@app.callback(
    Output("user-display", "children"),
    Output("host-display", "children"),
    Output("workspace-name-display", "children"),
    Output("metastore-display", "children"),
    Input("url", "pathname"),
    Input("conn-config", "data"),
)
def init_on_load(_, conn_config):
    """Callback 1: Populate topbar user chip, host label, workspace name, and metastore."""
    host, token = _resolve_conn(conn_config)
    host_label = html.Span(
        (host or "").replace("https://", ""),
        className="text-muted",
    ) if host else html.Span("(not connected)", className="text-warning")

    ws_name = None
    ms_name = None
    if token and host:
        info = get_current_user_info(token, host)
        name = info.get("display_name") or info.get("user_name") or "Unknown"
        user_el = html.Span([
            html.I(className="bi bi-person-circle me-1"),
            name,
            html.I(className="bi bi-chevron-down ms-1 small"),
        ], className="user-chip")
        # Use CLI profile name when in profile mode, otherwise workspace name
        conn_mode = (conn_config or {}).get("mode")
        if conn_mode == "profile":
            ws_name = (conn_config or {}).get("profile") or DATABRICKS_PROFILE
        else:
            ws_name = get_workspace_name(token, host)
        ms_name = get_metastore_name(token, host)
    else:
        user_el = html.Span([
            html.I(className="bi bi-person-circle me-1"),
            "Not connected",
            html.I(className="bi bi-chevron-down ms-1 small"),
        ], className="user-chip text-warning")

    ws_name_el = html.Span(
        [html.I(className="bi bi-tag me-1"), ws_name],
        className="workspace-name-text"
    ) if ws_name else None

    ms_name_el = html.Span(
        [html.I(className="bi bi-layers me-1"), ms_name],
        className="metastore-name-text"
    ) if ms_name else None

    return user_el, host_label, ws_name_el, ms_name_el


# 1b. Toggle deploy modal
@app.callback(
    Output("deploy-modal", "is_open"),
    Input("mode-badge-btn", "n_clicks"),
    State("deploy-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_deploy_modal(n, is_open):
    """Callback 1b: Toggle the deploy-instructions modal."""
    return not is_open


# 1c. Toggle about modal
@app.callback(
    Output("about-modal", "is_open"),
    Input("about-btn", "n_clicks"),
    State("about-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_about_modal(n, is_open):
    """Callback 1c: Toggle the about modal."""
    return not is_open


# 1d. Toggle settings modal and sync controls to saved values on open
app.clientside_callback(
    """
    function(n, isOpen, settings) {
        if (!n) return [dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update];
        var opening = !isOpen;
        if (opening && settings) {
            return [true, settings.timezone || "Europe/Berlin", settings.language || "en"];
        }
        return [!isOpen, dash_clientside.no_update, dash_clientside.no_update];
    }
    """,
    Output("settings-modal", "is_open"),
    Output("settings-timezone", "value"),
    Output("settings-language", "value"),
    Input("settings-btn", "n_clicks"),
    State("settings-modal", "is_open"),
    State("settings-store", "data"),
    prevent_initial_call=True,
)


# 1e. Unified settings callback — theme card clicks update the store;
#     store changes apply CSS variables.  Dropdowns are *not* outputs
#     of the store callback, breaking the circular dependency.
@app.callback(
    Output("settings-store", "data"),
    Input("settings-timezone", "value"),
    Input("settings-language", "value"),
    Input({"type": "theme-card", "idx": ALL}, "n_clicks"),
    State("settings-store", "data"),
    prevent_initial_call=True,
)
def update_settings(tz, lang, theme_clicks, current):
    """Callback 1e: Update settings store when any setting changes."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update
    tid = ctx.triggered[0]["prop_id"]
    settings = dict(current) if current else {"timezone": "Europe/Berlin", "language": "en", "theme": "midnight"}
    if "settings-timezone" in tid:
        settings["timezone"] = tz
    elif "settings-language" in tid:
        settings["language"] = lang
    elif "theme-card" in tid:
        import json as _json
        parsed = _json.loads(tid.rsplit(".", 1)[0])
        settings["theme"] = parsed["idx"]
    return settings


# 1f. Apply theme CSS variables whenever the settings store changes (clientside).
#     Does NOT write back to timezone/language dropdowns — those are already
#     in sync because the user just changed them (or they're set via initial value).
app.clientside_callback(
    """
    function(settings) {
        if (!settings) return window.dash_clientside.no_update;

        var themes = """ + json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("label", "icon", "dark")} for k, v in _THEMES.items()}) + """;
        var theme = themes[settings.theme || "midnight"] || themes["midnight"];
        var root = document.documentElement;
        root.style.setProperty('--bg-void', theme['bg-void']);
        root.style.setProperty('--bg-dark', theme['bg-dark']);
        root.style.setProperty('--bg-panel', theme['bg-panel']);
        root.style.setProperty('--bg-card', theme['bg-card']);
        root.style.setProperty('--bg-hover', theme['bg-hover']);
        root.style.setProperty('--bg-active', theme['bg-active']);
        root.style.setProperty('--border', theme['border']);
        root.style.setProperty('--border-hi', theme['border-hi']);
        root.style.setProperty('--text-hi', theme['text-hi']);
        root.style.setProperty('--text-1', theme['text-1']);
        root.style.setProperty('--text-2', theme['text-2']);
        root.style.setProperty('--text-3', theme['text-3']);
        root.style.setProperty('--cyan', theme['accent']);
        root.style.setProperty('--glow-cyan', '0 0 18px ' + theme['accent'] + '48');
        root.style.setProperty('--card-bg', theme['card-bg']);

        // Highlight the active theme card
        document.querySelectorAll('.theme-card').forEach(function(card) {
            card.classList.remove('theme-card-active');
            if (card.getAttribute('data-theme') === (settings.theme || 'midnight')) {
                card.classList.add('theme-card-active');
            }
        });

        return window.dash_clientside.no_update;
    }
    """,
    Output("settings-theme-dummy", "data"),
    Input("settings-store", "data"),
)


# 2. Toggle dropdown open/close — clientside for instant reactivity
app.clientside_callback(
    """
    function(btnClicks, overlayClicks, isOpen) {
        // Both inputs trigger a close or toggle
        var triggered = dash_clientside.callback_context.triggered;
        if (!triggered || !triggered.length) return [dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update];
        var tid = triggered[0].prop_id;
        if (tid === "dropdown-overlay.n_clicks") {
            // Overlay click → always close
            return [false, {display: "none"}, {display: "none"}];
        }
        // user-btn click → toggle
        var newOpen = !isOpen;
        var style = newOpen ? {display: "block"} : {display: "none"};
        return [newOpen, style, style];
    }
    """,
    Output("dropdown-open", "data"),
    Output("user-dropdown", "style"),
    Output("dropdown-overlay", "style"),
    Input("user-btn", "n_clicks"),
    Input("dropdown-overlay", "n_clicks"),
    State("dropdown-open", "data"),
    prevent_initial_call=True,
)


# 2b. Populate identity info when dropdown opens (server-side, async)
@app.callback(
    Output("popup-avatar", "children"),
    Output("popup-name", "children"),
    Output("popup-username", "children"),
    Output("popup-status", "children"),
    Output("popup-auth-details", "children"),
    Output("popup-groups", "children"),
    Output("conn-mode-radio", "value"),
    Output("profile-select", "value"),
    Output("profile-select", "options"),
    Input("dropdown-open", "data"),
    Input("conn-config", "data"),
    prevent_initial_call=True,
)
def populate_dropdown(is_open, conn_config):
    """Callback 2b: Fetch SCIM identity and populate the dropdown panel."""
    if not is_open:
        return [no_update] * 9

    conn_config = conn_config or _DEFAULT_CONN
    host, token = _resolve_conn(conn_config)

    # Refresh profile list from disk every time the dropdown opens
    profiles = get_cli_profiles()
    profile_options = [{"label": p, "value": p} for p in profiles]
    current_profile = conn_config.get("profile", DATABRICKS_PROFILE)
    if current_profile not in profiles and profiles:
        current_profile = profiles[0]

    scim: Dict = {}
    if token and host:
        r = make_api_call("GET", "/api/2.0/preview/scim/v2/Me", token, host)
        if r["success"]:
            scim = r["data"]

    display_name = scim.get("displayName", "Unknown")
    username = scim.get("userName", "")
    active = scim.get("active", True)
    groups: List[Dict] = scim.get("groups", [])
    emails: List[Dict] = scim.get("emails", [])
    primary_email = next((e["value"] for e in emails if e.get("primary")), emails[0]["value"] if emails else "")
    user_id = scim.get("id", "")

    letter = (display_name[0] if display_name not in ("", "Unknown") else username[0] if username else "?").upper()

    # Auth type
    if IS_DATABRICKS_APP:
        auth_type_display = "On-Behalf-Of (OBO)"
    elif conn_config.get("mode") == "custom":
        auth_type_display = "Personal Access Token"
    else:
        try:
            cfg = _get_local_config()
            raw = getattr(cfg, "auth_type", None) or "unknown"
            auth_type_display = {
                "pat": "Personal Access Token",
                "oauth-m2m": "OAuth M2M",
                "external-browser": "OAuth (Browser / SSO)",
                "azure-client-secret": "Azure Service Principal",
                "azure-msi": "Azure Managed Identity",
            }.get(raw, raw)
        except Exception:
            auth_type_display = "Unknown"

    account_id = get_account_id(conn_config.get("profile"))
    auth_details = html.Div([
        html.Div([html.Span("Auth", className="auth-info-label"), html.Span(auth_type_display, className="auth-info-value font-mono")], className="auth-info-row"),
        html.Div([html.Span("Host", className="auth-info-label"), html.Span((host or "—").replace("https://", ""), className="auth-info-value font-mono small")], className="auth-info-row"),
        html.Div([html.Span("Account ID", className="auth-info-label"), html.Span(account_id or "not available", className="auth-info-value font-mono small")], className="auth-info-row"),
        html.Div([html.Span("Email", className="auth-info-label"), html.Span(primary_email or "—", className="auth-info-value small")], className="auth-info-row") if primary_email else None,
        html.Div([html.Span("User ID", className="auth-info-label"), html.Span(user_id or "—", className="auth-info-value font-mono small")], className="auth-info-row") if user_id else None,
    ], className="auth-info-table")

    groups_el = html.Div([
        dbc.Badge(g.get("display", g.get("value", "?")), color="secondary", className="me-1 mb-1 auth-group-badge")
        for g in groups[:20]
    ] + ([html.Span(f"+{len(groups)-20} more", className="text-muted small")] if len(groups) > 20 else [])
    ) if groups else html.Span("No groups", className="text-muted small")

    status_el = dbc.Badge(
        [html.I(className="bi bi-circle-fill me-1"), "Active" if active else "Inactive"],
        color="success" if active else "danger", className="auth-active-badge mt-1",
    )

    return (
        letter,
        display_name,
        username,
        status_el,
        auth_details,
        groups_el,
        conn_config.get("mode", "profile"),
        current_profile,
        profile_options,
    )

# 4. Show/hide profile vs sso vs custom section
@app.callback(
    Output("profile-section", "style"),
    Output("sso-section", "style"),
    Output("custom-section", "style"),
    Input("conn-mode-radio", "value"),
)
def toggle_conn_mode(mode):
    """Callback 4: Show/hide the profile, SSO, or custom connection section."""
    hide = {"display": "none"}
    if mode == "profile":
        return {}, hide, hide
    if mode == "sso":
        return hide, {}, hide
    return hide, hide, {}


# 5. Show auth type hint when profile changes
@app.callback(
    Output("profile-auth-type", "children"),
    Input("profile-select", "value"),
)
def show_profile_hint(profile):
    """Callback 5: Display auth type and host hint when the selected profile changes."""
    if not profile:
        return ""
    try:
        from databricks.sdk.core import Config
        cfg = Config(profile=profile)
        raw = getattr(cfg, "auth_type", None) or "?"
        label = {
            "pat": "Personal Access Token",
            "oauth-m2m": "OAuth M2M",
            "external-browser": "OAuth (Browser / SSO)",
            "azure-client-secret": "Azure Service Principal",
            "azure-msi": "Azure Managed Identity",
        }.get(raw, raw)
        host = (cfg.host or "").replace("https://", "")
        return html.Span(f"{label} · {host}", className="text-muted")
    except Exception as e:
        return html.Span(str(e), className="text-danger small")


# 6. Apply connection
@app.callback(
    Output("conn-config", "data"),
    Output("conn-status", "children"),
    Output("sso-poller", "disabled", allow_duplicate=True),
    Input("apply-conn-btn", "n_clicks"),
    State("conn-mode-radio", "value"),
    State("profile-select", "value"),
    State("sso-host-input", "value"),
    State("custom-host-input", "value"),
    State("custom-token-input", "value"),
    prevent_initial_call=True,
)
def apply_connection(n_clicks, mode, profile, sso_host, custom_host, custom_token):
    """Callback 6: Validate and apply the chosen connection settings.

    Writes a new ``conn-config`` store value on success and may kick
    off a background SSO browser flow for the ``"sso"`` mode.
    """
    if not n_clicks:
        return no_update, no_update, no_update

    if mode == "profile":
        if not profile:
            return no_update, html.Span("No profile selected.", className="text-danger"), no_update
        new_config = {"mode": "profile", "profile": profile}
        # Quick validation
        host, token = resolve_local_connection(new_config)
        if not host or not token:
            return no_update, html.Span("Could not connect with this profile — check CLI auth.", className="text-danger"), no_update
        return new_config, html.Span([html.I(className="bi bi-check-circle-fill me-1 text-success"), f"Connected via profile '{profile}'"]), no_update

    elif mode == "sso":
        host = (sso_host or "").strip().rstrip("/")
        if not host:
            return no_update, html.Span("Workspace URL is required.", className="text-danger"), no_update
        if not host.startswith("https://"):
            host = "https://" + host

        # 1 — try cached / refreshed token (instant, no browser)
        try:
            token = _sso_try_cached(host)
        except Exception:
            token = None

        if token:
            r = make_api_call("GET", "/api/2.0/preview/scim/v2/Me", token, host)
            if r["success"]:
                return {"mode": "sso", "host": host, "token": token}, html.Span([
                    html.I(className="bi bi-check-circle-fill me-1 text-success"),
                    f"Connected to {host.replace('https://', '')}",
                ]), no_update

        # 2 — no cached token → start browser OAuth in background thread
        with _sso_lock:
            _sso_result[host] = {"token": None, "error": None, "done": False}
        t = threading.Thread(target=_sso_browser_flow, args=(host,), daemon=True)
        t.start()
        return no_update, html.Span([
            html.I(className="bi bi-hourglass-split me-2"),
            "Waiting for SSO in browser… complete login and return here.",
        ], id="sso-waiting", **{"data-host": host}), False  # enable poller

    else:  # custom
        host = (custom_host or "").strip().rstrip("/")
        token = (custom_token or "").strip()
        if not host:
            return no_update, html.Span("Workspace URL is required.", className="text-danger"), no_update
        if not token:
            return no_update, html.Span("Token is required.", className="text-danger"), no_update
        if not host.startswith("https://"):
            host = "https://" + host
        # Quick validation
        r = make_api_call("GET", "/api/2.0/preview/scim/v2/Me", token, host)
        if not r["success"]:
            return no_update, html.Span(f"Connection failed: {r['status_code']} {r.get('error','')}", className="text-danger"), no_update
        return {"mode": "custom", "host": host, "token": token}, html.Span([html.I(className="bi bi-check-circle-fill me-1 text-success"), f"Connected to {host.replace('https://','')}"]), no_update


# 6b. Poll for SSO browser OAuth completion
@app.callback(
    Output("conn-config", "data", allow_duplicate=True),
    Output("conn-status", "children", allow_duplicate=True),
    Output("sso-poller", "disabled"),
    Input("sso-poller", "n_intervals"),
    prevent_initial_call=True,
)
def poll_sso(n_intervals):
    """Callback 6b: Poll for SSO browser-OAuth completion."""
    # Find the host that has a pending or completed SSO flow
    with _sso_lock:
        host = None
        for h, res in _sso_result.items():
            host = h
            break
    if not host:
        return no_update, no_update, True  # disable poller

    with _sso_lock:
        result = _sso_result.get(host)
    if not result or not result.get("done"):
        return no_update, no_update, False  # keep polling

    # Done — disable poller and process result
    with _sso_lock:
        _sso_result.pop(host, None)

    if result.get("error"):
        return no_update, html.Span(f"SSO failed: {result['error']}", className="text-danger"), True
    token = result.get("token")
    if not token:
        return no_update, html.Span("SSO completed but no token received.", className="text-danger"), True
    r = make_api_call("GET", "/api/2.0/preview/scim/v2/Me", token, host)
    if r["success"]:
        return {"mode": "sso", "host": host, "token": token}, html.Span([
            html.I(className="bi bi-check-circle-fill me-1 text-success"),
            f"Connected to {host.replace('https://', '')}",
        ]), True
    return no_update, html.Span(
        f"Token rejected by workspace (HTTP {r['status_code']}).", className="text-danger"
    ), True


# 7. Re-auth (profile mode only)
@app.callback(
    Output("reauth-status", "children"),
    Input("reauth-btn", "n_clicks"),
    State("profile-select", "value"),
    prevent_initial_call=True,
)
def reauth(n_clicks, profile):
    """Callback 7: Re-authenticate by launching ``databricks auth login`` in the background."""
    if not n_clicks:
        return no_update
    p = profile or DATABRICKS_PROFILE
    try:
        subprocess.Popen(
            ["databricks", "auth", "login", "--profile", p],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return html.Span([
            html.I(className="bi bi-check-circle-fill me-1 text-success"),
            "Browser opened — complete SSO, then click Connect.",
        ])
    except FileNotFoundError:
        return html.Span("Databricks CLI not found.", className="text-danger")
    except Exception as e:
        return html.Span(str(e), className="text-danger")


# 8. Select endpoint (sidebar button click → store)
@app.callback(
    Output("selected-endpoint", "data"),
    Input({"type": "endpoint-btn", "id": ALL}, "n_clicks"),
    State({"type": "endpoint-btn", "id": ALL}, "id"),
    prevent_initial_call=True,
)
def select_endpoint(n_clicks_list, btn_ids):
    """Callback 8: Write the clicked endpoint to ``selected-endpoint`` store."""
    from dash import callback_context as ctx
    if not ctx.triggered:
        return no_update
    try:
        clicked_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["id"]
    except (json.JSONDecodeError, KeyError):
        return no_update
    endpoint = get_endpoint_by_id(clicked_id)
    if not endpoint:
        return no_update
    return endpoint


# 8b. Sync sidebar button highlight + accordion section whenever selected-endpoint changes
@app.callback(
    Output({"type": "endpoint-btn", "id": ALL}, "className"),
    Output("api-accordion", "active_item"),
    Input("selected-endpoint", "data"),
    State({"type": "endpoint-btn", "id": ALL}, "id"),
    prevent_initial_call=True,
)
def sync_active_button(endpoint, btn_ids):
    """Callback 8b: Highlight the active sidebar button and open its accordion section."""
    active_id = (endpoint or {}).get("id", "")
    classes = ["endpoint-btn active" if b["id"] == active_id else "endpoint-btn" for b in btn_ids]
    # Open the accordion section for the endpoint's category
    cat_name = (endpoint or {}).get("category", "")
    scope = (endpoint or {}).get("scope", "workspace")
    catalog = ACCOUNT_API_CATALOG if scope == "account" else API_CATALOG
    cat_keys = list(catalog.keys())
    active_item = no_update
    if cat_name in cat_keys:
        active_item = f"item-{cat_keys.index(cat_name)}"
    return classes, active_item


# 9. Render endpoint detail
@app.callback(
    Output("endpoint-detail", "children"),
    Output("endpoint-detail", "className"),
    Input("selected-endpoint", "data"),
    State("conn-config", "data"),
    prevent_initial_call=True,
)
def render_endpoint_detail(endpoint: Optional[Dict], conn_config):
    """Callback 9: Render the endpoint detail card (header, path, params, Execute button)."""
    if not endpoint:
        return WELCOME, "form-panel"
    prefill = dict(endpoint.get("_prefill", {}))

    # Auto-fill account_id for account-scope endpoints from the CLI profile
    if endpoint.get("scope") == "account" and "account_id" not in prefill:
        profile = (conn_config or {}).get("profile")
        acct_id = get_account_id(profile)
        if acct_id:
            prefill["account_id"] = acct_id

    cat_color = endpoint.get("category_color", "#00d4ff")
    content = html.Div([
        html.Div([
            method_badge(endpoint.get("method", "GET")),
            html.Div([
                html.Div(endpoint["name"], className="endpoint-name"),
                html.Div(html.Span(endpoint.get("category", ""), style={"color": cat_color}), className="endpoint-category"),
            ], className="endpoint-meta"),
        ], className="endpoint-header"),
        html.Div(endpoint["path"], className="endpoint-path font-mono"),
        html.Div(endpoint.get("description", ""), className="endpoint-desc"),
        html.Hr(className="divider"),
        html.Div("Parameters", className="param-section-title"),
        build_param_form(endpoint, prefill),
        html.Hr(className="divider"),
        html.Div([
            html.Button(
                [html.I(className="bi bi-play-fill me-2"), "Execute"],
                id="execute-btn", n_clicks=0, className="execute-btn",
            ),
            html.Div([
                html.I(className="bi bi-clock me-1"),
                dbc.Input(
                    id="timeout-input",
                    type="number",
                    value=endpoint.get("timeout", 30),
                    min=1, max=600, step=1,
                    className="timeout-input font-mono",
                ),
                html.Span("s", className="timeout-unit"),
            ], className="timeout-control", title="Timeout in seconds"),
        ], className="execute-row"),
        html.Div([
            html.Div([
                html.Span([html.I(className="bi bi-terminal me-2"), "curl"], className="curl-label"),
                html.Button(
                    [html.I(className="bi bi-clipboard me-1"), "Copy"],
                    id="curl-copy-btn", n_clicks=0, className="curl-copy-btn",
                ),
            ], className="curl-header"),
            html.Pre(id="curl-text", className="curl-text font-mono"),
        ], id="curl-display", className="curl-display"),
    ], className="endpoint-card")
    return content, "form-panel"


# 9b. Restore cached response when switching endpoints via sidebar
@app.callback(
    Output("response-container", "children", allow_duplicate=True),
    Output("chips-store", "data", allow_duplicate=True),
    Input("selected-endpoint", "data"),
    State("response-cache", "data"),
    prevent_initial_call=True,
)
def restore_cached_response(endpoint, cache):
    """Callback 9b: Restore a previously cached response when switching endpoints."""
    if not endpoint:
        return _RESPONSE_EMPTY, None
    ep_id = endpoint.get("id", "")
    cached = (cache or {}).get(ep_id)
    if not cached:
        return _RESPONSE_EMPTY, None
    result = cached["result"]
    chips = cached.get("chips")
    return build_response_panel(result, chips), chips


# 10. Execute API call
@app.callback(
    Output("response-container", "children"),
    Output("last-request", "data"),
    Output("spinner-off", "data"),
    Output("chips-store", "data"),
    Output("response-cache", "data", allow_duplicate=True),
    Output("sp-load-all-btn", "style"),
    Input("execute-btn", "n_clicks"),
    State("selected-endpoint", "data"),
    State({"type": "param-input", "name": ALL}, "value"),
    State({"type": "param-input", "name": ALL}, "id"),
    State("body-textarea", "value"),
    State("timeout-input", "value"),
    State("conn-config", "data"),
    State("response-cache", "data"),
    prevent_initial_call=True,
)
def execute_api_call(n_clicks, endpoint, param_values, param_ids, body_text, timeout_val, conn_config, cache):
    """Callback 10: Execute the selected API call and render the response."""
    if not n_clicks or not endpoint:
        return no_update, no_update, no_update, no_update, no_update, no_update

    params: Dict[str, Any] = {}
    ep_param_map = {p["name"]: p for p in endpoint.get("params", [])}
    for pid, pval in zip(param_ids, param_values):
        name = pid["name"]
        if pval in (None, ""):
            continue
        if ep_param_map.get(name, {}).get("type") == "integer":
            try:
                params[name] = int(float(pval))
            except (ValueError, TypeError):
                params[name] = pval
        else:
            params[name] = pval

    path: str = endpoint["path"]
    for pp in endpoint.get("path_params", []):
        val = params.pop(pp, "")
        if not val:
            return build_error_panel(f"Path parameter '{pp}' is required."), no_update, time.time(), None, no_update, {"display": "none"}
        path = path.replace(f"{{{pp}}}", str(val))

    method = endpoint.get("method", "GET")
    body = None
    if method == "POST" and body_text and body_text.strip():
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError as e:
            return build_error_panel(f"Invalid JSON body: {e}"), no_update, time.time(), None, no_update, {"display": "none"}

    ws_host, ws_token = _resolve_conn(conn_config)
    if not ws_host:
        return build_error_panel("No workspace host. Configure a connection in the user menu."), no_update, time.time(), None, no_update, {"display": "none"}

    # Account-scope endpoints need a token issued for the accounts console
    is_account = endpoint.get("scope") == "account"
    if is_account:
        host, token = resolve_account_connection(conn_config, _accounts_host(ws_host))
    else:
        host, token = ws_host, ws_token

    if not token:
        msg = "No auth token for the accounts console. Ensure your CLI profile has an account_id configured." if is_account else "No auth token. Configure a connection in the user menu."
        return build_error_panel(msg), no_update, time.time(), None, no_update, {"display": "none"}

    try:
        ep_timeout = max(1, int(timeout_val or endpoint.get("timeout", 30)))
    except (ValueError, TypeError):
        ep_timeout = endpoint.get("timeout", 30)
    resp_format = endpoint.get("response_format")
    result = make_api_call(
        method=method, path=path, token=token, host=host,
        query_params=params if method == "GET" else None, body=body,
        timeout=ep_timeout,
    )

    # CSV responses: parse _raw text into a table instead of showing raw text
    if resp_format == "csv" and result["success"] and isinstance(result["data"], dict) and "_raw" in result["data"]:
        result["_csv"] = result["data"]["_raw"]
        result["data"] = {"message": "CSV data downloaded successfully. See table below."}

    chips = extract_chips(endpoint.get("id", ""), result["data"]) if result["success"] else []
    resp_data = result["data"] if isinstance(result["data"], dict) else {}
    has_more = bool(resp_data.get("has_more"))
    last_req = {
        "path": path,
        "method": method,
        "query_params": params if method == "GET" else None,
        "body": body,
        "endpoint_id": endpoint.get("id", ""),
        "initial_data": result["data"],
        "elapsed_ms": result["elapsed_ms"],
        "status_code": result["status_code"],
        "url": result.get("url", ""),
    }
    ep_id = endpoint.get("id", "")
    new_cache = dict(cache or {})
    new_cache[ep_id] = {"result": result, "chips": chips or None}
    btn_style = {"display": "inline-flex"} if has_more else {"display": "none"}
    return build_response_panel(result, chips), last_req, time.time(), chips or None, new_cache, btn_style


# 11. Signal tick_fetch to start a new pagination run whenever execute fires.
#     Writes to page-trigger (separate store) so tick_fetch stays the sole
#     primary writer of page-state — ensuring sync_status_bar fires on every tick.
@app.callback(
    Output("page-trigger", "data"),
    Output("page-ticker", "disabled"),
    Input("last-request", "data"),
    prevent_initial_call=True,
)
def start_pagination(last_req):
    """Callback 11: Seed the pagination trigger store after each Execute."""
    if not last_req:
        return {}, True
    initial_data = last_req.get("initial_data", {})
    # Skip auto-pagination when has_more is present — "Load All" handles those
    if isinstance(initial_data, dict) and initial_data.get("has_more"):
        return {"run_id": time.time()}, True
    next_token = _detect_next_page_token(initial_data)
    list_key = _find_list_key(initial_data) if next_token else None
    should_paginate = next_token is not None
    return {
        "run_id": time.time(),
        "next_token": next_token,
        "list_key": list_key,
        "initial_items": list(initial_data.get(list_key, [])) if list_key else [],
        "initial_data": initial_data,
        "endpoint_id": last_req.get("endpoint_id", ""),
        "status_code": last_req.get("status_code", 200),
        "url": last_req.get("url", ""),
        "path": last_req.get("path", ""),
        "method": last_req.get("method", "GET"),
        "query_params": last_req.get("query_params"),
        "body": last_req.get("body"),
    }, not should_paginate


# 11b. PRIMARY writer of page-state — no allow_duplicate, so sync_status_bar
#      and render_when_done are reliably triggered on every page fetch.
@app.callback(
    Output("page-state", "data"),          # PRIMARY — no allow_duplicate
    Input("page-ticker", "n_intervals"),
    State("page-trigger", "data"),
    State("page-state", "data"),
    State("conn-config", "data"),
    prevent_initial_call=True,
)
def tick_fetch(n_intervals, page_trigger, page_state, conn_config):
    """Callback 11b: Fetch the next page on each ticker interval.

    This is the **primary** writer of ``page-state`` -- it must not
    use ``allow_duplicate`` so that downstream callbacks
    (``sync_status_bar``, ``render_when_done``) fire reliably.
    """
    trigger = page_trigger or {}
    state   = page_state  or {}

    new_run = trigger.get("run_id") and trigger["run_id"] != state.get("run_id")

    # ── Start a new run when trigger signals a fresh execute ──────────
    if new_run:
        if not trigger.get("next_token") or not trigger.get("list_key"):
            # API doesn't paginate — just reset state
            return {"running": False, "run_id": trigger["run_id"]}

        host, token = _resolve_conn(conn_config)
        if not token or not host:
            return {"running": False, "run_id": trigger["run_id"], "error": "No auth token"}

        items = list(trigger.get("initial_items", []))
        t0 = time.perf_counter()
        r = make_api_call(
            trigger["method"], trigger["path"], token, host,
            query_params={**(trigger.get("query_params") or {}), "page_token": trigger["next_token"]},
            body=trigger.get("body"),
        )
        elapsed = int((time.perf_counter() - t0) * 1000)

        base = {
            "run_id":      trigger["run_id"],
            "list_key":    trigger["list_key"],
            "initial_data": trigger.get("initial_data", {}),
            "endpoint_id": trigger.get("endpoint_id", ""),
            "status_code": trigger.get("status_code", 200),
            "url":         trigger.get("url", ""),
            "path":        trigger["path"],
            "method":      trigger["method"],
            "query_params": trigger.get("query_params"),
            "body":        trigger.get("body"),
        }
        if not r["success"]:
            return {**base, "running": False, "pages_done": 0,
                    "items": items, "total_items": len(items),
                    "elapsed_ms": elapsed, "error": r.get("error", "API error")}

        page_data  = r["data"]
        new_items  = items + list(page_data.get(trigger["list_key"], []))
        next_token = _detect_next_page_token(page_data)
        return {**base, "running": next_token is not None, "pages_done": 1,
                "total_items": len(new_items), "items": new_items,
                "next_token": next_token, "elapsed_ms": elapsed, "error": None}

    # ── Continue an existing run ───────────────────────────────────────
    if not state.get("running") or not state.get("next_token"):
        return no_update
    if state.get("pages_done", 0) >= 50:
        return {**state, "running": False, "error": "Reached 50-page limit"}

    host, token = _resolve_conn(conn_config)
    if not token or not host:
        return {**state, "running": False, "error": "No auth token"}

    t0 = time.perf_counter()
    r = make_api_call(
        state["method"], state["path"], token, host,
        query_params={**(state.get("query_params") or {}), "page_token": state["next_token"]},
        body=state.get("body"),
    )
    elapsed = int((time.perf_counter() - t0) * 1000)

    if not r["success"]:
        return {**state, "running": False,
                "error": r.get("error", "API error"),
                "elapsed_ms": state["elapsed_ms"] + elapsed}

    page_data  = r["data"]
    new_items  = list(state["items"]) + list(page_data.get(state["list_key"], []))
    next_token = _detect_next_page_token(page_data)
    return {
        **state,
        "running":    next_token is not None,
        "pages_done": state["pages_done"] + 1,
        "total_items": len(new_items),
        "items":      new_items,
        "next_token": next_token,
        "elapsed_ms": state["elapsed_ms"] + elapsed,
        "error":      None,
    }


# 11c. Update status bar from page-state
@app.callback(
    Output("fetch-status-bar", "children"),
    Input("page-state", "data"),
    prevent_initial_call=True,
)
def sync_status_bar(page_state):
    """Callback 11c: Update the fetch-status bar from ``page-state``."""
    state = page_state or {}
    total = state.get("total_items", 0)
    elapsed = state.get("elapsed_ms", 0)

    if not state.get("running") and not total:
        return None

    if state.get("error") == "Cancelled":
        return html.Div([
            html.I(className="bi bi-slash-circle me-2"),
            f"Cancelled — {total:,} items loaded",
        ], className="fetch-status-inner cancelled")

    if state.get("error"):
        return html.Div([
            html.I(className="bi bi-x-circle-fill me-2"),
            f"Error: {state['error']} — {total:,} items loaded",
        ], className="fetch-status-inner error")

    if state.get("running"):
        next_page = state.get("pages_done", 0) + 2   # page 1 = initial, next = pages_done+2
        return html.Div([
            html.Span(className="status-spinner me-2"),
            f"Fetching page {next_page}… {total:,} items so far",
            html.Button(
                [html.I(className="bi bi-x-lg me-1"), "Abort"],
                id="abort-btn", n_clicks=0, className="abort-btn ms-3",
            ),
        ], className="fetch-status-inner loading")

    return html.Div([
        html.I(className="bi bi-check-circle-fill me-2"),
        f"All pages loaded — {total:,} items · {elapsed}ms",
    ], className="fetch-status-inner done")


# 11c. Render final merged result when pagination completes
@app.callback(
    Output("response-container", "children", allow_duplicate=True),
    Output("response-cache", "data", allow_duplicate=True),
    Output("page-ticker", "disabled", allow_duplicate=True),
    Input("page-state", "data"),
    State("response-cache", "data"),
    prevent_initial_call=True,
)
def render_when_done(page_state, cache):
    """Callback 11c (cont.): Render the merged result once pagination completes."""
    state = page_state or {}
    if state.get("running") or not state.get("items"):
        return no_update, no_update, no_update
    initial_data = state.get("initial_data", {})
    list_key = state.get("list_key")
    if not list_key:
        return no_update, no_update
    merged_data = {**initial_data, list_key: state["items"]}
    merged_data.pop("next_page_token", None)
    merged_data.pop("has_more", None)
    merged_result = {
        "status_code": state.get("status_code", 200),
        "elapsed_ms": state.get("elapsed_ms", 0),
        "data": merged_data,
        "success": True,
        "error": None,
        "url": state.get("url", ""),
    }
    chips = extract_chips(state.get("endpoint_id", ""), merged_data)
    ep_id = state.get("endpoint_id", "")
    new_cache = dict(cache or {})
    if ep_id:
        new_cache[ep_id] = {"result": merged_result, "chips": chips or None}
    return build_response_panel(merged_result, chips), new_cache, True


# 11g. Abort button — cancel in-flight pagination
@app.callback(
    Output("page-state", "data", allow_duplicate=True),
    Input("abort-btn", "n_clicks"),
    State("page-state", "data"),
    prevent_initial_call=True,
)
def abort_pagination(n_clicks, page_state):
    """Callback 11g: Cancel in-flight automatic pagination."""
    if not n_clicks:
        return no_update
    state = page_state or {}
    return {**state, "running": False, "error": "Cancelled"}


# 11h. "Load All" — background thread fetches pages; ticker polls progress.

def _load_all_worker(last_req, host, token, list_key, initial_data):
    """Background thread that fetches all remaining pages via offset/token.

    Mutates the module-level :data:`_load_all_state` dict in place so
    that the ``poll_load_all`` ticker callback can read progress.

    Args:
        last_req: The ``last-request`` store value from the initial
            Execute call.
        host: Workspace URL.
        token: Bearer token.
        list_key: Top-level JSON key that holds the item array.
        initial_data: Parsed response from the first page.
    """
    state = _load_all_state
    items = list(initial_data.get(list_key, []))
    limit = len(items) or 25
    offset = len(items)
    next_token = _detect_next_page_token(initial_data)
    use_token = next_token is not None
    total_elapsed = last_req.get("elapsed_ms", 0)
    pages = 1

    state["items"] = items
    state["pages"] = pages
    state["total_items"] = len(items)
    state["elapsed_ms"] = total_elapsed

    while pages < 200 and state["running"]:
        qp = dict(last_req.get("query_params") or {})
        if use_token and next_token:
            qp["page_token"] = next_token
        else:
            qp["offset"] = str(offset)
            qp["limit"] = str(limit)

        t0 = time.perf_counter()
        r = make_api_call(last_req["method"], last_req["path"], token, host,
                          query_params=qp, body=last_req.get("body"))
        total_elapsed += int((time.perf_counter() - t0) * 1000)

        if not r["success"]:
            state["error"] = r.get("error", "API error")
            break

        page_data = r["data"]
        new_page_items = page_data.get(list_key, [])
        items.extend(new_page_items)
        pages += 1
        offset += limit
        next_token = _detect_next_page_token(page_data)

        state["items"] = items
        state["pages"] = pages
        state["total_items"] = len(items)
        state["elapsed_ms"] = total_elapsed

        if not page_data.get("has_more"):
            break

    state["running"] = False
    state["done"] = True


# 11h-start: Click "Load All" → start background thread + enable ticker
@app.callback(
    Output("load-all-ticker", "disabled"),
    Output("fetch-status-bar", "children", allow_duplicate=True),
    Output("sp-load-all-btn", "style", allow_duplicate=True),
    Output("load-all-abort-btn", "style"),
    Input("sp-load-all-btn", "n_clicks"),
    State("last-request", "data"),
    State("conn-config", "data"),
    prevent_initial_call=True,
)
def start_load_all(n_clicks, last_req, conn_config):
    """Callback 11h-start: Launch the background Load All thread and enable the ticker."""
    NO = (True, no_update, no_update, no_update)
    if not n_clicks or not last_req:
        return NO
    initial_data = last_req.get("initial_data", {})
    if not isinstance(initial_data, dict) or not initial_data.get("has_more"):
        return NO
    list_key = _find_list_key(initial_data)
    if not list_key:
        return NO

    host, token = _resolve_conn(conn_config)
    if not token or not host:
        return NO

    # Reset shared state
    _load_all_state.update({
        "running": True, "done": False, "error": None,
        "pages": 1, "total_items": 0, "items": [],
        "list_key": list_key, "initial_data": initial_data,
        "last_req": last_req, "elapsed_ms": 0,
    })
    _load_all_state.pop("finished_at", None)

    # Launch background thread
    t = threading.Thread(target=_load_all_worker, args=(last_req, host, token, list_key, initial_data), daemon=True)
    t.start()

    status = html.Div([
        html.I(className="bi bi-arrow-repeat me-2 spin-icon"),
        "Loading page 1…",
    ], className="fetch-status-inner loading")

    return False, status, {"display": "none"}, {"display": "inline-flex"}


# 11h-tick: Poll progress from background thread
@app.callback(
    Output("response-container", "children", allow_duplicate=True),
    Output("response-cache", "data", allow_duplicate=True),
    Output("chips-store", "data", allow_duplicate=True),
    Output("fetch-status-bar", "children", allow_duplicate=True),
    Output("load-all-ticker", "disabled", allow_duplicate=True),
    Output("load-all-abort-btn", "style", allow_duplicate=True),
    Input("load-all-ticker", "n_intervals"),
    State("response-cache", "data"),
    prevent_initial_call=True,
)
def poll_load_all(n_intervals, cache):
    """Callback 11h-tick: Poll the background Load All thread for progress."""
    NO = (no_update, no_update, no_update, no_update, no_update, no_update)
    state = _load_all_state
    pages = state.get("pages", 0)
    total = state.get("total_items", 0)
    elapsed = state.get("elapsed_ms", 0)
    HIDE = {"display": "none"}

    if state.get("running"):
        # Still loading — update status bar only
        status = html.Div([
            html.I(className="bi bi-arrow-repeat me-2 spin-icon"),
            f"Loading page {pages + 1}… ({total:,} items so far · {elapsed:,}ms)",
        ], className="fetch-status-inner loading")
        return no_update, no_update, no_update, status, False, no_update

    # Auto-dismiss: if finished_at was set, wait 5s then clear status bar
    finished_at = state.get("finished_at")
    if finished_at and not state.get("done"):
        if time.time() - finished_at >= 5:
            state.pop("finished_at", None)
            return no_update, no_update, no_update, "", True, HIDE  # clear status, stop ticker
        return NO  # keep ticking, waiting to dismiss

    if not state.get("done"):
        return NO

    # Done or error — render final result and set dismiss timer
    if state.get("error"):
        status = html.Div([
            html.I(className="bi bi-exclamation-triangle-fill me-2"),
            f"Aborted after {pages} pages ({total:,} items · {elapsed:,}ms)",
        ], className="fetch-status-inner cancelled")
    else:
        status = html.Div([
            html.I(className="bi bi-check-circle-fill me-2"),
            f"All pages loaded — {total:,} items · {pages} pages · {elapsed:,}ms",
        ], className="fetch-status-inner done")

    items = state.get("items", [])
    list_key = state.get("list_key")
    initial_data = state.get("initial_data", {})
    last_req = state.get("last_req", {})

    merged_data = {**initial_data, list_key: items}
    merged_data.pop("has_more", None)
    merged_data.pop("next_page_token", None)
    merged_result = {
        "status_code": last_req.get("status_code", 200),
        "elapsed_ms": elapsed,
        "data": merged_data,
        "success": True, "error": None,
        "url": last_req.get("url", ""),
    }
    chips = extract_chips(last_req.get("endpoint_id", ""), merged_data)
    ep_id = last_req.get("endpoint_id", "")
    new_cache = dict(cache or {})
    if ep_id:
        new_cache[ep_id] = {"result": merged_result, "chips": chips or None}

    # Mark done, set dismiss timer — keep ticker running for auto-dismiss
    _load_all_state.update({"done": False, "items": [], "finished_at": time.time()})

    return build_response_panel(merged_result, chips), new_cache, chips or None, status, False, HIDE


# 11h-abort: Stop background Load All thread
@app.callback(
    Output("fetch-status-bar", "children", allow_duplicate=True),
    Output("load-all-abort-btn", "style", allow_duplicate=True),
    Input("load-all-abort-btn", "n_clicks"),
    prevent_initial_call=True,
)
def abort_load_all(n_clicks):
    """Callback 11h-abort: Signal the background Load All thread to stop."""
    if not n_clicks:
        return no_update, no_update
    _load_all_state["running"] = False
    _load_all_state["error"] = "Cancelled"
    return html.Div([
        html.I(className="bi bi-x-circle-fill me-2"),
        "Aborting…",
    ], className="fetch-status-inner cancelled"), {"display": "none"}


# 11h-abort-on-switch: Cancel Load All when a different endpoint is selected
@app.callback(
    Output("load-all-ticker", "disabled", allow_duplicate=True),
    Output("fetch-status-bar", "children", allow_duplicate=True),
    Output("load-all-abort-btn", "style", allow_duplicate=True),
    Input("selected-endpoint", "data"),
    prevent_initial_call=True,
)
def abort_load_all_on_switch(endpoint):
    """Callback 11h-abort-on-switch: Auto-cancel Load All when a different endpoint is selected."""
    if _load_all_state.get("running"):
        _load_all_state["running"] = False
        _load_all_state["error"] = "Cancelled"
    # Also clear any lingering dismiss timer
    _load_all_state.pop("finished_at", None)
    return True, "", {"display": "none"}


# 13. Search filter
@app.callback(
    Output({"type": "endpoint-btn", "id": ALL}, "style"),
    Input("search-input", "value"),
    State({"type": "endpoint-btn", "id": ALL}, "id"),
)
def filter_endpoints(query, btn_ids):
    """Callback 13: Filter sidebar buttons by name, path, category, or method."""
    if not query or not query.strip():
        return [{"display": "flex"} for _ in btn_ids]
    q = query.strip().lower()
    return [
        {"display": "flex"} if any(
            q in ENDPOINT_MAP.get(b["id"], {}).get(k, "").lower()
            for k in ("name", "path", "category", "method")
        ) else {"display": "none"}
        for b in btn_ids
    ]


# 14a. Show spinner immediately when Execute is clicked
app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks || n_clicks <= 0) return window.dash_clientside.no_update;
        document.title = '\u23f3 Updating\u2026 \u2014 Databricks API Explorer';
        return 'topbar-spinner';
    }
    """,
    Output("topbar-spinner", "className"),
    Input("execute-btn", "n_clicks"),
    prevent_initial_call=True,
)

# 14b. Hide spinner when the API call completes (spinner-off written by execute_api_call)
app.clientside_callback(
    """
    function(spinner_off) {
        document.title = 'Databricks API Explorer';
        return 'topbar-spinner topbar-spinner-hidden';
    }
    """,
    Output("topbar-spinner", "className", allow_duplicate=True),
    Input("spinner-off", "data"),
    prevent_initial_call=True,
)


# 15. Wire up postMessage from large-JSON iframes → iframe-link-click store.
#     set_props writes to the store from outside a Dash callback (event listener).
app.clientside_callback(
    """
    function(pathname) {
        if (!window._iframeLinkListenerAdded) {
            window._iframeLinkListenerAdded = true;
            window.addEventListener('message', function(e) {
                if (e.data && e.data.type === 'id-link') {
                    window.dash_clientside.set_props('iframe-link-click', {data: e.data});
                }
            });
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("iframe-link-click", "data"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)


# 16. Handle iframe inline link click — navigate to get endpoint with prefill
@app.callback(
    Output("selected-endpoint", "data", allow_duplicate=True),
    Output("response-container", "children", allow_duplicate=True),
    Output("response-cache", "data", allow_duplicate=True),
    Input("iframe-link-click", "data"),
    State("conn-config", "data"),
    State("response-cache", "data"),
    prevent_initial_call=True,
)
def handle_iframe_link_click(link_data, conn_config, cache):
    """Callback 16: Navigate to a *get* endpoint when an inline ID link is clicked."""
    if not link_data:
        return no_update, no_update, no_update
    get_id = link_data.get("gid", "")
    param_name = link_data.get("par", "")
    value = link_data.get("val", "")
    if not get_id or not param_name or value == "":
        return no_update, no_update, no_update

    endpoint = get_endpoint_by_id(get_id)
    if not endpoint:
        return no_update, no_update, no_update

    extras = link_data.get("ext") or {}
    path = endpoint["path"]
    query_params: Dict[str, Any] = {}
    prefill = {param_name: value, **extras}

    # Auto-fill account_id for account-scope get endpoints
    if endpoint.get("scope") == "account" and "account_id" not in prefill:
        profile = (conn_config or {}).get("profile")
        acct_id = get_account_id(profile)
        if acct_id:
            prefill["account_id"] = acct_id

    for k, v in prefill.items():
        if k in endpoint.get("path_params", []):
            path = path.replace(f"{{{k}}}", str(v))
        else:
            query_params[k] = v

    ws_host, ws_token = _resolve_conn(conn_config)
    if not ws_host:
        return no_update, build_error_panel("No workspace host."), no_update

    is_account = endpoint.get("scope") == "account"
    if is_account:
        host, token = resolve_account_connection(conn_config, _accounts_host(ws_host))
    else:
        host, token = ws_host, ws_token

    if not token:
        return no_update, build_error_panel("No auth token."), no_update

    method = endpoint.get("method", "GET")
    body = None
    if method == "POST" and query_params:
        body = query_params
        query_params = {}
    result = make_api_call(
        method=method,
        path=path, token=token, host=host,
        query_params=query_params or None,
        body=body,
    )
    chips = extract_chips(get_id, result["data"]) if result["success"] else []
    endpoint_with_prefill = {**endpoint, "_prefill": prefill}
    new_cache = dict(cache or {})
    new_cache[get_id] = {"result": result, "chips": chips or None}
    return endpoint_with_prefill, build_response_panel(result, chips), new_cache


# 17. Side-panel toggle — pure JS, no server round-trip
app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) return window.dash_clientside.no_update;
        var panel = document.getElementById('side-panel');
        if (panel) panel.classList.toggle('sp-collapsed');
        return window.dash_clientside.no_update;
    }
    """,
    Output("sp-dummy", "data"),
    Input("sp-toggle-btn", "n_clicks"),
    prevent_initial_call=True,
)


# 18. Side-panel item click → navigate to GET endpoint (reuses iframe-link-click flow)
@app.callback(
    Output("iframe-link-click", "data", allow_duplicate=True),
    Input({"type": "sp-item", "index": ALL}, "n_clicks"),
    State("chips-store", "data"),
    prevent_initial_call=True,
)
def handle_sp_item_click(n_clicks_list, chips_data):
    """Callback 18: Translate a side-panel item click into an iframe-link-click event."""
    from dash import callback_context
    if not callback_context.triggered or not chips_data:
        return no_update
    triggered = callback_context.triggered[0]
    if not triggered["value"]:
        return no_update
    import json as _json
    idx = _json.loads(triggered["prop_id"].split(".")[0])["index"]
    if idx >= len(chips_data):
        return no_update
    chip = chips_data[idx]
    msg = {"type": "id-link", "gid": chip["get_id"], "par": chip["param"], "val": chip["value"]}
    if chip.get("extras"):
        msg["ext"] = chip["extras"]
    return msg


# 18b. Side-panel action button click → navigate to action endpoint
@app.callback(
    Output("iframe-link-click", "data", allow_duplicate=True),
    Input({"type": "sp-action", "index": ALL, "action": ALL}, "n_clicks"),
    State("chips-store", "data"),
    prevent_initial_call=True,
)
def handle_sp_action_click(n_clicks_list, chips_data):
    """Callback 18b: Translate a side-panel action button click into an iframe-link-click event."""
    from dash import callback_context
    if not callback_context.triggered or not chips_data:
        return no_update
    triggered = callback_context.triggered[0]
    if not triggered["value"]:
        return no_update
    tid = json.loads(triggered["prop_id"].split(".")[0])
    idx, action_idx = tid["index"], tid["action"]
    if idx >= len(chips_data):
        return no_update
    chip = chips_data[idx]
    actions = chip.get("actions") or []
    if action_idx >= len(actions):
        return no_update
    action = actions[action_idx]
    # The action's params dict has all params needed; pick the first as the primary par/val
    params = action["params"]
    first_key = next(iter(params), "")
    first_val = params.get(first_key, "")
    ext = {k: v for k, v in params.items() if k != first_key}
    msg = {"type": "id-link", "gid": action["gid"], "par": first_key, "val": first_val}
    if ext:
        msg["ext"] = ext
    return msg


# 19. Build curl command below Execute button whenever a request completes
@app.callback(
    Output("curl-text", "children"),
    Output("curl-display", "style"),
    Input("last-request", "data"),
    State("conn-config", "data"),
    prevent_initial_call=True,
)
def update_curl_display(last_req, conn_config):
    """Callback 19: Build a ready-to-copy ``curl`` command from the last request."""
    from urllib.parse import urlencode
    if not last_req:
        return "", {"display": "none"}
    host, token = _resolve_conn(conn_config)
    method = last_req.get("method", "GET")
    base_url = last_req.get("url", "")
    query_params = last_req.get("query_params") or {}
    body = last_req.get("body")

    full_url = f"{base_url}?{urlencode(query_params)}" if query_params else base_url

    lines = [f"curl -X {method} \\", f"  '{full_url}' \\", f"  -H 'Authorization: Bearer {token}' \\",
             "  -H 'Content-Type: application/json'"]
    if body:
        lines[-1] += " \\"
        lines.append(f"  -d '{json.dumps(body, separators=(',', ':'))}'")

    return "\n".join(lines), {"display": "block"}


# 19b. Copy curl command to clipboard
app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) return window.dash_clientside.no_update;
        var el = document.getElementById('curl-text');
        var btn = document.getElementById('curl-copy-btn');
        if (!el || !btn) return window.dash_clientside.no_update;
        navigator.clipboard.writeText(el.textContent).then(function() {
            btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Copied!';
            setTimeout(function() {
                btn.innerHTML = '<i class="bi bi-clipboard me-1"></i>Copy';
            }, 1500);
        }).catch(function() {});
        return window.dash_clientside.no_update;
    }
    """,
    Output("curl-dummy", "data"),
    Input("curl-copy-btn", "n_clicks"),
    prevent_initial_call=True,
)




# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("DATABRICKS_APP_PORT", "8050"))
    app.run(debug=not IS_DATABRICKS_APP, host="0.0.0.0", port=port)
