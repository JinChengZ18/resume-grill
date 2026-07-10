#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_pdf.py — pull plain text out of one or more resume PDFs.

Usage:
  python extract_pdf.py <a.pdf> [<b.pdf> ...] [--out candidates.json]

- With --out: writes a JSON list [{"file":..., "text":...}, ...] (UTF-8), ready to
  hand to the analysis workflow.
- Without --out: prints each file's text to stdout with a header separator.

Requires pypdf (already present in this environment). If a PDF is image-only,
extraction may be empty — fall back to the Read tool's PDF page rendering / OCR.
"""
import sys, json, io, os, unicodedata

def extract(path):
    import pypdf
    r = pypdf.PdfReader(path)
    parts = []
    for p in r.pages:
        parts.append(p.extract_text() or "")
    # NFKC repairs common pypdf artifacts: Kangxi-radical glyphs (⼤→大, ⼯→工),
    # ligatures (ﬂ→fl, so InﬂuxDB→InfluxDB), and full/half-width normalization.
    return unicodedata.normalize("NFKC", "\n".join(parts)).strip()

def main():
    args = [a for a in sys.argv[1:]]
    out = None
    if "--out" in args:
        i = args.index("--out"); out = args[i+1]; del args[i:i+2]
    if not args:
        print("usage: python extract_pdf.py <a.pdf> [b.pdf ...] [--out file.json]"); sys.exit(1)
    items = []
    for f in args:
        try:
            items.append({"file": os.path.basename(f), "path": f, "text": extract(f)})
        except Exception as e:
            items.append({"file": os.path.basename(f), "path": f, "text": "", "error": str(e)})
    if out:
        with open(out, "wb") as fh:
            fh.write(json.dumps(items, ensure_ascii=False, indent=1).encode("utf-8"))
        print("wrote " + out + "  (" + str(len(items)) + " file(s))")
        for it in items:
            print("  - %s : %d chars%s" % (it["file"], len(it["text"]),
                  ("  [ERROR: %s]" % it["error"]) if it.get("error") else ""))
    else:
        for it in items:
            sys.stdout.write("==== %s ====\n%s\n\n" % (it["file"], it["text"]))

if __name__ == "__main__":
    main()
