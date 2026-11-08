"""
render_dynamic.py

Turns parse_content.py's data into HTML. build_site2.py imports the
functions here to splice dynamic sections (gallery grid, product cards,
brand cards) into its existing pages, and to write the individual
build/event detail pages as separate files.
"""

import json
import re
import os
import html
import urllib.parse
import parse_content

UI_PATH = "User Input"  # relative path prefix used in generated <img src="">


def img_src(entry_or_folder_rel, filename):
    return f"{UI_PATH}/{entry_or_folder_rel}/{filename}"


def portfolio_img_src(filename):
    if str(filename).startswith("http"):
        return filename
    return f"{UI_PATH}/portfolio/{filename}"


def product_img_src(section, raw_name, filename):
    subpath = {"3d-printed": "products/3d-printed",
               "spare-deals": "products/store/spare-deals",
               "used-blasters": "products/store/used-blasters"}[section]
    return f"{UI_PATH}/{subpath}/{raw_name}/{filename}"


def brand_img_src(filename):
    return f"{UI_PATH}/brands/{filename}"


# ---------------------------------------------------------------------------
# GALLERY GRID (build-gallery.html)
# ---------------------------------------------------------------------------

_TS = r"\d{1,2}:\d{2}(?::\d{2})?"


def _ts_secs(ts):
    n = [int(x) for x in ts.split(":")]
    sec = 0
    for x in n:
        sec = sec * 60 + x
    return sec


def _chapters_html(items, has_video):
    rows = []
    for ts, label in items:
        if has_video:
            t = f'<button type="button" class="chapter-ts" data-seek="{_ts_secs(ts)}">{ts}</button>'
        else:
            t = f'<span class="chapter-ts">{ts}</span>'
        rows.append(f"<li>{t}<span class=\"chapter-label\">{label}</span></li>")
    return '<h3>Chapters</h3>\n      <ul class="chapters">' + "".join(rows) + "</ul>"


def _split_long(text, limit=260):
    """Break one long run of text into short paragraphs at sentence ends."""
    sents = re.split(r'(?<=[.!?])\s+(?=[A-Z"\u201c(])', text.strip())
    paras, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) > limit:
            paras.append(cur)
            cur = s
        else:
            cur = (cur + " " + s).strip()
    if cur:
        paras.append(cur)
    return paras


def breakdown_html(text, has_video=False):
    """Blank lines in the Breakdown become paragraphs, single line breaks stay line breaks.
    A short first line with no full stop (like "What's next") becomes a sub-heading.
    A "Chapters:" list (inline or one per line) becomes a timestamp list, and
    long unbroken text is split into readable paragraphs."""
    text = (text or "").strip()
    chapters = []
    m = re.search(r"(?:^|\s)Chapters?\s*:\s*", text, re.I)
    if m:
        tail = text[m.end():]
        text = text[:m.start()].strip()
        for cm in re.finditer(rf"({_TS})\s*[-\u2013:]?\s*(.+?)(?=[,;\n]\s*{_TS}\b|\s*$)", tail, re.S):
            chapters.append((cm.group(1), cm.group(2).strip().rstrip(",;. ").replace("\n", " ")))
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out = []
    for p in parts:
        lines = [l.strip() for l in p.split("\n") if l.strip()]
        if len(lines) > 1 and len(lines[0]) <= 40 and not re.search(r"[.!?:]$", lines[0]):
            out.append(f"<h3>{lines[0]}</h3>")
            lines = lines[1:]
        elif len(lines) == 1 and len(lines[0]) <= 40 and not re.search(r"[.!?]$", lines[0]):
            out.append(f"<h3>{lines[0]}</h3>")
            continue
        if len(lines) == 1 and len(lines[0]) > 300:
            out.extend("<p>" + x + "</p>" for x in _split_long(lines[0]))
        else:
            out.append("<p>" + "<br>".join(lines) + "</p>")
    if chapters:
        out.append(_chapters_html(chapters, has_video))
    return "\n      ".join(out)


def gallery_card(entry):
    kw_list = ",".join(k["kw"].lower() for k in entry["keywords"])
    thumb = portfolio_img_src(entry["images"][0]) if entry["images"] else ""
    type_badge = entry["type"]

    if entry["youtube"]:
        yt_id = extract_youtube_id(entry["youtube"])
        hover_start_sec = parse_content.timestamp_to_seconds(entry["hover_start"]) or 0
        return f'''    <a class="gallery-item gallery-video-card" href="builds/{entry['slug']}.html"
       data-keywords="{kw_list}" data-yt-id="{yt_id}" data-hover-start="{hover_start_sec}">
      <img src="{thumb}" alt="{entry['title']}" onerror="this.onerror=null;this.src=this.src.replace('maxresdefault','hqdefault')">
      <span class="gallery-type-badge">{type_badge} &middot; Video</span>
      <span class="play-overlay" aria-hidden="true">{PLAY_SVG_INLINE}</span>
      <div class="gallery-cap"><strong>{entry['title']}</strong><br>{entry['description']}</div>
    </a>'''
    return f'''    <a class="gallery-item" href="builds/{entry['slug']}.html" data-keywords="{kw_list}">
      <img src="{thumb}" alt="{entry['title']}">
      <span class="gallery-type-badge">{type_badge}</span>
      <div class="gallery-cap"><strong>{entry['title']}</strong><br>{entry['description']}</div>
    </a>'''


