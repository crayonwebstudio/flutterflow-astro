#!/usr/bin/env python3
"""Convert the FlutterFlow static HTML archive into Astro pages, faithfully.

Method (Orisa-style):
- One Astro page per unique source page, at the same clean URL.
- The source head (inline <style>, preloads, inline GTM/UTM/theme scripts,
  meta, canonical, OG/Twitter) and the source body inner HTML are extracted
  verbatim into src/source/<slug>.head.html / .body.html fragments.
- Pages import those fragments with ?raw and pass them to MainLayout, which
  renders them with set:html. Nothing in the source markup, CSS or JS is
  re-authored, so the rendered output matches the original.
- Relative asset and page links are rewritten to root-absolute clean URLs,
  because Astro clean URLs live one directory deeper than the original
  flat .html files (e.g. /blog/foo/ instead of /blog/foo.html). Absolute
  flutterflow.io canonical/OG URLs are kept as supplied.
- All non-HTML assets are copied unchanged into public/, preserving paths.

Source is read-only. Run from the project root: python3 tools/convert.py
Optional: python3 tools/convert.py --limit 3  (first 3 pages only, for testing)
"""
import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
SRC = Path("/home/hatch/workspace/flutterflow-original/flutterflow.io")
PAGES_JSON = Path("/home/hatch/workspace/flutterflow-original/pages.json")

DUPLICATES = {
    "index-1.htm",
    "pricing-1.html",
    "enterprise-1.html",
    "studio/work-with-developers-1.html",
}

# Duplicate source files are skipped, so links pointing at them must land
# on the canonical page instead (e.g. blog posts link ../index-1.htm).
DUPLICATE_CANONICAL = {
    "index-1.htm": "index.htm",
    "pricing-1.html": "pricing.html",
    "enterprise-1.html": "enterprise.html",
    "studio/work-with-developers-1.html": "studio/work-with-developers.html",
}


def clean_slug(rel: str) -> str:
    """Source path -> clean URL slug without extension, '' for the homepage."""
    p = rel
    for ext in (".html", ".htm"):
        if p.endswith(ext):
            p = p[: -len(ext)]
            break
    if p == "index" or p.endswith("/index"):
        p = p[: -len("index")].rstrip("/")
    return p


def clean_url(rel: str) -> str:
    slug = clean_slug(rel)
    return "/" if slug == "" else "/" + slug + "/"


def resolve_relative(page_dir: str, path: str) -> str:
    """Resolve a relative path against the source page directory, root-relative."""
    joined = posixpath.normpath(posixpath.join(page_dir, path)) if page_dir else posixpath.normpath(path)
    while joined.startswith("../"):
        joined = joined[3:]
    return joined.lstrip("/")


def rewrite_url(url: str, page_dir: str) -> str:
    if not url or url.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
        return url
    parts = urlsplit(url)
    if parts.scheme in ("http", "https", "mailto", "tel", "data", "javascript") or url.startswith("//"):
        return url
    path = parts.path
    if not path:
        return url
    suffix = ""
    if parts.query:
        suffix += "?" + parts.query
    if parts.fragment:
        suffix += "#" + parts.fragment
    if path.startswith("/"):
        if path.endswith((".html", ".htm")):
            resolved = DUPLICATE_CANONICAL.get(path.lstrip("/"), path.lstrip("/"))
            return clean_url(resolved) + suffix
        return url
    resolved = resolve_relative(page_dir, path)
    resolved = DUPLICATE_CANONICAL.get(resolved, resolved)
    if resolved.endswith((".html", ".htm")):
        return clean_url(resolved) + suffix
    return "/" + resolved + suffix


def rewrite_srcset(value: str, page_dir: str) -> str:
    out = []
    for entry in value.split(","):
        entry = entry.strip()
        if not entry:
            continue
        bits = entry.split()
        bits[0] = rewrite_url(bits[0], page_dir)
        out.append(" ".join(bits))
    return ", ".join(out)


ATTR_RE = re.compile(r'\b(src|href|poster|action)\s*=\s*"([^"]*)"')
SRCSET_RE = re.compile(r'\bsrcset\s*=\s*"([^"]*)"')
CSS_URL_RE = re.compile(r"url\(\s*\"([^\"]+)\"\s*\)|url\(\s*'([^']+)'\s*\)|url\(\s*([^)\s\"']+)\s*\)")
MD_LINK_RE = re.compile(r"\]\(([^)\s]+)(\s+\"[^\"]*\")?\)")


def rewrite_html(html: str, page_dir: str) -> str:
    def attr_sub(m):
        name, val = m.group(1), m.group(2)
        return f'{name}="{rewrite_url(val, page_dir)}"'

    html = ATTR_RE.sub(attr_sub, html)
    html = SRCSET_RE.sub(lambda m: f'srcset="{rewrite_srcset(m.group(1), page_dir)}"', html)

    def css_url_sub(m):
        val = m.group(1) or m.group(2) or m.group(3)
        if val.startswith(("data:", "http://", "https://", "#")):
            return m.group(0)
        return f'url("{rewrite_url(val, page_dir)}")'

    html = CSS_URL_RE.sub(css_url_sub, html)

    def md_sub(m):
        return f"]({rewrite_url(m.group(1), page_dir)}{m.group(2) or ''})"

    html = MD_LINK_RE.sub(md_sub, html)
    return html


