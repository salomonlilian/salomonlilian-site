#!/usr/bin/env python3
"""Generate one static page per painting (works/<slug>/index.html), sitemap.xml and robots.txt
from the entry data embedded in index.html. Re-run after any change to a painting entry:

    python3 scripts/build_pages.py
"""
import html, json, re, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://salomonlilian.com"

SLUGS = {
    "rubens-hercules": "peter-paul-rubens-hercules-as-a-gladiator",
    "rubens-rosary": "peter-paul-rubens-the-virgin-and-child-of-the-rosary",
    "swabian-red-hat": "swabian-school-portrait-of-a-man-with-a-red-hat",
    "lievens": "jan-lievens-tronie-of-a-bearded-old-man-in-profile",
    "sweerts-turban": "michael-sweerts-young-man-wearing-a-turban-fingernail-test",
    "verelst": "pieter-verelst-self-portrait-with-a-black-beret",
    "backer": "jacob-backer-tronie-of-a-bearded-man-with-a-large-beret",
    "berckheyde": "job-berckheyde-view-of-the-old-stock-exchange-amsterdam",
    "sweerts-backgammon": "michael-sweerts-backgammon-players-in-an-interior",
    "marrel": "jacob-marrel-a-tulip-mania-painting",
    "van-der-pluym": "karel-van-der-pluym-tronie-of-a-man-with-a-red-cap",
    "claesz": "pieter-claesz-still-life-with-a-roemer-and-oysters-1642",
    "van-de-velde": "jan-van-de-velde-iii-still-life-with-a-gouda-pipe-1658",
    "rottenhammer": "hans-rottenhammer-adoration-of-the-christ-child-with-angels",
    "ruysdael": "salomon-van-ruysdael-a-river-view-with-a-bastion-1645",
    "sweerts-virgin": "michael-sweerts-the-virgin-at-prayer-with-self-portrait",
    "peeters-bouquet": "clara-peeters-a-bouquet-of-flowers-in-a-roemer-glass",
}

GALLERY = {
    "@type": "ArtGallery",
    "@id": SITE + "/#gallery",
    "name": "Salomon Lilian Dutch Old Master Paintings",
    "url": SITE + "/",
}

e = html.escape


def load():
    s = (ROOT / "index.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r'id="entry-data">(.*?)</script>', s, re.S).group(1))
    imgs, hidden = {}, set()
    for m in re.finditer(r'<div class="painting-card[^"]*" data-entry="([^"]+)"([^>]*)>(.*?)</div>\s*</div>', s, re.S):
        im = re.search(r'<img[^>]*src="([^"]+)"[^>]*alt="([^"]*)"', m.group(3))
        imgs[m.group(1)] = (im.group(1), html.unescape(im.group(2)))
        if " hidden" in m.group(2):
            hidden.add(m.group(1))
    pdfs = {m.group(1): m.group(2) for m in re.finditer(r'<a[^>]*id="(pdf-[^"]+)"[^>]*href="([^"]+)"', s)}
    pdfs.update({m.group(2): m.group(1) for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*id="(pdf-[^"]+)"', s)})
    return data, imgs, hidden, pdfs


def short_title(key, d, imgs):
    if len(d["title"]) <= 70:
        return d["title"]
    alt = imgs[key][1]
    suffix = ", " + d["artist"]
    if alt.endswith(suffix):
        return alt[: -len(suffix)]
    if alt.startswith(d["artist"] + ", "):
        return re.sub(r",? before \(left\).*$", "", alt[len(d["artist"]) + 2:])
    return d["title"]


def meta_desc(d):
    text = " ".join(p for p in d["essay"] if not p.startswith("## "))
    text = re.sub(r"\s+", " ", text)
    if len(text) > 155:
        text = text[:152].rsplit(" ", 1)[0] + "…"
    return text


def medium(d):
    for x in d["details"]:
        m = re.match(r"Oil on (\w+)", x)
        if m:
            return m.group(1)
    return None


def dims(d):
    for x in d["details"]:
        m = re.match(r"([\d.]+) × ([\d.]+) cm", x)
        if m:
            return m.group(1), m.group(2)
    return None


YEARS = {"marrel": "1635"}  # dates the regex cannot read


def year(d, key=None):
    if key in YEARS:
        return YEARS[key]
    for x in d["details"]:
        m = re.search(r"\b(1[5-7]\d\d)\b", x)
        if m and ("dated" in x or "Signed" in x or x.startswith("c.")):
            return m.group(1)
    return None


def jsonld(key, d, imgs, url, title):
    art = {
        "@type": "VisualArtwork",
        "@id": url + "#artwork",
        "name": d["title"],
        "alternateName": title if title != d["title"] else None,
        "url": url,
        "image": SITE + "/" + imgs[key][0],
        "description": meta_desc(d),
        "artform": "Painting",
        "creator": {"@type": "Person", "name": d["artist"], "description": d["life"]}
        if d["artist"] != "Swabian School" else {"@type": "Organization", "name": "Swabian School"},
        "provider": {"@id": SITE + "/#gallery"},
    }
    md = medium(d)
    if md:
        art["artMedium"] = "Oil"
        art["artworkSurface"] = md
    dm = dims(d)
    if dm:
        art["height"] = {"@type": "QuantitativeValue", "value": float(dm[0]), "unitCode": "CMT"}
        art["width"] = {"@type": "QuantitativeValue", "value": float(dm[1]), "unitCode": "CMT"}
    y = year(d, key)
    if y:
        art["dateCreated"] = y
    art = {k: v for k, v in art.items() if v is not None}
    crumbs = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Salomon Lilian", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": d["artist"] + ", " + title, "item": url},
        ],
    }
    graph = {"@context": "https://schema.org", "@graph": [art, crumbs, GALLERY]}
    return json.dumps(graph, ensure_ascii=False, indent=1).replace("</", "<\\/")


CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--ink:#0A0907;--ivory:#EDE6D6;--gold:#B8975A;--stone:#4A4035;--mist:#7A6E60;--panel:#130F0A}
body{background:var(--ink);color:var(--ivory);font-family:'Inter',sans-serif;font-weight:300;-webkit-font-smoothing:antialiased}
a{color:var(--gold)}
header{display:flex;justify-content:space-between;align-items:center;padding:28px 56px;border-bottom:1px solid var(--stone)}
.brand{font-family:'Cormorant Garant',serif;font-size:22px;letter-spacing:4px;text-transform:uppercase;color:var(--ivory);text-decoration:none}
.back{font-size:10px;letter-spacing:2.5px;text-transform:uppercase;text-decoration:none}
main{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:72px;max-width:1320px;margin:0 auto;padding:64px 56px 96px}
.media{position:sticky;top:40px;align-self:start;background:var(--panel);padding:40px;display:flex;justify-content:center}
.media img{max-width:100%;max-height:78vh;height:auto;display:block}
.artist{font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--gold)}
.life{font-size:11px;letter-spacing:1px;color:var(--mist);margin-top:8px}
h1{font-family:'Cormorant Garant',serif;font-weight:300;font-style:italic;font-size:40px;line-height:1.15;margin:22px 0 24px}
.details{list-style:none;margin-bottom:32px}
.details li{font-size:12px;color:var(--ivory);opacity:.82;line-height:1.8}
h2{font-weight:400;font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:var(--gold);margin:32px 0 12px}
.essay p{font-size:14px;line-height:1.95;opacity:.9;margin-bottom:16px}
.block ul{list-style:none}
.block li{font-size:12px;opacity:.8;line-height:1.7;margin-bottom:8px}
figure{margin:28px 0}figure img{max-width:100%;display:block}
figcaption{font-size:11px;color:var(--mist);margin-top:10px;line-height:1.6}
.actions{display:flex;flex-wrap:wrap;gap:14px;margin:36px 0 8px}
.btn{display:inline-block;border:1px solid var(--gold);color:var(--gold);padding:13px 22px;font-size:10px;letter-spacing:2.5px;text-transform:uppercase;text-decoration:none;transition:background .3s,color .3s}
.btn:hover{background:var(--gold);color:var(--ink)}
.more{border-top:1px solid var(--stone);max-width:1320px;margin:0 auto;padding:48px 56px}
.more ul{list-style:none;columns:2;column-gap:56px}
.more li{margin-bottom:10px;font-size:13px;break-inside:avoid}
.more a{text-decoration:none;color:var(--ivory);opacity:.85}.more a:hover{color:var(--gold)}
.more span{color:var(--mist)}
footer{border-top:1px solid var(--stone);padding:36px 56px;font-size:11px;letter-spacing:1px;color:var(--mist);line-height:1.9;display:flex;flex-wrap:wrap;gap:40px}
footer a{color:var(--mist)}
@media(max-width:900px){header{padding:18px 20px;gap:16px}.brand{font-size:16px;letter-spacing:3px;white-space:nowrap}.back{white-space:nowrap;letter-spacing:2px}main{grid-template-columns:1fr;gap:36px;padding:32px 20px 64px}.media{position:static;padding:20px}h1{font-size:30px}.more{padding:36px 20px}.more ul{columns:1}footer{padding:28px 20px}}
"""


def page(key, d, imgs, hidden, pdfs, all_items):
    slug = SLUGS[key]
    url = f"{SITE}/works/{slug}/"
    title = short_title(key, d, imgs)
    img, alt = imgs[key]
    desc = meta_desc(d)
    doc_title = f"{d['artist']}, {title} | Salomon Lilian Dutch Old Master Paintings"
    parts = []
    parts.append(f'<p class="artist">{e(d["artist"])}</p><p class="life">{e(d["life"])}</p>')
    parts.append(f'<h1>{e(d["title"])}</h1>')
    parts.append('<ul class="details">' + "".join(f"<li>{e(x)}</li>" for x in d["details"]) + "</ul>")
    essay = []
    if d.get("essay_heading"):
        essay.append(f"<h2>{e(d['essay_heading'])}</h2>")
    for p in d["essay"]:
        essay.append(f"<h2>{e(p[3:])}</h2>" if p.startswith("## ") else f"<p>{e(p)}</p>")
    parts.append('<div class="essay">' + "".join(essay) + "</div>")
    for f in d.get("figures") or []:
        parts.append(f'<figure><img src="/{e(f["src"])}" alt="{e(f["caption"])}" loading="lazy"><figcaption>{e(f["caption"])}</figcaption></figure>')
    acts = []
    pid = (d.get("pdf") or {}).get("id")
    if pid and pid != "none" and pid in pdfs:
        acts.append(f'<a class="btn" href="/{e(pdfs[pid])}" download>{e(d["pdf"]["label"])}</a>')
    acts.append('<a class="btn" href="/#contact">Enquire with the gallery</a>')
    parts.append('<div class="actions">' + "".join(acts) + "</div>")
    for name, items in d["lists"]:
        parts.append(f'<div class="block"><h2>{e(name)}</h2><ul>' + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul></div>")
    more = "".join(
        f'<li><a href="/works/{SLUGS[k]}/">{e(t)}</a> <span>· {e(a)}</span></li>'
        for k, a, t in all_items if k != key
    )
    back = "/#research" if key in hidden else "/#collection"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(doc_title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Salomon Lilian Dutch Old Master Paintings">
<meta property="og:title" content="{e(d['artist'] + ', ' + title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/{e(img)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garant:ital,wght@0,300;0,400;1,300&family=Inter:wght@300;400&display=swap" rel="stylesheet">
<style>{CSS}</style>
<script type="application/ld+json">
{jsonld(key, d, imgs, url, title)}
</script>
</head>
<body>
<header><a class="brand" href="/">Salomon Lilian</a><a class="back" href="{back}">&larr; The gallery</a></header>
<main>
<div class="media"><img src="/{e(img)}" alt="{e(alt)}"></div>
<article>{''.join(parts)}</article>
</main>
<section class="more"><h2>More works</h2><ul>{more}</ul></section>
<footer>
<div>Salomon Lilian Dutch Old Master Paintings</div>
<div>Spiegelgracht 5, 1017 JP Amsterdam</div>
<div>Rue Verdaine 6, CH-1204 Geneva</div>
<div><a href="tel:+33627812629">+33 627 812 629</a> · <a href="mailto:salomonlilianoldmasters@gmail.com">salomonlilianoldmasters@gmail.com</a></div>
</footer>
</body>
</html>
"""