PLAY_SVG_INLINE = '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>'


def extract_youtube_id(url):
    import re
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    return m.group(1) if m else ""


def gallery_grid_html(portfolio):
    if not portfolio:
        return '<div class="wrap"><p style="color:var(--text-dim);">No builds or events uploaded yet.</p></div>'
    cards = "\n".join(gallery_card(e) for e in portfolio)
    return f'<div class="gallery-grid" id="dynamic-gallery">\n{cards}\n  </div>'


# ---------------------------------------------------------------------------
# PRODUCT CARDS (3d-printing.html / store.html)
# ---------------------------------------------------------------------------

def product_card(product, portfolio, show_status=False, show_price=False):
    thumb = product_img_src(product["section"], product["raw_name"], product["images"][0]) if product["images"] else ""
    examples = parse_content.resolve_product_examples(product, portfolio)
    kw_list = ",".join(k["kw"].lower() for k in product["keywords"])

    meta_line = ""
    if show_status and product.get("status"):
        cls = "status-in-stock" if product["status"].lower() == "in stock" else "status-print-to-order"
        meta_line = f'<span class="product-status {cls}">{product["status"]}</span>'
    if show_price and product.get("price"):
        meta_line += f'<span class="product-price">{product["price"]}</span>'

    examples_btn = ""
    if examples and kw_list:
        first_kw = kw_list.split(",")[0]
        examples_btn = f'<a class="btn small" href="build-gallery.html?keyword={first_kw}">See Examples</a>'

    return f'''    <div class="card product-card" data-keywords="{kw_list}" data-brand="{html.escape((product.get('brand') or '').lower())}">
      <img src="{thumb}" alt="{product['title']}">
      <div class="card-body">
        <h3>{product['title']}</h3>
        <p>{product['description']}</p>
        <div class="product-meta">{meta_line}</div>
        {examples_btn}
      </div>
    </div>'''


def products_grid_html(products, portfolio, show_status=False, show_price=False):
    if not products:
        return '<p style="color:var(--text-dim);">Nothing listed here yet.</p>'
    cards = "\n".join(product_card(p, portfolio, show_status, show_price) for p in products)
    return f'<div class="card-row cols-3">\n{cards}\n  </div>'


# ---------------------------------------------------------------------------
# BRAND CARDS (brands.html)
# ---------------------------------------------------------------------------

def brand_card(brand, all_products):
    if not brand.get("logo"):
        return ""  # no logo = skip entirely, per spec
    logo = brand_img_src(brand["logo"])
    desc = html.escape(brand.get("description") or "")
    return f'''    <a class="brand-tile2" href="brand/{brand['slug']}.html">
      <span class="brand-tile2-logo"><img src="{logo}" alt="{html.escape(brand['title'])}" loading="lazy"></span>
      {f'<span class="brand-tile2-desc">{desc}</span>' if desc else ''}
    </a>'''


def _product_link(product):
    anchor_map = {"3d-printed": "3d-printing.html", "spare-deals": "store.html", "used-blasters": "store.html"}
    return f'{anchor_map.get(product["section"], "#")}#{product["slug"]}'


def brands_grid_html(brands, products):
    cards = [brand_card(b, products) for b in brands]
    cards = [c for c in cards if c]
    if not cards:
        return '<p style="color:var(--text-dim);">No brand logos uploaded yet.</p>'
    return f'<div class="brand-grid2">\n{"".join(cards)}\n  </div>'


# ---------------------------------------------------------------------------
# BUILD / EVENT DETAIL PAGES
# ---------------------------------------------------------------------------

def keyword_buttons_html(entry, kw_index):
    """Buttons under a build's breakdown linking to matched products directly
    (not grouped by brand — that's the separate brand-logo section)."""
    seen = set()
    buttons = []
    for k in entry["keywords"]:
        kw_lower = k["kw"].lower()
        for p in kw_index.get(kw_lower, []):
            key = (p["section"], p["slug"])
            if key in seen:
                continue
            seen.add(key)
            buttons.append(f'<a class="btn small" href="{_product_link(p)}">{p["title"]}</a>')
    if not buttons:
        return ""
    return f'<div class="keyword-product-buttons">{"".join(buttons)}</div>'