def parse_attrs(tag_inner: str) -> dict:
    attrs = {}
    for m in re.finditer(r'([A-Za-z_:][\w:.\-]*)(?:\s*=\s*"([^"]*)"|\s*=\s*\'([^\']*)\')?', tag_inner):
        name = m.group(1)
        val = m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else "")
        attrs[name] = val
    return attrs


def attrs_literal(attrs: dict) -> str:
    if not attrs:
        return "{}"
    return "{" + ", ".join(f"{json.dumps(k)}: {json.dumps(v)}" for k, v in attrs.items()) + "}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    pages = json.loads(PAGES_JSON.read_text())
    seen_md5 = set()
    unique = []
    skipped = []
    for entry in pages:
        md5 = entry["md5"]
        if entry["path"] in DUPLICATES or md5 in seen_md5:
            skipped.append(entry["path"])
            continue
        seen_md5.add(md5)
        unique.append(entry)
    unique.sort(key=lambda e: e["path"])
    if args.limit:
        unique = unique[: args.limit]

    print(f"unique pages: {len(unique)}, duplicates skipped: {len(skipped)} -> {skipped}")

    # --- clean scaffold placeholders that conflict ---
    for comp in ("Header", "Footer", "Navigation", "MobileMenu", "Hero", "Button"):
        p = ROOT / "src" / "components" / f"{comp}.astro"
        if p.exists():
            p.unlink()
    for stale in (ROOT / "src" / "components").glob("*.astro"):
        stale.unlink()
    (ROOT / "src" / "components").mkdir(exist_ok=True)
    for f in (ROOT / "src" / "layouts" / "PageLayout.astro", ROOT / "src" / "scripts" / "main.js"):
        if f.exists():
            f.unlink()
    # old placeholder index page is replaced by generated pages
    old_index = ROOT / "src" / "pages" / "index.astro"
    if old_index.exists():
        old_index.unlink()
    # remove old generated pages/fragments on a full run so stale pages cannot linger
    if not args.limit:
        for d in (ROOT / "src" / "pages", ROOT / "src" / "source"):
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)

    (ROOT / "src" / "source").mkdir(parents=True, exist_ok=True)
    (ROOT / "src" / "pages").mkdir(parents=True, exist_ok=True)

    converted = []
    for entry in unique:
        rel = entry["path"]
        src_path = SRC / rel
        text = src_path.read_text(encoding="utf-8", errors="ignore").lstrip("\ufeff")
        m_html = re.search(r"<html([^>]*)>", text)
        m_head = re.search(r"<head>(.*?)</head>", text, re.S)
        m_body = re.search(r"<body([^>]*)>(.*)</body>", text, re.S)
        if not (m_html and m_head and m_body):
            print(f"WARN: could not parse {rel}", file=sys.stderr)
            continue
        html_attrs = parse_attrs(m_html.group(1))
        body_attrs = parse_attrs(m_body.group(1))
        page_dir = posixpath.dirname(rel)
        head_html = rewrite_html(m_head.group(1), page_dir)
        body_html = rewrite_html(m_body.group(2), page_dir)

        slug = clean_slug(rel)
        stem = slug if slug else "index"
        frag_dir = ROOT / "src" / "source" / posixpath.dirname(stem)
        frag_dir.mkdir(parents=True, exist_ok=True)
        base = posixpath.basename(stem)
        (frag_dir / f"{base}.head.html").write_text(head_html, encoding="utf-8")
        (frag_dir / f"{base}.body.html").write_text(body_html, encoding="utf-8")

        page_dir_out = ROOT / "src" / "pages" / posixpath.dirname(stem)
        page_dir_out.mkdir(parents=True, exist_ok=True)
        page_file = page_dir_out / f"{base}.astro"
        frag_rel = os.path.relpath(frag_dir, page_dir_out).replace(os.sep, "/")
        layout_rel = os.path.relpath(ROOT / "src" / "layouts" / "MainLayout.astro", page_dir_out).replace(os.sep, "/")
        if not frag_rel.startswith("."):
            frag_rel = "./" + frag_rel
        if not layout_rel.startswith("."):
            layout_rel = "./" + layout_rel
        page_file.write_text(
            "---\n"
            f"// Generated from source archive: {rel}\n"
            f"// Head and body are the original source markup, carried verbatim\n"
            f"// (inline styles, scripts, meta) via MainLayout set:html.\n"
            f"import MainLayout from '{layout_rel}';\n"
            f"import headHtml from '{frag_rel}/{base}.head.html?raw';\n"
            f"import bodyHtml from '{frag_rel}/{base}.body.html?raw';\n"
            f"const htmlAttrs = {attrs_literal(html_attrs)};\n"
            f"const bodyAttrs = {attrs_literal(body_attrs)};\n"
            "---\n\n"
            "<MainLayout htmlAttrs={htmlAttrs} bodyAttrs={bodyAttrs} headHtml={headHtml} bodyHtml={bodyHtml} />\n",
            encoding="utf-8",
        )
        converted.append((rel, str(page_file.relative_to(ROOT))))

    print(f"converted pages: {len(converted)}")
    for rel, out in converted[:5]:
        print("  ", rel, "->", out)
    if len(converted) > 5:
        print("   ...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
