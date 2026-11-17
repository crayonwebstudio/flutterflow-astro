// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Stage deployment domain. This is a stage copy of flutterflow.io, so it
// must not be indexed: see public/robots.txt (Disallow all), the noindex
// meta in src/layouts/MainLayout.astro, and the X-Robots-Tag in nginx.conf.
// Source canonical/OG URLs inside src/source/*.head.html still point to
// https://www.flutterflow.io as supplied; they were deliberately not
// rewritten. Change them only if this ever becomes a production site.
export default defineConfig({
  site: 'https://omnimercestage.woodwolfdigital.com',
  output: 'static',
  integrations: [sitemap()],
});