def brand_section_html(entry, kw_index, brand_lookup):
    groups = parse_content.resolve_build_brands(entry, kw_index, brand_lookup)
    if not groups:
        return ""
    tiles = []
    for g in groups:
        brand = g["brand"]
        logo = brand_img_src(brand["logo"])
        items = "\n".join(
            f'<a href="{_product_link(p)}">{p["title"]}</a>' for p in g["products"]
        )
        link = brand.get("supplier_link") or "#"
        tiles.append(f'''    <div class="brand-tile">
      <a href="{link}" target="_blank" rel="noopener" class="brand-logo-link">
        <img src="{logo}" alt="{brand['title']}">
      </a>
      <div class="brand-submenu">{items}</div>
    </div>''')
    return f'''<div class="section-head" style="margin-top:40px;">
      <span class="kicker">Featured in this build</span>
      <h3>Brands</h3>
    </div>
    <div class="brand-grid">
{"".join(tiles)}
    </div>'''


def video_block_html(entry, kw_index=None, portfolio=None):
    if not entry["youtube"]:
        return ""
    yt_id = extract_youtube_id(entry["youtube"])
    related_html = related_tiles_html(entry, kw_index or {}, portfolio)
    hover_start_sec = parse_content.timestamp_to_seconds(entry["hover_start"]) or 0
    kw_timestamps = [
        {"label": k["kw"], "sec": parse_content.timestamp_to_seconds(k["ts"])}
        for k in entry["keywords"] if k["ts"]
    ]
    jump_buttons = "".join(
        f'<button class="btn small keyword-jump-btn" data-seek="{kt["sec"]}">{kt["label"]} ({entry["hover_start"] if False else ""}{_fmt_ts(kt["sec"])})</button>'
        for kt in kw_timestamps
    )
    return f'''<div class="video-highlight-player" data-yt-id="{yt_id}" data-start="{hover_start_sec}" data-duration="{entry.get('highlight_length') or 20}" id="detail-video">
      <div class="video-highlight-frame"></div>
      <div class="video-shield"></div>
      <div class="video-pause-overlay" hidden>
        <div class="vpo-left">
          <a class="btn primary video-full-btn" href="https://youtube.com/watch?v={yt_id}" target="_blank" rel="noopener">
            <svg viewBox="0 0 24 24" width="34" height="34" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>
            <span>Watch In Full</span>
          </a>
        </div>
        <div class="vpo-right">{related_html}</div>
      </div>
    </div>
    <div class="video-jump-row">{jump_buttons}</div>'''


def _next_video(entry, portfolio):
    """The closest related other video: most shared keywords, then same series,
    then whichever comes next in the gallery order."""
    vids = [o for o in (portfolio or []) if o.get("youtube")]
    others = [o for o in vids if o["slug"] != entry["slug"]]
    if not others:
        return None
    mine = {k["kw"].lower() for k in entry["keywords"]}
    order = [o["slug"] for o in vids]
    here = order.index(entry["slug"]) if entry["slug"] in order else -1

    def score(o):
        shared = len(mine & {k["kw"].lower() for k in o["keywords"]})
        series = 1 if entry.get("series") and o.get("series") == entry.get("series") else 0
        dist = (order.index(o["slug"]) - here) % len(order)   # 1 = the very next one
        return (-shared, -series, dist)
    return sorted(others, key=score)[0]


def related_tiles_html(entry, kw_index, portfolio):
    """Thin tiles for every product and other build/video sharing this entry's keywords."""
    tiles, seen = [], set()
    prod_done = False
    for k in entry["keywords"]:
        for pr in kw_index.get(k["kw"].lower(), []):
            key = ("p", pr["section"], pr["slug"])
            if key in seen or prod_done:
                continue
            seen.add(key)
            prod_done = True
            tiles.append(f'<a class="vpo-tile" href="{_product_link(pr)}"><span class="vpo-tag">Product</span><span class="vpo-name">{pr["title"]}</span></a>')
    mine = {k["kw"].lower() for k in entry["keywords"]}
    for o in portfolio or []:
        if o["slug"] == entry["slug"] or o.get("category") != "builds":
            continue
        if mine & {k["kw"].lower() for k in o["keywords"]}:
            if any('<span class="vpo-tag">Build</span>' in t for t in tiles):
                break
            tiles.append(f'<a class="vpo-tile" href="../builds/{o["slug"]}.html"><span class="vpo-tag">Build</span><span class="vpo-name">{o["title"]}</span></a>')
    nxt = _next_video(entry, portfolio)
    nxt_html = ""
    if nxt:
        nxt_html = (f'<a class="vpo-tile vpo-next" href="../builds/{nxt["slug"]}.html">'
                    f'<span class="vpo-tag">Next:</span><span class="vpo-name">{nxt["title"]}</span></a>')
    lst = "".join(tiles) or '<span class="vpo-empty">More from Bitchin\' Blasters in the Gallery</span>'
    return f'<div class="vpo-list">{lst}</div>{nxt_html}'


