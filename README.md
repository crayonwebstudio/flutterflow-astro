# flutterflow-astro

Astro (v5.18.2) conversion of the FlutterFlow website archive (flutterflow.io).
The source site was itself built with Astro, so this project reproduces it
faithfully: the original head (inline CSS, meta, canonical, OG/Twitter,
font preloads, inline theme/GTM/UTM scripts) and the original body markup
are carried verbatim per page, and the original hashed `_astro` JS modules
are served unchanged.

## Source

- Archive: `~/workspace/flutterflow-original/flutterflow.io.zip` (635 MB,
  md5 c51b6ca1811ce24b70cea22ca9e52340), extracted to
  `~/workspace/flutterflow-original/flutterflow.io/` (1319 files, 692 MB).
  The original archive was never modified.
- Inventory: `~/workspace/flutterflow-original/INVENTORY.md` and `pages.json`.
- Conversion script: `tools/convert.py` (re-runnable, regenerates
  `src/pages/` and `src/source/` from the archive).

## What was converted

- **203 unique pages** (207 HTML/HTM files in the archive, 4 duplicates
  skipped: `index-1.htm`, `pricing-1.html`, `enterprise-1.html`,
  `studio/work-with-developers-1.html`). Links to the duplicate files are
  rewritten to the canonical page (for example blog posts linking
  `../index-1.htm?ref=blog.flutterflow.io` now link `/`).
- Page counts: blog 110, root 21, customer-stories 21, studio/showcase 19,
  author 12, studio/changelog 11, studio 8, changelog 3, designer 1,
  designer/changelog 1.
- Clean URLs: `pricing.html` is `/pricing/`, `blog/<slug>.html` is
  `/blog/<slug>/`, `index.htm` is `/`. No `.html` in output URLs.
- **Assets copied unchanged into `public/`** (1113 files, 658 MB),
  preserving relative paths: `_astro/` (19 JS modules, webp, woff2),
  `images/` (433 MB), `fonts/`, `blog-assets/` (including the 7 `.dart`
  download files), `hubfs/`, `66c1e912a9f78e8cf01dff25/`,
  `flutterflowdev.appspot.com/`, `c/`, `v1/`, `s/` (Cookie Script),
  `flutterflow-downloads/` (2 files, 113 MB, see below), plus
  `favicon-16.png`, `favicon-32.png`, `apple-touch-icon.png`.
  Asset counts: 553 png, 276 webp, 116 gif, 39 avif, 32 jpeg, 10 jpg,
  10 mp4, 20 js, 11 woff2, 35 svg, 7 dart, 1 pdf, 1 txt.
- The scaffold placeholder content is gone: no placeholder nav, hero copy,
  site name, or `example.com` site URL remains in `src/pages`,
  `src/layouts`, or `astro.config.mjs`. The 6 `example.com` strings left in
  the project are the source's own demo content (`alex@example.com` in
  login mockups on studio pages).

## How it works

- `src/layouts/MainLayout.astro` is the only layout. It takes the original
  `<html>` and `<body>` attributes plus the raw head and body HTML and
  renders them with `set:html`, so Astro does not re-parse, escape, or
  alter the source markup, CSS, or JS.
- `src/source/<slug>.head.html` / `.body.html` hold the extracted head and
  body for each page. `src/pages/<slug>.astro` imports them with `?raw`
  and passes them to MainLayout.
- Relative links were rewritten to root-absolute clean URLs, because Astro
  clean URLs live one directory deeper than the original flat `.html`
  files. Internal page links (`.html`/`.htm`) became clean URLs,
  asset links became `/<path>`. Absolute `https://www.flutterflow.io`
  canonical and OG URLs were kept as supplied.
