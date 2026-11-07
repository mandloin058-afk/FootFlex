"""Session based shopping cart + price calculation."""
from django.conf import settings

from .models import Coupon, Product

SESSION_KEY = "cart"
COUPON_KEY = "coupon"


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.items = self.session.get(SESSION_KEY, [])  # [{pid,size,color,qty}]

    def save(self):
        self.session[SESSION_KEY] = self.items
        self.session.modified = True

    def __len__(self):
        return sum(i["qty"] for i in self.items)

    def add(self, pid, size, color, qty):
        for i in self.items:
            if (i["pid"], i["size"], i["color"]) == (pid, size, color):
                i["qty"] = min(i["qty"] + qty, 10)
                break
        else:
            self.items.append({"pid": pid, "size": size, "color": color, "qty": min(qty, 10)})
        self.save()

    def set_qty(self, idx, qty):
        if 0 <= idx < len(self.items):
            if qty <= 0:
                self.items.pop(idx)
            else:
                self.items[idx]["qty"] = min(qty, 10)
            self.save()

    def remove(self, idx):
        self.set_qty(idx, 0)

    def clear(self):
        self.items = []
        self.session.pop(COUPON_KEY, None)
        self.save()

    def lines(self):
        """Cart rows with live product data. Rows whose product/colour vanished are dropped."""
        products = Product.objects.prefetch_related("colors", "stocks").in_bulk([i["pid"] for i in self.items])
        out, kept = [], []
        for idx, i in enumerate(self.items):
            p = products.get(i["pid"])
            color = next((c for c in p.colors.all() if c.name == i["color"]), None) if p else None
            if not p or not color:
                continue
            stock = next((s.qty for s in p.stocks.all() if s.size == i["size"]), 0)
            kept.append(i)
            out.append({"idx": len(kept) - 1, "product": p, "color": color, "size": i["size"], "qty": i["qty"],
                        "price": p.price, "total": p.price * i["qty"], "stock": stock,
                        "problem": stock < i["qty"]})
        if len(kept) != len(self.items):
            self.items = kept
            self.save()
        return out


def totals(lines, code=""):
    subtotal = sum(l["total"] for l in lines)
    discount, free_ship, coupon, message = 0, False, None, ""
    if code:
        coupon = Coupon.objects.filter(code=code).first()
        if coupon:
            ok, discount, free_ship, message = coupon.evaluate(subtotal)
            if not ok:
                coupon, discount, free_ship = None, 0, False
        else:
            message = "Invalid coupon code"
    shipping = 0 if (not lines or subtotal - discount >= settings.FREE_SHIP_ABOVE or free_ship) else settings.SHIPPING_FEE
    return {
        "subtotal": subtotal, "discount": discount, "shipping": shipping,
        "total": subtotal - discount + shipping, "coupon": coupon, "coupon_message": message,
        "free_ship_left": max(0, settings.FREE_SHIP_ABOVE - (subtotal - discount)),
    }
