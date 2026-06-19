import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(process.cwd());
const distDir = path.join(root, 'dist');
const assetsDir = path.join(root, 'assets', 'brand');

const siteUrl = 'https://www.arkastrology.app';
const title = 'The Ark ✦ Astrology';
const description = 'Mystical, practical astrology readings that teach the chart as they guide the day.';
const themeColor = '#16322E';
const backgroundColor = '#F7F1E7';

const assetNames = [
  'favicon.png',
  'apple-touch-icon.png',
  'icon-192.png',
  'icon-512.png',
  'og-card.png',
  'brandmark.svg',
];

for (const assetName of assetNames) {
  fs.copyFileSync(path.join(assetsDir, assetName), path.join(distDir, assetName));
}

const manifest = {
  name: 'The Ark',
  short_name: 'The Ark',
  description,
  start_url: '/',
  display: 'standalone',
  background_color: backgroundColor,
  theme_color: themeColor,
  icons: [
    { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
    { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
  ],
};

fs.writeFileSync(path.join(distDir, 'manifest.webmanifest'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

const indexPath = path.join(distDir, 'index.html');
let html = fs.readFileSync(indexPath, 'utf8');

html = html.replace('<title>The Ark</title>', `<title>${title}</title>`);

const headBlock = `
    <meta name="description" content="${description}" />
    <meta name="theme-color" content="${themeColor}" />
    <meta name="apple-mobile-web-app-title" content="The Ark" />
    <meta name="application-name" content="The Ark" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="The Ark" />
    <meta property="og:title" content="${title}" />
    <meta property="og:description" content="${description}" />
    <meta property="og:url" content="${siteUrl}" />
    <meta property="og:image" content="${siteUrl}/og-card.png" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="${title}" />
    <meta name="twitter:description" content="${description}" />
    <meta name="twitter:image" content="${siteUrl}/og-card.png" />
    <link rel="icon" type="image/png" href="/favicon.png" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
    <link rel="manifest" href="/manifest.webmanifest" />`;

if (!html.includes('og:image')) {
  html = html.replace('</title>', `</title>\n${headBlock}`);
}

html = html.replace(/\s*<meta name="theme-color" content="#16322E">\s*<link rel="icon" href="\/favicon\.ico" \/>/i, '');

fs.writeFileSync(indexPath, html, 'utf8');