- The scaffold `Header`, `Footer`, `Navigation`, `MobileMenu`, `Hero`,
  and `Button` components and `PageLayout` were removed: the source pages
  already contain their own header and footer in the body markup, and
  extracting shared components without changing the rendered output was
  not possible without risking fidelity. `src/styles/global.css` and
  `variables.css` are kept for reference only and are not loaded; the
  source inline CSS (2 `<style>` blocks per page, about 100 to 127 KB
  each) is authoritative.
- `astro.config.mjs`: `site` is
  `https://omnimercestage.woodwolfdigital.com` (the stage deployment
  domain) and `@astrojs/sitemap` generates the sitemap for that domain.
  This is a stage copy of flutterflow.io, so it must not be indexed:
  `public/robots.txt` Disallows all, `src/layouts/MainLayout.astro`
  injects `<meta name="robots" content="noindex, nofollow">` on every
  page, and `nginx.conf` adds `X-Robots-Tag "noindex, nofollow"`.
  The source canonical/OG URLs inside `src/source/*.head.html` still
  say `https://www.flutterflow.io` as supplied and were not rewritten.

## Build and verification

```bash
npm install
npm run build
npm run preview
```

- Build: exit 0, **203 pages built in 8.04s** (last full run).
- `dist/` holds 203 `index.html` files (695 MB total, mostly the copied
  public assets) and `sitemap-index.xml` / `sitemap-0.xml` listing 203 URLs.
- Sample checks passed: `/` title "Build an app by describing it ·
  FlutterFlow", `/pricing/` title "Pricing · FlutterFlow",
  `/ai/` title "FlutterFlow AI · Build your app with an AI agent",
  `/blog/` title "The FlutterFlow blog", a blog post, an author page, a
  customer-story page, `/studio/`, and `/designer/`, each with the correct
  title and H1 in `dist` HTML.
- Local asset audit of all 17,846 local `src`/`href`/`poster`/`srcset`
  references in `dist`: the only missing files are the 76 versioned
  desktop download links below. All `_astro` JS files referenced by
  index and pricing exist in `dist/_astro` with the same hashed names.
- Local preview check: `/` 200, `/pricing/` 200, a blog post 200, an
  `_astro` JS module 200, `sitemap-index.xml` 200.

## Known gaps and exclusions (source gaps, not conversion bugs)

- **Desktop installers:** only 2 installer files were in the archive
  (`flutterflow-downloads/designer/macos/prod/flutterflow-designer-latest-macos.dmg`
  and `.../designer/windows/prod/flutterflow-designer-latest-windows-setup.exe`,
  113 MB, both copied). `studio.html` and `studio/desktop.html` link to
  76 versioned macOS/Windows installers
  (`flutterflow-downloads/macos/...`, `.../macos-v7-1/...`,
  `.../windows_enterprise-.../...`, etc.) whose files were not in the
  archive, so those download links 404 in this build exactly as they
  would from the supplied archive. Supply the missing installers to fix.
- **OG images missing from the archive:** `images/v3/og.jpg` (85 pages),
  `social-share.png` (3 pages, also the Twitter image),
  `images/studio/og.png` (4 pages), `images/ai/og-ai.png` (1 page),
  7 `images/changelog/*-hero.*` images, and 4 `images/cdn/*` OG images.
  The OG tags still point at the absolute flutterflow.io URLs as supplied,
  so they resolve only if those files exist on the live domain. Body
  images are all present.
- **External integrations, kept as supplied, no credentials invented:**
  forms post to `https://build.flutterflow.io/signin` and to
  FlutterFlow/Hotjar/HubSpot style endpoints in the source JS; GTM and
  Cookie Script (`s/3423b15a1eef66feff758383200b359d.js`) run with the
  source IDs; links to `build.flutterflow.io`, `app.flutterflow.io`,
  `docs.flutterflow.io`, marketplace, community, and YouTube are kept
  as-is. None of these backends were tested with real credentials, and
  no keys were added.
- The 3 Webflow CDN OG images (`cdn.prod.website-files.com/...`) are
  external and were kept as absolute URLs, as supplied.

