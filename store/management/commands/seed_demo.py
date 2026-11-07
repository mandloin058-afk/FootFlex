"""Loads the demo catalogue, coupons, users and orders:  python manage.py seed_demo  [--reset]"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from store.models import (COLORWAYS, SIZES, STATUSES, Coupon, Order, OrderEvent, OrderItem, Product, ProductColor,
                          ProductStock, User)

DESC = {
    "Running": "Engineered for speed with a responsive foam midsole, breathable engineered mesh and a snug heel lock. Light, springy and ready for every kilometre.",
    "Lifestyle": "A clean everyday silhouette with a cushioned footbed and premium synthetic upper. Pairs with anything from joggers to chinos.",
    "Basketball": "High-traction outsole, supportive ankle collar and impact-absorbing cushioning built for explosive cuts on the court.",
    "Training": "Stable, flat-ish platform with a flexible forefoot for lifts, circuits and gym sessions. Reinforced sidewalls add durability.",
    "Casual": "Soft lining, lightweight sole and effortless style. The go-to pair for long days, commutes and weekend plans.",
    "Sports": "All-round performance trainer with grippy rubber outsole and ventilated upper for football, badminton and everything in between.",
}
SPECS = "Upper: Engineered mesh + synthetic overlays\nMidsole: FlexFoam™ EVA\nOutsole: High-abrasion rubber\nClosure: Lace-up\nCare: Wipe with a damp cloth. Do not machine wash."

# (name, category, type, price, mrp, [colours], options)
PRODUCTS = [
    ("Volt Runner X", "men", "Running", 6499, 8999, ["Neon Blue", "Grey", "Red", "Volt"], dict(featured=1, new=1, age=3)),
    ("Neon Pulse", "men", "Lifestyle", 5299, 6999, ["Neon Blue", "Red", "White", "Black"], dict(featured=1, pattern="stripe", age=9)),
    ("Street Phantom", "men", "Casual", 3799, 4999, ["Black", "Orange", "Red"], dict(pattern="dots", age=20)),
    ("Hyper Court Pro", "men", "Basketball", 8999, 11999, ["Neon Blue", "Royal Blue", "Red", "White"], dict(featured=1, new=1, age=5)),
    ("Aero Drift", "men", "Running", 4599, 5999, ["Neon Blue", "Grey", "Black"], dict(age=14)),
    ("Titan Trek", "men", "Training", 5799, 7499, ["Black", "Volt"], dict(pattern="stripe", age=30)),
    ("Orbit Low", "men", "Lifestyle", 2999, 3999, ["White", "Red"], dict(pattern="dots", age=40)),
    ("Apex Blaze", "men", "Sports", 4199, 5499, ["Royal Blue", "Grey"], dict(low=1, age=11)),
    ("Velocity Max", "men", "Running", 12999, 15999, ["Neon Blue", "Red", "Grey", "White"], dict(featured=1, new=1, age=2)),
    ("Cyber Glide", "women", "Running", 5499, 7299, ["Neon Blue", "Pink", "White", "Navy"], dict(featured=1, new=1, age=4)),
    ("Lunar Slip", "women", "Casual", 2499, 3299, ["Orange", "White", "Pink"], dict(pattern="dots", age=18)),
    ("Nebula Knit", "women", "Lifestyle", 4899, 6499, ["Navy", "Red", "White"], dict(pattern="stripe", age=8)),
    ("Flux Racer", "women", "Running", 5999, 7999, ["Grey", "Pink", "Volt"], dict(age=12)),
    ("Mirage Lite", "women", "Training", 4299, 5699, ["Black", "Navy"], dict(age=25)),
    ("Echo Walk", "women", "Casual", 1999, 2999, ["White", "Orange", "Pink"], dict(pattern="dots", age=50)),
    ("Pixel High", "women", "Basketball", 7499, 9999, ["Neon Blue", "White", "Pink", "Red"], dict(featured=1, age=7)),
    ("Cloud Stride", "women", "Sports", 3999, 5299, ["Navy", "Grey"], dict(low=1, age=16)),
    ("Zen Sprint", "women", "Running", 6299, 8299, ["Red", "Pink"], dict(new=1, age=6)),
    ("Rocket Jr", "kids", "Sports", 2299, 2999, ["Neon Blue", "Grey", "Volt"], dict(featured=1, new=1, age=5)),
    ("Mini Bolt", "kids", "Running", 1999, 2699, ["Royal Blue", "Red"], dict(age=10)),
    ("Tiny Titan", "kids", "Casual", 1799, 2399, ["Black", "Grey"], dict(pattern="stripe", age=22)),
    ("Jelly Hop", "kids", "Casual", 1499, 1999, ["Pink", "Navy", "White"], dict(pattern="dots", age=35)),
    ("Sparkle Dash", "kids", "Sports", 2199, 2899, ["Pink", "Volt"], dict(age=13)),
    ("Junior Court", "kids", "Basketball", 2799, 3699, ["White", "Royal Blue"], dict(low=1, age=19)),
]

COUPONS = [
    ("FOOTFLEX10", "10% off (up to ₹1,500) on orders above ₹1,999", "percent", 10, 1500, 1999),
    ("WELCOME200", "₹200 off on orders above ₹1,499", "flat", 200, None, 1499),
    ("FLEXFREE", "Free delivery on any order", "ship", 0, None, 0),
]


def stock_for(category, seed, low):
    out = {}
    for i, s in enumerate(SIZES[category]):
        v = (seed * 7 + i * 13 + 5) % 11
        out[s] = (3 if i == 2 else 2 if i == 4 else 0) if low else (0 if v < 2 else v + 2)
    return out


class Command(BaseCommand):
    help = "Load demo products, coupons, users and orders (use --reset to wipe the shop data first)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="delete products, orders and coupons first")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            Order.objects.all().delete()
            Product.objects.all().delete()
            Coupon.objects.all().delete()
            User.objects.filter(email__in=["admin@footflex.in", "demo@footflex.in"]).delete()
        elif Product.objects.exists():
            self.stdout.write("Products already exist — skipped (use --reset to reload).")
            return

        now = timezone.now()
        products = []
        for n, (name, cat, typ, price, mrp, colours, o) in enumerate(PRODUCTS, start=1):
            p = Product.objects.create(
                name=name, category=cat, type=typ, price=price, mrp=mrp, pattern=o.get("pattern", "swoosh"),
                description=DESC[typ], specs=SPECS, rating=round(4 + ((n * 37) % 10) / 12, 1),
                reviews=40 + (n * 53) % 460, featured=bool(o.get("featured")), is_new=bool(o.get("new")),
                sold=20 + (n * 17) % 120, created_at=now - timedelta(days=o.get("age", n * 6)),
            )
            ProductColor.objects.bulk_create([ProductColor(product=p, name=c, body=COLORWAYS[c][0], accent=COLORWAYS[c][1]) for c in colours])
            ProductStock.objects.bulk_create([ProductStock(product=p, size=s, qty=q) for s, q in stock_for(cat, n, o.get("low")).items()])
            products.append(p)

        for code, label, typ, value, mx, mn in COUPONS:
            Coupon.objects.update_or_create(code=code, defaults=dict(label=label, type=typ, value=value, max_discount=mx, min_order=mn))

        admin = User.objects.filter(email="admin@footflex.in").first()
        if not admin:
            admin = User.objects.create_superuser("admin@footflex.in", "admin@footflex.in", "admin123", first_name="FootFlex", last_name="Admin", phone="9000000000")
        demo = User.objects.filter(email="demo@footflex.in").first()
        if not demo:
            demo = User.objects.create_user("demo@footflex.in", "demo@footflex.in", "demo123", first_name="Aarav", last_name="Sharma",
                                            phone="9876543210", address_line="12, Lake View Apartments, Arera Colony",
                                            city="Bhopal", state="Madhya Pradesh", pin="462016")

        # (order id, [(product number, size, colour index, qty)], progress (index into STATUSES), days ago, payment)
        demo_orders = [
            ("FF-24A1B9", [(1, "9", 0, 1)], 5, 14, "UPI (aarav@okhdfc)"),
            ("FF-25C7D2", [(2, "8", 1, 1), (7, "8", 0, 1)], 3, 3, "Card ending 4242"),
            ("FF-26E3F5", [(4, "10", 0, 1)], 0, 0.2, "Cash on Delivery"),
        ]
        for oid, items, progress, days, pay in demo_orders:
            start = now - timedelta(days=days)
            lines = []
            for num, size, ci, qty in items:
                p = products[num - 1]
                c = list(p.colors.all())[ci]
                lines.append((p, size, c, qty))
            subtotal = sum(p.price * q for p, _, _, q in lines)
            shipping = 0 if subtotal >= 2999 else 99
            order = Order.objects.create(
                id=oid, user=demo, email=demo.email, name="Aarav Sharma", phone=demo.phone, address_line=demo.address_line,
                city=demo.city, state=demo.state, pin=demo.pin, payment=pay, subtotal=subtotal, shipping=shipping,
                total=subtotal + shipping, status=STATUSES[progress], created_at=start,
            )
            OrderItem.objects.bulk_create([OrderItem(order=order, product=p, name=p.name, price=p.price, size=s, qty=q,
                                                     color=c.name, body=c.body, accent=c.accent) for p, s, c, q in lines])
            span = timedelta(days=days) / max(progress, 1)
            for k in range(progress + 1):
                OrderEvent.objects.create(order=order, status=STATUSES[k], at=start + span * k)

        self.stdout.write(self.style.SUCCESS(f"Demo data loaded: {len(products)} products, {len(COUPONS)} coupons, 2 users, 3 orders."))
