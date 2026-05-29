// lvrn.dev/r/:slug → 302 redirect using links.json registry.
import links from '../links.json' with { type: 'json' };

export default function handler(req, res) {
  const slug = String(req.query.slug || '').toLowerCase();
  const target = links[slug];
  if (!target) {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.status(404).send(`<!doctype html><meta charset="utf-8"><title>LVRN · 404</title>
<style>body{background:#0a0a0a;color:#fff;font-family:system-ui,sans-serif;display:grid;place-items:center;height:100vh;margin:0}
h1{font-weight:300;font-size:48px;letter-spacing:-.03em;margin:0 0 12px}
p{color:#5f5f5f;font-family:'JetBrains Mono',monospace;letter-spacing:.2em;text-transform:uppercase;font-size:11px;margin:0}</style>
<div><h1>404</h1><p>lvrn.dev/r/${slug} — not registered</p></div>`);
    return;
  }
  res.setHeader('Cache-Control', 'public, max-age=300, s-maxage=300');
  res.redirect(302, target);
}
