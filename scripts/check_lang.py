#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_lang.py — catch source-language leakage in the generated payload.

The résumé and the deliverable often differ in language (e.g. a Chinese résumé asked to
produce English materials). The model must TRANSLATE any phrase it cites from the résumé,
never reproduce the original characters — otherwise an English-reading interviewer hits
unreadable CJK inside the answer keys.

This scans every model-generated string in payload.json and reports CJK characters when
the output language is not a CJK language. File names / link hrefs are exempt (the résumé
PDF legitimately keeps its original name).

Usage:
  python check_lang.py <payload.json>          # exit 1 if leakage found
  python check_lang.py <payload.json> --quiet   # only print on failure

Exit codes: 0 = clean, 1 = leakage found, 2 = bad usage.
"""
import io, json, re, sys

# CJK punctuation, kana, Han (incl. Ext-A / compat), Hangul, fullwidth forms
CJK_RE = re.compile(
    "[　-〿぀-ヿ㐀-䶿一-鿿"
    "豈-﫿가-힯＀-￯]"
)
CJK_LANGS = {"zh", "zh-cn", "zh-tw", "zh-hans", "zh-hant", "ja", "ko", "yue"}

# keys whose values legitimately keep the source script (file names, link targets)
EXEMPT_KEYS = {"resume", "href", "lang"}


def walk(node, path, hits):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in EXEMPT_KEYS:
                continue
            walk(v, f"{path}.{k}" if path else k, hits)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]", hits)
    elif isinstance(node, str):
        found = CJK_RE.findall(node)
        if found:
            hits.append((path, "".join(sorted(set(found))), node))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    if len(args) != 1:
        print("usage: python check_lang.py <payload.json> [--quiet]", file=sys.stderr)
        sys.exit(2)

    with io.open(args[0], encoding="utf-8") as f:
        payload = json.load(f)
    lang = str(payload.get("meta", {}).get("lang") or "").lower()

    if lang in CJK_LANGS or not lang:
        if not quiet:
            print("skip: output language is %r — CJK is expected" % (lang or "unset"))
        sys.exit(0)

    hits = []
    walk(payload, "", hits)
    if not hits:
        if not quiet:
            print("OK: no CJK leakage in payload (lang=%s)" % lang)
        sys.exit(0)

    print("FAIL: %d field(s) leak source-language characters (lang=%s)" % (len(hits), lang))
    for path, chars, text in hits:
        snippet = text if len(text) <= 110 else text[:107] + "..."
        print("  %-34s  [%s]\n      %s" % (path, chars, snippet.replace("\n", " ")))
    print("\nFix: have the model rewrite those fields with the cited phrases translated,")
    print("or edit payload.json directly, then re-run render.py.")
    sys.exit(1)


if __name__ == "__main__":
    main()