def main():
    data, imgs, hidden, pdfs = load()
    missing = set(data) - set(SLUGS)
    if missing:
        raise SystemExit(f"Add a slug in SLUGS for: {', '.join(sorted(missing))}")
    # record each page's address in the entry data so the gallery dialog can link to it
    idx = ROOT / "index.html"
    src = idx.read_text(encoding="utf-8")
    m = re.search(r'(id="entry-data">)(.*?)(</script>)', src, re.S)
    for k in data:
        data[k]["page"] = f"/works/{SLUGS[k]}/"
    src = src[: m.start(2)] + json.dumps(data, ensure_ascii=False) + src[m.end(2):]
    idx.write_text(src, encoding="utf-8")
    items = [(k, data[k]["artist"], short_title(k, data[k], imgs)) for k in data]
    items.sort(key=lambda x: (x[1], x[2]))
    out = ROOT / "works"
    for k in data:
        p = out / SLUGS[k] / "index.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(page(k, data[k], imgs, hidden, pdfs, items), encoding="utf-8")
    today = datetime.date.today().isoformat()
    urls = [SITE + "/"] + [f"{SITE}/works/{SLUGS[k]}/" for k, _, _ in items]
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /scripts/\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(data)} pages, sitemap with {len(urls)} URLs")


if __name__ == "__main__":
    main()
