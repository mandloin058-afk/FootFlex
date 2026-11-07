import itertools

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()
_uid = itertools.count(1)


def shade(hex_color, amt):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    n = int(h, 16)

    def f(v):
        v = v + (255 - v) * amt if amt >= 0 else v * (1 + amt)
        return max(0, min(255, round(v)))

    r, g, b = f((n >> 16) & 255), f((n >> 8) & 255), f(n & 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def color_vars(body, accent):
    """CSS custom properties that recolour the sneaker artwork."""
    return (
        f"--b:{body};--bl:{shade(body, .32)};--bm:{shade(body, .12)};--bd:{shade(body, -.32)};"
        f"--bdd:{shade(body, -.6)};--a:{accent};"
    )


@register.filter
def inr(value):
    """12345 -> ₹12,345 (Indian digit grouping)."""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return "₹0"
    s, neg = str(abs(n)), n < 0
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-₹" if neg else "₹") + s


@register.filter
def mul(a, b):
    return int(a) * int(b)


@register.filter
def getitem(d, k):
    try:
        return d.get(k)
    except AttributeError:
        return None


@register.simple_tag
def swatch_attrs(color):
    """data-* attributes for a colour swatch button (JS copies them onto the artwork)."""
    v = color_vars(color.body, color.accent)
    return mark_safe(f'data-vars="{escape(v)}" data-name="{escape(color.name)}" '
                     f'style="background:linear-gradient(135deg,{color.body} 55%,{color.accent} 55%)"')


@register.simple_tag
def shoe(body="#0F2A5E", accent="#27B6FF", pattern="swoosh", label="Sneaker", css=""):
    """Inline vector sneaker. Every colour is a CSS variable, so swatches can recolour it instantly."""
    i = next(_uid)
    u = lambda n: f"{n}{i}"  # noqa: E731
    laces = "".join(
        f'<g><line x1="{160 + k / 5 * 132 - 1:.1f}" y1="{101 + k / 5 * 25.5 - 2:.1f}" x2="{160 + k / 5 * 132 - 6:.1f}" y2="{101 + k / 5 * 25.5 + 17:.1f}" stroke="#fafaf8" stroke-width="5.4" stroke-linecap="round"/>'
        f'<circle cx="{160 + k / 5 * 132 - 1:.1f}" cy="{101 + k / 5 * 25.5 - 1:.1f}" r="2" style="fill:var(--bdd)" opacity=".75"/></g>'
        for k in range(6)
    )
    if pattern == "stripe":
        side = ('<g style="fill:var(--a)"><path d="M124 178 L162 112 L176 114 L140 178 Z"/>'
                '<path d="M152 178 L190 116 L200 118 L166 178 Z" opacity=".85"/>'
                '<path d="M176 178 L214 122 L222 124 L190 178 Z" opacity=".65"/></g>')
    elif pattern == "dots":
        side = '<g style="fill:var(--a)">' + "".join(f'<circle cx="{120 + k * 24}" cy="{158 - k * 6}" r="5.5"/>' for k in range(5)) \
               + "".join(f'<circle cx="{132 + k * 24}" cy="{142 - k * 5}" r="4" opacity=".75"/>' for k in range(3)) + "</g>"
    else:
        side = '<path d="M92 164 C150 170 222 150 292 118 C240 160 172 188 92 170 Z" style="fill:var(--a)"/>'
    toe_dots = "".join(f'<circle cx="{352 + k * 8}" cy="{160 - k * 3}" r="1.7"/>' for k in range(4)) \
        + "".join(f'<circle cx="{344 + k * 8}" cy="{168 - k * 2}" r="1.7"/>' for k in range(3))
    air = "".join(f'<line x1="{x}" y1="194" x2="{x}" y2="204"/>' for x in (78, 92, 106, 120, 134))
    upper = "M46 176 C39 150 41 118 55 92 C59 85 69 82 80 85 C96 90 112 102 134 104 L158 100 L298 128 C342 134 383 148 389 172 L389 176 Z"
    svg = f'''<svg viewBox="20 36 380 200" class="shoe-art {escape(css)}" role="img" aria-label="{escape(label)}" xmlns="http://www.w3.org/2000/svg" style="{color_vars(body, accent)}">
<defs>
<linearGradient id="{u('up')}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--bl)"/><stop offset=".5" style="stop-color:var(--b)"/><stop offset="1" style="stop-color:var(--bd)"/></linearGradient>
<linearGradient id="{u('tg')}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color:var(--bl)"/><stop offset="1" style="stop-color:var(--bm)"/></linearGradient>
<linearGradient id="{u('so')}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset=".55" stop-color="#f5f5f3"/><stop offset="1" stop-color="#c6c6c1"/></linearGradient>
<linearGradient id="{u('win')}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:var(--a)" stop-opacity=".15"/><stop offset=".5" style="stop-color:var(--a)" stop-opacity=".75"/><stop offset="1" style="stop-color:var(--a)" stop-opacity=".15"/></linearGradient>
<linearGradient id="{u('hl')}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<pattern id="{u('mesh')}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><circle cx="1.6" cy="1.6" r="1.05" fill="#000" opacity=".22"/><circle cx="4.6" cy="4.6" r=".9" fill="#fff" opacity=".14"/></pattern>
<clipPath id="{u('clip')}"><path d="{upper}"/></clipPath>
</defs>
<ellipse cx="216" cy="221" rx="170" ry="7" fill="#000" opacity=".28"/>
<path d="{upper}" fill="url(#{u('up')})"/>
<g clip-path="url(#{u('clip')})">
<rect x="30" y="60" width="380" height="130" fill="url(#{u('mesh')})"/>
<path d="M298 128 C342 134 383 148 389 172 L389 178 L334 178 C334 156 322 138 298 128 Z" style="fill:var(--bd)" opacity=".7"/>
<g fill="#000" opacity=".28">{toe_dots}</g>
<path d="M46 178 C39 150 41 118 55 92 L88 96 C76 120 74 150 84 178 Z" style="fill:var(--bd)" opacity=".75"/>
{side}
</g>
<path d="M158 100 L298 128 L291 148 L150 120 Z" style="fill:var(--bm)"/>
<path d="M158 100 L298 128" style="stroke:var(--a)" stroke-width="2.4" fill="none" stroke-linecap="round"/>
<path d="M152 117 L291 145" stroke="#fff" stroke-width="1.2" stroke-dasharray="4 4" opacity=".5" fill="none"/>
{laces}
<path d="M163 100 C152 86 138 90 144 100 C148 106 158 104 163 100 Z" fill="#fafaf8" opacity=".95"/>
<path d="M163 100 C170 84 186 88 180 99 C177 105 168 104 163 100 Z" fill="#fafaf8"/>
<path d="M134 104 C138 80 150 60 170 55 C186 52 196 62 192 76 L178 106 Z" fill="url(#{u('tg')})"/>
<path d="M134 104 C138 80 150 60 170 55 C186 52 196 62 192 76" fill="none" style="stroke:var(--a)" stroke-width="2.2" stroke-linecap="round" opacity=".9"/>
<rect x="152" y="68" width="22" height="9" rx="2" transform="rotate(-14 152 68)" style="fill:var(--bdd)" opacity=".55"/>
<path d="M57 91 C69 86 80 88 94 95 C108 102 120 105 134 105 L129 115 C108 114 90 106 74 99 C66 96 60 97 56 99 Z" style="fill:var(--bdd)"/>
<path d="M55 92 C59 85 69 82 80 85 C96 90 112 102 134 104" fill="none" style="stroke:var(--a)" stroke-width="3" stroke-linecap="round"/>
<path d="M52 100 C44 94 42 82 48 76 C54 74 62 80 64 88 Z" style="fill:var(--a)"/>
<path d="M62 172 C58 150 60 128 70 108" fill="none" stroke="#fff" stroke-width="1.1" stroke-dasharray="3 3.4" opacity=".45"/>
<path d="M318 142 C332 150 338 160 338 172" fill="none" stroke="#fff" stroke-width="1.1" stroke-dasharray="3 3.4" opacity=".4"/>
<path d="M86 96 C118 100 150 92 176 70" fill="none" stroke="url(#{u('hl')})" stroke-width="3" stroke-linecap="round"/>
<path d="M200 112 C250 124 300 130 340 144" fill="none" stroke="url(#{u('hl')})" stroke-width="2.4" stroke-linecap="round" opacity=".8"/>
<path d="M40 170 C38 194 44 208 62 214 L300 214 C342 214 374 208 390 188 C396 180 394 172 385 171 C300 178 120 178 40 170 Z" fill="url(#{u('so')})"/>
<path d="M60 214 L300 214 C342 214 374 208 390 188" fill="none" style="stroke:var(--bdd)" stroke-width="5" stroke-linecap="round" opacity=".85"/>
<path d="M44 183 C140 190 300 190 388 181" fill="none" style="stroke:var(--a)" stroke-width="3.2" stroke-linecap="round"/>
<rect x="62" y="191" width="96" height="16" rx="8" fill="url(#{u('win')})" style="stroke:var(--a)" stroke-width="1" opacity=".95"/>
<g stroke="#fff" stroke-width="1.4" opacity=".55">{air}</g>
<g stroke="#000" stroke-width="1.2" opacity=".18" stroke-linecap="round"><line x1="250" y1="192" x2="250" y2="210"/><line x1="278" y1="192" x2="278" y2="210"/><line x1="306" y1="192" x2="306" y2="210"/></g>
</svg>'''
    return mark_safe(svg)


@register.simple_tag
def product_image(product, color=None, css="", hover=True):
    """Uploaded photo if the product has one (fitted by CSS), otherwise the vector sneaker.
    With 2+ photos the second one fades in on hover (like big shoe shops)."""
    urls = product.photo_list
    if urls:
        html = f'<img class="product-photo {escape(css)}" src="{escape(urls[0])}" alt="{escape(product.name)}" loading="lazy">'
        if hover and len(urls) > 1:
            html += f'<img class="product-photo hover" src="{escape(urls[1])}" alt="" loading="lazy" aria-hidden="true">'
        return mark_safe(html)
    # Never substitute vector/cartoon artwork for a missing product photo.
    return mark_safe(
        f'<div class="photo-placeholder {escape(css)}" role="img" '
        f'aria-label="Photo coming soon for {escape(product.name)}">'
        f'<span>Product photo coming soon</span></div>'
    )
