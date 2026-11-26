#!/usr/bin/env python3
"""Execute the shipped page script under node with DOM stubs; fail on any exception.

Why: the page is the only artifact whose logic never runs in any of the other checks. A missing
variable declaration in one panel's render loop threw a ReferenceError that killed every panel after
it, and every python-side gate stayed green because they only compare numbers in the payload. The
payload was correct; the page was blank. This runs the real script against the real embedded JSON.

Not a browser test: it proves the code parses and executes end to end without throwing, which is the
failure that shipped. Layout and CSS are not checked.

Exit codes: 0 executed clean, 1 threw, 2 harness problem (no node, no payload).
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "out" / "index.html"

PRELUDE = r"""
function __el(id) {
  const o = {
    id: id, textContent: '', innerHTML: '', outerHTML: '', value: '',
    className: '', checked: false, disabled: false, href: '', src: '', title: '',
    style: new Proxy({}, { get: () => '', set: () => true }),
    dataset: {},
    classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
    children: [], childNodes: [],
    appendChild(c){ this.children.push(c); return c; },
    removeChild(){}, remove(){}, setAttribute(){}, getAttribute(){ return null; },
    addEventListener(){}, removeEventListener(){}, focus(){}, blur(){}, click(){},
    querySelector(){ return __el('q'); }, querySelectorAll(){ return []; },
    getBoundingClientRect(){ return {top:0,left:0,right:0,bottom:0,width:800,height:600}; },
    insertAdjacentHTML(){}, cloneNode(){ return __el('c'); },
  };
  return o;
}
const __payload = globalThis.__PAYLOAD__ || '';
const __byId = { data: Object.assign(__el('data'), { textContent: __payload }) };
globalThis.document = {
  getElementById: (id) => (__byId[id] || (__byId[id] = __el(id))),
  querySelector: () => __el('q'), querySelectorAll: () => [],
  createElement: (t) => __el(t), createTextNode: (t) => ({ textContent: t }),
  addEventListener(){}, removeEventListener(){},
  body: __el('body'), documentElement: __el('html'),
  head: __el('head'), title: '',
};
globalThis.window = {
  addEventListener(){}, removeEventListener(){},
  matchMedia: () => ({ matches: false, addEventListener(){}, addListener(){} }),
  location: { href: 'https://example.invalid/', hash: '' },
  localStorage: { getItem: () => null, setItem(){}, removeItem(){} },
  innerWidth: 1280, innerHeight: 900, devicePixelRatio: 1,
  requestAnimationFrame: (f) => setTimeout(f, 0), cancelAnimationFrame(){},
  getComputedStyle: () => ({ getPropertyValue: () => '' }),
  scrollTo(){},
};
globalThis.addEventListener = globalThis.window.addEventListener;
globalThis.requestAnimationFrame = globalThis.window.requestAnimationFrame;
globalThis.matchMedia = globalThis.window.matchMedia;
globalThis.localStorage = globalThis.window.localStorage;
globalThis.navigator = { userAgent: 'node' };
"""


def extract(html: str, page: pathlib.Path | None = None) -> tuple[str, str]:
    """Return (payload_json, app_script).

    The payload is the application/json block. The app script used to be inline; it now lives in
    `assets/app.js` and is referenced by `<script src=...>`, so a gate that only reads inline blocks would
    find no script at all and pass on nothing. Every non-JSON script counts, inline or linked, concatenated
    in document order: a second file added later is then included here instead of being silently skipped.
    """
    payload = ""
    m = re.search(r'<script[^>]*id="data"[^>]*>(.*?)</script>', html, re.S)
    if m:
        payload = m.group(1)

    parts: list[str] = []
    base = (page.parent if page else PAGE.parent)
    for tag, body in re.findall(r"<script([^>]*)>(.*?)</script>", html, re.S):
        if "application/json" in tag or 'id="data"' in tag:
            continue
        src = re.search(r'src="([^"]+)"', tag)
        if src:
            path = (base / src.group(1)).resolve()
            if not path.exists():
                raise FileNotFoundError(f"page references a missing script: {path}")
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
        elif body.strip():
            parts.append(body)
    return payload, "\n".join(parts)


def main() -> int:
    node = shutil.which("node")
    if not node:
        print("node not found", file=sys.stderr)
        return 2
    if not PAGE.exists():
        print("out/index.html missing", file=sys.stderr)
        return 2
    page = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else PAGE
    payload, app = extract(page.read_text(encoding="utf-8", errors="replace"), page)
    if not payload or not app:
        print("could not extract payload or app script", file=sys.stderr)
        return 2
    try:
        json.loads(payload)
    except json.JSONDecodeError as e:
        print(f"FAIL  embedded payload is not valid JSON: {e}")
        return 1

    harness = (
        "globalThis.__PAYLOAD__ = " + json.dumps(payload) + ";\n"
        + PRELUDE
        + "\ntry {\n" + app + "\nconsole.log('EXECUTED_CLEAN');\n}"
        + " catch (e) { console.error('THREW: ' + (e && e.stack ? e.stack.split('\\n').slice(0,4).join('\\n') : e)); "
        + "process.exitCode = 1; }\n"
    )
    tmp = ROOT / ".lane-scratch" / "_page_check.js"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(harness, encoding="utf-8")

    r = subprocess.run([node, str(tmp)], capture_output=True, text=True, timeout=120)
    out = (r.stdout or "") + (r.stderr or "")
    if "EXECUTED_CLEAN" in r.stdout and r.returncode == 0:
        print("PASS  page script executes end to end with the embedded payload")
        return 0
    print("FAIL  page script threw; every panel after the failure never renders")
    for line in out.strip().splitlines()[:14]:
        print("   ", line)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
