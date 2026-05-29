#!/usr/bin/env python3
"""LVRN QR · Release Ops CLI

Generate branded QR codes for LVRN releases & content.

Usage:
  python lvrn_qr.py generate --artist alxapo --type single --title lobola-szn --url https://open.spotify.com/...
  python lvrn_qr.py batch releases.csv
  python lvrn_qr.py registry

CSV columns: artist,type,title,url
"""
import argparse, json, csv, sys, os, datetime, re
from pathlib import Path

# Windows console: force UTF-8 so arrows / accents print cleanly.
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

try:
    import qrcode
    from qrcode.image.svg import SvgImage
    from PIL import Image, ImageDraw
except ImportError:
    print("Install deps: pip install qrcode[pil]", file=sys.stderr); sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
ARTISTS_FILE = ROOT / "web" / "artists.json"
REGISTRY_FILE = ROOT / "releases.json"
LINKS_FILE = ROOT / "redirects" / "links.json"
OUT_DIR = ROOT / "out"
OUT_DIR.mkdir(exist_ok=True)

SHORT_DOMAIN = "r.lvrn.dev"

def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def slugify(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s

def get_artist(roster, slug):
    for a in roster:
        if a["slug"] == slug: return a
    raise SystemExit(f"Unknown artist: {slug}. Available: {[a['slug'] for a in roster]}")

def generate_one(artist, type_slug, title, url, roster, ecc="Q"):
    artist_data = get_artist(roster, artist)
    title_slug = slugify(title)
    slug = "-".join(p for p in [artist, type_slug, title_slug] if p)
    short_url = f"{SHORT_DOMAIN}/{slug}"
    full_short = f"https://{short_url}"

    ecc_map = {"L": qrcode.constants.ERROR_CORRECT_L, "M": qrcode.constants.ERROR_CORRECT_M,
               "Q": qrcode.constants.ERROR_CORRECT_Q, "H": qrcode.constants.ERROR_CORRECT_H}
    qr = qrcode.QRCode(version=None, error_correction=ecc_map[ecc], box_size=20, border=2)
    qr.add_data(full_short); qr.make(fit=True)

    # PNG
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    png_path = OUT_DIR / f"{slug}.png"
    img.save(png_path)

    # SVG
    svg_path = OUT_DIR / f"{slug}.svg"
    svg = qrcode.make(full_short, image_factory=SvgImage,
                      error_correction=ecc_map[ecc], border=2)
    svg.save(str(svg_path))

    entry = {
        "artist": artist, "artistName": artist_data["name"],
        "type": type_slug, "title": title, "slug": slug,
        "shortUrl": short_url, "destination": url, "ecc": ecc,
        "files": {"png": str(png_path.relative_to(ROOT)), "svg": str(svg_path.relative_to(ROOT))},
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    # registry
    reg = load_json(REGISTRY_FILE, [])
    reg.insert(0, entry)
    save_json(REGISTRY_FILE, reg)

    # short-link redirect map
    links = load_json(LINKS_FILE, {})
    links[slug] = url
    save_json(LINKS_FILE, links)

    return entry

def cmd_generate(args, roster):
    e = generate_one(args.artist, args.type, args.title, args.url, roster, args.ecc)
    print(f"OK · {e['shortUrl']} → {e['destination']}")
    print(f"   PNG: {e['files']['png']}")
    print(f"   SVG: {e['files']['svg']}")

def cmd_batch(args, roster):
    n = 0
    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                e = generate_one(row["artist"], row["type"], row.get("title",""), row["url"], roster, row.get("ecc","Q"))
                print(f"  + {e['shortUrl']}")
                n += 1
            except Exception as ex:
                print(f"  ! {row}: {ex}", file=sys.stderr)
    print(f"\nGenerated {n} QR(s). Registry: {REGISTRY_FILE.name}, links: {LINKS_FILE.name}")

def cmd_registry(args, roster):
    reg = load_json(REGISTRY_FILE, [])
    if not reg: print("(empty)"); return
    for e in reg[:args.limit]:
        print(f"{e['createdAt'][:10]}  {e['artistName']:<14}  {e['type']:<8}  {e['shortUrl']:<32}  → {e['destination']}")

def main():
    roster = load_json(ARTISTS_FILE, {"roster": [], "contentTypes": []})["roster"]
    p = argparse.ArgumentParser(prog="lvrn-qr", description="LVRN QR Release Ops")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate one QR")
    g.add_argument("--artist", required=True)
    g.add_argument("--type", required=True)
    g.add_argument("--title", default="")
    g.add_argument("--url", required=True)
    g.add_argument("--ecc", default="Q", choices=["L","M","Q","H"])

    b = sub.add_parser("batch", help="Batch from CSV (artist,type,title,url[,ecc])")
    b.add_argument("csv")

    r = sub.add_parser("registry", help="Show recent QRs")
    r.add_argument("--limit", type=int, default=20)

    args = p.parse_args()
    {"generate": cmd_generate, "batch": cmd_batch, "registry": cmd_registry}[args.cmd](args, roster)

if __name__ == "__main__":
    main()