def _fmt_ts(seconds):
    if seconds is None:
        return ""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _image_numbers(images):
    """Photo number for each image: 'name 3.jpg' and 'name_3.jpg' are both 3.
    The un-numbered main photo counts as 1 (unless a 'name 1' / 'name_1' exists)."""
    nums = []
    for img in images:
        stem = os.path.splitext(os.path.basename(str(img)))[0]
        m = re.search(r"[ _](\d+)$", stem) if not str(img).startswith("http") else None
        nums.append(int(m.group(1)) if m else None)
    has_one = 1 in nums
    return [n if n is not None else (0 if has_one else 1) for n in nums]


CATEGORY_WORDS = {  # category -> (default prefill word, default button word)
    "builds": ("Builds", "build"),
    "events": ("Events", "event"),
    "tech-tips": ("Tech-Tips", "tip"),
    "reviews": ("Reviews", "product"),
}


def ask_base_msg(entry):
    plural, single = CATEGORY_WORDS.get(entry.get("category"), ("Gallery", "post"))
    about = entry.get("ask_prefill") or plural
    return f"I have a question about {about}, looking at {entry['title']}"


def ask_about_html(entry):
    plural, single = CATEGORY_WORDS.get(entry.get("category"), ("Gallery", "post"))
    word = entry.get("ask_about") or single
    msg = ask_base_msg(entry)
    href = "../your-build.html?msg=" + urllib.parse.quote(msg) + "#other-enquiries"
    return f'<p style="margin-top:32px;"><a href="{href}" class="btn primary">Ask about this {html.escape(word)}</a></p>'


def cap_img_html(entry, i, nums, extra_class="", hero=False):
    img = entry["images"][i]
    cap = html.escape(entry.get("captions", {}).get(nums[i], ""), quote=True)
    src = portfolio_img_src(img)
    alt = html.escape(entry["title"], quote=True)
    cap_el = f'<figcaption class="cap-text">{cap}</figcaption>' if cap else ""
    cls = f"cap-img {'cap-hero' if hero else 'gallery-item'} {extra_class}".strip()
    inner_img = f'<img src="{src}" alt="{alt}"' + (' class="detail-hero-img"' if hero else ' loading="lazy"') + ">"
    return (f'<figure class="{cls}" data-full="{src}" data-cap="{cap}" data-num="{nums[i]}">'
            f'<div class="cap-zoom">{inner_img}{cap_el}</div></figure>')


def detail_page_body(entry, kw_index, brand_lookup, portfolio=None):
    nums = _image_numbers(entry["images"])
    gallery_imgs = "\n".join(
        cap_img_html(entry, i, nums)
        for i in range(1, len(entry["images"]))  # first image already shown as hero/video
    )
    location_line = f'<p class="kicker">{entry["location"]}</p>' if entry.get("location") else ""
    hero_media = video_block_html(entry, kw_index, portfolio) if entry["youtube"] else (
        cap_img_html(entry, 0, nums, hero=True) if entry["images"] else ""
    )
    viewer_js = (("<script>window.BB_ASK=" + json.dumps({"base": ask_base_msg(entry), "url": "../your-build.html"}).replace("</", "<\\/") + ";</script>\n" + VIEWER_SCRIPT) if entry["images"] else "")

    kw_buttons = keyword_buttons_html(entry, kw_index)
    brand_section = brand_section_html(entry, kw_index, brand_lookup) if entry.get("category") == "builds" else ""

    return f'''<section class="page-banner detail-banner">
  <div class="page-banner-content">
    <h1>{entry['title']}</h1>
    {location_line}
  </div>
</section>
<section class="detail-section">
  <div class="wrap">
    <div class="detail-hero">{hero_media}</div>
    <div class="detail-breakdown">
      {breakdown_html(entry['breakdown'] or entry['description'], bool(entry['youtube']))}
    </div>
    <div id="products-used">{kw_buttons}</div>
    {gallery_imgs and f'<div class="gallery-grid" style="margin-top:32px;">{gallery_imgs}</div>'}
    {brand_section}
    {ask_about_html(entry)}
    <p style="margin-top:24px;"><a href="../build-gallery.html" class="btn">&larr; Back to Gallery</a></p>
  </div>
</section>
{viewer_js}'''