## Deploy

Target domain: **https://omnimercestage.woodwolfdigital.com** (stage).

### Site config

- `site` in `astro.config.mjs` is
  `https://omnimercestage.woodwolfdigital.com`, so the generated
  sitemap lists 203 URLs under that domain.
- `public/robots.txt` is `Disallow: /` for all user agents, with the
  sitemap URL pointing at the stage domain.

### Why this stage site is noindex (three layers)

This is a stage copy of flutterflow.io, so it must not be indexed or
it will compete with the real flutterflow.io in search results:

1. `public/robots.txt`: `Disallow: /`.
2. `src/layouts/MainLayout.astro` injects
   `<meta name="robots" content="noindex, nofollow">` in the `<head>`
   of every page, outside the raw source head HTML. Verified: present
   in all 203 pages in `dist/`.
3. `nginx.conf` adds `X-Robots-Tag "noindex, nofollow" always` on
   every response.

The `src/source/*.head.html` fragments were not edited, so their
canonical and OG URLs still say `https://www.flutterflow.io`. That is
deliberate for a stage copy: the noindex layers above are what keep
search engines from treating this as a duplicate of flutterflow.io.
If this ever becomes a production site on its own domain, those
canonical/OG URLs must be rewritten to the new domain first.

### Dockerfile and nginx

- `Dockerfile`: Node 22 Alpine build stage (`npm ci`, `npm run
  build`), then nginx Alpine serve stage, `dist/` copied to
  `/usr/share/nginx/html`, port 80.
- `nginx.conf`: listens on 80, serves from
  `/usr/share/nginx/html`, `try_files $uri $uri/ $uri.html =404`,
  `error_page 404 /404.html`, `X-Robots-Tag "noindex, nofollow"`,
  30-day immutable cache for css/js/images/fonts (including webp,
  avif, woff2, mp4, pdf).
- `.dockerignore` excludes `node_modules/`, `dist/`, `.astro/`,
  `.git/`, `tools/`, and `README.md`, so the image build context is
  just the source and public assets. `.gitignore` excludes
  `node_modules/`, `dist/`, `.astro/`, and `.env` files.
- Note: there is no 404 page in the source archive, so `dist/` has
  no `404.html`; nginx falls back to its built-in 404 until one is
  added.

### How to build

```bash
npm install
npm run build
```

Build: exit 0, 203 pages in about 8s. `dist/` is 695 MB (mostly the
copied public assets) and is not committed. Serve `dist/` with the
Dockerfile above, or any static host.

### Known blockers (not yet resolved)

- **Coolify API is currently 401**, so no Coolify project or app was
  created and nothing was deployed. That step is blocked separately.
- **GitHub push size:** the tree to push is about **696 MB**
  (725,289,711 bytes, excluding `dist/`, `node_modules/`, and
  `.astro/`): `public/` 658 MB plus `src/` 38 MB. Largest single
  files are the desktop installers,
  `public/flutterflow-downloads/designer/macos/prod/flutterflow-designer-latest-macos.dmg`
  (78 MB) and `.../designer/windows/prod/flutterflow-designer-latest-windows-setup.exe`
  (38 MB). Neither single file exceeds GitHub's 100 MB per-file
  limit, but the 696 MB total is far above a normal repo push, so
  expect a slow push and consider Git LFS for the large binaries,
  excluding the installers, or pushing in chunks. No git repo was
  created and nothing was pushed.
- **Canonical/OG URLs** in the source fragments still say
  `https://www.flutterflow.io` (see above). Do not launch this as a
  production site without rewriting them.
- **Dockerfile and nginx.conf were not tested locally:** neither
  `docker` nor `nginx` is installed on this machine, so the image
  was not built and the nginx config was not syntax-checked here.
  Build the image once on a machine with Docker before deploying.

No git repo, deploy, or push was done as part of this preparation.