VIEWER_SCRIPT = """<script>
(function(){
  const items = Array.from(document.querySelectorAll('.cap-img'));
  if (!items.length) return;
  const canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  // ---- PC hover: grow to 2x from the corner furthest from screen centre, never leaving the screen ----
  if (canHover) {
    items.forEach(el => {
      if (el.classList.contains('cap-hero')) return;   // the top image does not pop up
      const zoom = el.querySelector('.cap-zoom');
      el.addEventListener('mouseenter', () => {
        const r = el.getBoundingClientRect(), vw = window.innerWidth, vh = window.innerHeight, m = 8;
        const growRight = (r.left + r.width / 2) < vw / 2;
        const growDown = (r.top + r.height / 2) < vh / 2;
        const availW = growRight ? vw - m - r.left : r.right - m;
        const availH = growDown ? vh - m - Math.max(r.top, m) : Math.min(r.bottom, vh - m) - m;
        let z = Math.min(2, availW / r.width, availH / r.height);
        if (z < 1.08) z = 1;
        zoom.style.transformOrigin = (growRight ? '0%' : '100%') + ' ' + (growDown ? '0%' : '100%');
        zoom.style.setProperty('--z', z);
        zoom.style.transform = 'scale(' + z + ')';
        el.classList.add('zoomed');
      });
      el.addEventListener('mouseleave', () => {
        el.classList.remove('zoomed');
        zoom.style.transform = '';
        zoom.style.setProperty('--z', 1);
      });
    });
  }

  // ---- Click / tap: near full-screen viewer with the caption ----
  const lb = document.createElement('div');
  lb.className = 'lb';
  lb.hidden = true;
  lb.innerHTML = '<button type="button" class="lb-x" aria-label="Close">&times;</button>' +
    '<button type="button" class="lb-nav lb-prev" aria-label="Previous">&lsaquo;</button>' +
    '<button type="button" class="lb-nav lb-next" aria-label="Next">&rsaquo;</button>' +
    '<figure class="lb-fig"><img alt=""><figcaption class="lb-cap"></figcaption>' +
    '<a class="btn small primary lb-ask" href="#">Ask about this photo</a></figure>';
  document.body.appendChild(lb);
  const lbImg = lb.querySelector('img'), lbCap = lb.querySelector('.lb-cap');
  let cur = 0;
  // Double tap (or double click) the big photo to close it and drop back to the post.
  let lastTap = 0;
  lbImg.addEventListener('touchend', e => {
    const now = Date.now();
    if (now - lastTap < 350) { e.preventDefault(); lastTap = 0; close(); } else { lastTap = now; }
  });
  lbImg.addEventListener('dblclick', () => close());
  function show(i) {
    cur = (i + items.length) % items.length;
    lbImg.src = items[cur].querySelector("img").currentSrc || items[cur].querySelector("img").src;
    lbImg.alt = items[cur].querySelector('img').alt;
    lbCap.textContent = items[cur].dataset.cap || '';
    const ask = lb.querySelector('.lb-ask');
    if (window.BB_ASK && ask) {
      const n = items[cur].dataset.num;
      ask.href = window.BB_ASK.url + '?msg=' + encodeURIComponent(window.BB_ASK.base + (n ? ', photo ' + n : '')) + '#other-enquiries';
    }
    lbCap.style.display = items[cur].dataset.cap ? '' : 'none';
  }
  function open(i) {
    show(i);
    lb.hidden = false;
    document.body.style.overflow = 'hidden';
    lb.classList.toggle('single', items.length < 2);
  }
  function close() { lb.hidden = true; lbImg.src = ''; document.body.style.overflow = ''; }
  items.forEach((el, i) => el.addEventListener('click', () => open(i)));
  lb.addEventListener('click', e => { if (e.target === lb || e.target.closest('.lb-x')) close(); });
  lb.querySelector('.lb-prev').addEventListener('click', e => { e.stopPropagation(); show(cur - 1); });
  lb.querySelector('.lb-next').addEventListener('click', e => { e.stopPropagation(); show(cur + 1); });
  document.addEventListener('keydown', e => {
    if (lb.hidden) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft') show(cur - 1);
    else if (e.key === 'ArrowRight') show(cur + 1);
  });
})();
</script>"""


def write_detail_pages(output_dir, page_fn, data):
    """page_fn: build_site2.page(title, description, active, body) -> full html string.
    Writes one file per portfolio entry into output_dir/builds/<slug>.html"""
    builds_dir = os.path.join(output_dir, "builds")
    os.makedirs(builds_dir, exist_ok=True)
    # Remove pages for builds/events that no longer exist, so deleting an entry
    # from User Input also removes its page on the next rebuild.
    for old_page in os.listdir(builds_dir):
        if old_page.endswith(".html"):
            os.remove(os.path.join(builds_dir, old_page))
    for entry in data["portfolio"]:
        body = detail_page_body(entry, data["kw_index"], data["brand_lookup"], data["portfolio"])
        # detail pages live one level deeper (builds/), so relative asset
        # paths need "../" — patch that in for nav/logo/footer links.
        html = page_fn(f"{entry['title']} — Bitchin' Blasters", entry["description"],
                        "build-gallery", body)
        html = _fix_relative_paths(html)
        with open(os.path.join(builds_dir, f"{entry['slug']}.html"), "w", encoding="utf-8") as f:
            f.write(html)


# ---------------------------------------------------------------------------
# BRAND DETAIL PAGES  (brand/<slug>.html)
# ---------------------------------------------------------------------------

def _brand_products(brand, products):
    out = []
    for section_products in products.values():
        for p in section_products:
            if p.get("brand", "").lower() == brand["title"].lower():
                out.append(p)
    return out


def _brand_gallery_matches(brand, portfolio):
    """Gallery entries whose keywords include one of the brand's keywords or
    the brand name itself. Videos first, then photos."""
    wanted = {k.lower() for k in brand.get("keywords", [])}
    wanted.add(brand["title"].lower())
    wanted.add(brand["slug"])
    hits = []
    for e in portfolio:
        kws = {k["kw"].lower() for k in e["keywords"]}
        if kws & wanted:
            hits.append(e)
    videos = [e for e in hits if e["youtube"]]
    photos = [e for e in hits if not e["youtube"]]
    return videos, photos


def brand_page_body(brand, data):
    title = html.escape(brand["title"])
    logos = brand.get("logos") or ([brand["logo"]] if brand.get("logo") else [])
    # logo #1 replaces the brand name as the page title; any extra logos
    # (name 2.png, name 3.png ...) are listed under it.
    logo_html = "".join(
        f'<img src="{brand_img_src(f)}" alt="{title} logo">' for f in logos[1:]
    )
    title_html = (f'<img class="brand-title-logo" src="{brand_img_src(logos[0])}" alt="{title}">'
                  if logos else title)
    products = _brand_products(brand, data["products"])
    videos, photos = _brand_gallery_matches(brand, data["portfolio"])

    # ---- buttons at the bottom: each opens the site section already filtered ----
    import urllib.parse as _u
    kws = [k for k in (brand.get("keywords") or [])] + [brand["title"]]

    def best_kw(entries):
        for k in kws:
            kl = k.lower()
            if any(kl in {x["kw"].lower() for x in e["keywords"]} for e in entries):
                return k
        return None

    btns = []
    store_prods = [p for p in products if p["section"] in ("spare-deals", "used-blasters")]
    print_prods = [p for p in products if p["section"] == "3d-printed"]
    q = _u.quote(brand["title"].lower())
    if store_prods:
        btns.append(f'<a class="btn primary" href="../store.html?brand={q}">Shop {title}</a>')
    if print_prods:
        label = f"Shop {title} (3D printed)" if store_prods else f"Shop {title}"
        btns.append(f'<a class="btn{"" if store_prods else " primary"}" href="../3d-printing.html?brand={q}">{label}</a>')
    if not products:
        msg = f"Hi, I'm interested in {brand['title']} parts. Can you help?"
        href = "../your-build.html?msg=" + _u.quote(msg) + "#other-enquiries"
        btns.append(f'<a class="btn primary" href="{href}">Ask about {title}</a>')
    vk = best_kw(videos)
    if vk:
        btns.append(f'<a class="btn" href="../build-gallery.html?keyword={_u.quote(vk.lower())}&kind=video">See {title} in action</a>')
    pk = best_kw(photos)
    if pk:
        btns.append(f'<a class="btn" href="../build-gallery.html?keyword={_u.quote(pk.lower())}&kind=photo">See {title} in builds</a>')
    if brand.get("supplier_link"):
        btns.append(f'<a class="btn" href="{html.escape(brand["supplier_link"])}" target="_blank" rel="noopener">Visit {title} website &#8599;</a>')

    breakdown = ""
    text = brand.get("breakdown") or brand.get("description") or ""
    if text:
        breakdown = f'<div class="detail-breakdown">{breakdown_html(text, False)}</div>'

    return f'''<section class="page-banner detail-banner">
  <div class="page-banner-content">
    <h1 class="brand-h1">{title_html}</h1>
  </div>
</section>
<section class="detail-section">
  <div class="wrap">
    {f'<div class="brand-logos">{logo_html}</div>' if logo_html else ''}
    {breakdown}
    <div class="brand-actions">{"".join(btns)}</div>
    <p style="margin-top:24px;"><a href="../brands.html" class="btn">&larr; All brands</a></p>
  </div>
</section>'''


def write_brand_pages(output_dir, page_fn, data):
    """Writes brand/<slug>.html for every brand that has a logo."""
    bdir = os.path.join(output_dir, "brand")
    os.makedirs(bdir, exist_ok=True)
    for old in os.listdir(bdir):
        if old.endswith(".html"):
            os.remove(os.path.join(bdir, old))
    n = 0
    for brand in data["brands"]:
        if not brand.get("logo"):
            continue
        body = brand_page_body(brand, data)
        desc = brand.get("description") or f"{brand['title']} — brand we endorse."
        page_html = page_fn(f"{brand['title']} — Bitchin' Blasters", html.escape(desc), "brands", body)
        page_html = _fix_relative_paths(page_html)
        with open(os.path.join(bdir, f"{brand['slug']}.html"), "w", encoding="utf-8") as f:
            f.write(page_html)
        n += 1
    return n


BRAND_FILTER_SCRIPT = """
  // ---- Product brand filter (?brand=xxx) from a brand page ----
  (function() {
    const b = (new URLSearchParams(window.location.search).get('brand') || '').toLowerCase();
    if (!b) return;
    const cards = Array.prototype.slice.call(document.querySelectorAll('.product-card'));
    if (!cards.length) return;
    let shown = 0;
    cards.forEach(function(c) {
      if ((c.dataset.brand || '') !== b) c.style.display = 'none'; else shown++;
    });
    const first = cards[0];
    const host = first.closest('section') || first.parentElement;
    const bar = document.createElement('div');
    bar.style.cssText = 'margin:0 0 18px;padding:12px 14px;border:1px solid var(--lime);display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap';
    bar.innerHTML = '<span>Showing <strong></strong> only' + (shown ? '' : ' &mdash; nothing listed right now') + '</span><a class="btn small" href="' + location.pathname + '">Show all</a>';
    bar.querySelector('strong').textContent = b.replace(/\\b\\w/g, function(m){ return m.toUpperCase(); });
    host.parentElement.insertBefore(bar, host);
  })();
"""

GALLERY_FILTER_SCRIPT = """
  // ---- Gallery keyword filter (?keyword=xxx) ----
  (function() {
    const params = new URLSearchParams(window.location.search);
    const kw = (params.get('keyword') || '').toLowerCase();
    if (!kw) return;
    document.querySelectorAll('#dynamic-gallery .gallery-item').forEach(item => {
      const kws = (item.dataset.keywords || '').split(',');
      if (!kws.includes(kw)) item.style.display = 'none';
    });
  })();
"""

VIDEO_SYSTEM_SCRIPT = """
  // ---- Shared YouTube highlight-clip system ----
  const HIGHLIGHT_DURATION = 20; // default seconds; a video page can override with Highlight Length in its txt

  let ytAPIReady = false;
  let ytAPIQueue = [];
  function loadYouTubeAPI(cb) {
    if (ytAPIReady && window.YT && window.YT.Player) { cb(); return; }
    ytAPIQueue.push(cb);
    if (document.getElementById('youtube-iframe-api')) return;
    const tag = document.createElement('script');
    tag.id = 'youtube-iframe-api';
    tag.src = 'https://www.youtube.com/iframe_api';
    document.head.appendChild(tag);
    window.onYouTubeIframeAPIReady = function() {
      ytAPIReady = true;
      ytAPIQueue.forEach(f => f());
      ytAPIQueue = [];
    };
  }

  function attachHighlightPlayer(mountEl, ytId, startSec, options) {
    options = options || {};
    let player = null;
    let capTimer = null;

    function clearCap() { if (capTimer) { clearTimeout(capTimer); capTimer = null; } }

    let capped = false;
    function armCap() {
      clearCap();
      capped = false;
      capTimer = setTimeout(() => {
        capped = true;
        capTimer = null;
        const pb = mountEl.querySelector('.video-play-btn');
        if (pb) pb.remove();
        if (player && player.pauseVideo) player.pauseVideo();
        if (options.onCap) options.onCap();
      }, (options.duration || HIGHLIGHT_DURATION) * 1000);
    }

    function create(muted) {
      const div = document.createElement('div');
      mountEl.appendChild(div);
      player = new YT.Player(div, {
        videoId: ytId,
        playerVars: {
          start: startSec, autoplay: 1, controls: (muted || options.clean) ? 0 : 1,
          modestbranding: 1, rel: 0, playsinline: 1,
          ...(options.clean ? { disablekb: 1, iv_load_policy: 3, fs: 0 } : {})
        },
        events: {
          // The clip timer starts when the video really starts playing, not when
          // the page loads (phones block autoplay with sound until you tap Play).
          onStateChange: (e) => {
            if (e.data === 1) {
              const pb = mountEl.querySelector('.video-play-btn');
              if (pb) pb.remove();
              if (!capTimer && !capped) armCap();
            }
          },
          onReady: (e) => {
            if (muted) { e.target.mute(); } else { e.target.unMute(); }
            e.target.playVideo();
            if (!muted && options.onUnmutedReady) {
              // Detect blocked autoplay: if still paused shortly after play(),
              // the browser blocked unmuted autoplay and needs a real click.
              setTimeout(() => {
                if (player.getPlayerState && player.getPlayerState() !== 1 && player.getPlayerState() !== 3) {
                  options.onUnmutedReady(player);
                }
              }, 1000);
            }
          }
        }
      });
    }

    function seekTo(sec) {
      if (!player || !player.seekTo) return;
      player.seekTo(sec, true);
      player.playVideo();
      if (options.onResume) options.onResume();
      armCap();
    }

    function destroy() {
      clearCap();
      if (player && player.destroy) player.destroy();
      player = null;
      mountEl.innerHTML = '';
    }

    return { create, seekTo, destroy, getPlayer: () => player };
  }

  // ---- Gallery grid: muted hover preview on video cards ----
  document.querySelectorAll('.gallery-item[data-yt-id]').forEach(card => {
    const ytId = card.dataset.ytId;
    const startSec = parseInt(card.dataset.hoverStart || '0', 10);
    let ctrl = null;
    let mount = null;
    if (window.matchMedia && window.matchMedia('(hover: none)').matches) return; // skip touch devices
    card.addEventListener('mouseenter', () => {
      loadYouTubeAPI(() => {
        mount = document.createElement('div');
        mount.style.cssText = 'position:absolute;inset:0;z-index:1;pointer-events:none;';
        card.appendChild(mount);
        ctrl = attachHighlightPlayer(mount, ytId, startSec, {});
        ctrl.create(true);
      });
    });
    card.addEventListener('mouseleave', () => {
      if (ctrl) { ctrl.destroy(); ctrl = null; }
      if (mount) { mount.remove(); mount = null; }
    });
  });

  // ---- Build/event detail page: full unmuted highlight player ----
  document.querySelectorAll('.video-highlight-player').forEach(playerBlock => {
    const ytId = playerBlock.dataset.ytId;
    const startSec = parseInt(playerBlock.dataset.start || '0', 10);
    const frame = playerBlock.querySelector('.video-highlight-frame');
    const overlay = playerBlock.querySelector('.video-pause-overlay');

    const shield = playerBlock.querySelector('.video-shield');
    const ctrl = attachHighlightPlayer(frame, ytId, startSec, {
      duration: parseInt(playerBlock.dataset.duration || '20', 10),
      clean: true,
      onCap: () => { if (overlay) overlay.hidden = false; },
      onResume: () => { if (overlay) overlay.hidden = true; },
      onUnmutedReady: (player) => {
        // The browser blocked autoplay with sound. Start it muted instead (always
        // allowed) and let the first tap anywhere on the video turn the sound on.
        player.mute();
        player.playVideo();
        ctrl.player = player;
        mutedFirstTap = true;
      }
    });
    // Clicking (or double clicking) the video opens it on YouTube. If the browser
    // forced a muted start, the very first tap turns the sound on instead.
    let mutedFirstTap = false, lastOpen = 0;
    if (shield) shield.addEventListener('click', () => {
      if (mutedFirstTap) { mutedFirstTap = false; try { ctrl.player && ctrl.player.unMute(); } catch (e) {} return; }
      const now = Date.now();
      if (now - lastOpen < 1000) return;   // a double click only opens one tab
      lastOpen = now;
      window.open('https://www.youtube.com/watch?v=' + ytId, '_blank', 'noopener');
    });
    loadYouTubeAPI(() => ctrl.create(false));

    document.querySelectorAll('.chapter-ts[data-seek]').forEach(btn => {
      btn.addEventListener('click', () => {
        ctrl.seekTo(parseInt(btn.dataset.seek, 10));
        playerBlock.scrollIntoView({behavior:'smooth', block:'center'});
      });
    });
    playerBlock.parentElement.querySelectorAll('.keyword-jump-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const sec = parseInt(btn.dataset.seek, 10);
        ctrl.seekTo(sec);
      });
    });
  });
"""


def _fix_relative_paths(html):
    """Detail pages are one folder deeper than the site root, so every
    relative link/asset path needs a '../' prefix. Absolute URLs (http/https)
    and already-relative '../' paths are left untouched."""
    import re
    def repl(m):
        attr, val = m.group(1), m.group(2)
        if val.startswith(("http://", "https://", "mailto:", "#", "../")):
            return m.group(0)
        return f'{attr}="../{val}"'
    return re.sub(r'(src|href)="([^"]+)"', repl, html)
