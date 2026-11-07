import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import COUPON_KEY, Cart, totals
from .forms import AddressForm, RegisterForm
from .models import CATEGORIES, SIZES, TYPES, Coupon, Order, Product, ProductColor, Wishlist
from .services import OrderError, change_status, create_order

PAGE_SIZE = 12
TITLES = {"men": "Men’s Sneakers", "women": "Women’s Sneakers", "kids": "Kids’ Sneakers"}
SORTS = [
    ("featured", "Featured"), ("new", "Newest"), ("price-asc", "Price: Low to High"),
    ("price-desc", "Price: High to Low"), ("rating", "Top rated"), ("discount", "Biggest discount"),
]
SIZE_CHARTS = {
    "men": [("6", "24.5"), ("7", "25.4"), ("8", "26.2"), ("9", "27.1"), ("10", "27.9"), ("11", "28.8")],
    "women": [("3", "22.0"), ("4", "22.9"), ("5", "23.7"), ("6", "24.6"), ("7", "25.4"), ("8", "26.3")],
    "kids": [("1", "19.8"), ("2", "20.7"), ("3", "21.5"), ("4", "22.4"), ("5", "23.2")],
}


def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def products_qs():
    return Product.objects.prefetch_related("colors", "stocks", "photos")


# ------------------------------------------------------------------ home / shop

def home(request):
    qs = products_qs().annotate(stock_total=Sum("stocks__qty"))
    in_stock = qs.filter(stock_total__gt=0)
    featured = list(in_stock.filter(featured=True).order_by("-sold")[:5]) or list(in_stock[:5])
    tiles = []
    for key, label in CATEGORIES:
        p = qs.filter(category=key).order_by("-featured", "-sold").first()
        tiles.append({"key": key, "label": label, "product": p,
                      "tag": {"men": "Power. Speed. Street.", "women": "Light. Bold. Yours.", "kids": "Built for play."}[key]})
    ctx = {
        "featured": featured,
        "tiles": tiles,
        "new_arrivals": list(qs.filter(is_new=True).order_by("created_at")[:4]),
        "best_sellers": list(qs.order_by("-sold")[:4]),
        "total_products": Product.objects.count(),
    }
    return render(request, "store/home.html", ctx)


def shop(request, category=None):
    g = request.GET
    cat = category or g.get("cat", "")
    q = g.get("q", "").strip()
    sort = g.get("sort", "featured")
    types = [t for t in g.getlist("type") if t in TYPES]
    sizes = g.getlist("size")
    colors = g.getlist("color")
    try:
        max_p = int(g.get("max") or 0)
        min_rating = float(g.get("rating") or 0)
    except ValueError:
        max_p, min_rating = 0, 0
    only_stock = g.get("stock") == "1"
    only_sale = g.get("sale") == "1"

    qs = products_qs().annotate(stock_total=Sum("stocks__qty"))
    if cat in dict(CATEGORIES):
        qs = qs.filter(category=cat)
    else:
        cat = ""
    if q:
        for word in q.split():
            qs = qs.filter(Q(name__icontains=word) | Q(type__icontains=word) | Q(category__icontains=word)
                           | Q(colors__name__icontains=word))
    if types:
        qs = qs.filter(type__in=types)
    if sizes:
        qs = qs.filter(stocks__size__in=sizes, stocks__qty__gt=0)
    if colors:
        qs = qs.filter(colors__name__in=colors)
    if max_p:
        qs = qs.filter(price__lte=max_p)
    if min_rating:
        qs = qs.filter(rating__gte=min_rating)
    if only_stock:
        qs = qs.filter(stock_total__gt=0)
    if only_sale:
        qs = qs.filter(price__lte=F("mrp") * 0.8)
    qs = qs.distinct()
    order = {
        "new": ("-created_at",), "price-asc": ("price",), "price-desc": ("-price",),
        "rating": ("-rating", "-reviews"), "featured": ("-featured", "-sold"),
        "discount": ("-sold",),
    }.get(sort, ("-featured", "-sold"))
    if sort == "discount":
        items = sorted(qs, key=lambda p: -p.discount_pct)
    else:
        items = qs.order_by(*order, "id")
    page = Paginator(items, PAGE_SIZE).get_page(g.get("page"))

    params = g.copy()
    params.pop("page", None)
    all_colors = {}
    for c in ProductColor.objects.order_by("id"):
        all_colors.setdefault(c.name, c)
    all_sizes = sorted({s for v in SIZES.values() for s in v}, key=int)
    price_ceil = -(-(Product.objects.order_by("-price").values_list("price", flat=True).first() or 1000) // 500) * 500
    active = len(types) + len(sizes) + len(colors) + bool(max_p) + bool(min_rating) + only_stock + only_sale + bool(not category and cat)

    ctx = {
        "page": page, "title": f"Results for “{q}”" if q else ("Sale — up to 30% off" if only_sale else TITLES.get(cat, "All Sneakers")),
        "cat": cat, "fixed_category": category, "q": q, "sort": sort, "sorts": SORTS, "types_all": TYPES,
        "sel_types": types, "sel_sizes": sizes, "sel_colors": colors, "max_p": max_p, "min_rating": min_rating,
        "only_stock": only_stock, "only_sale": only_sale, "all_colors": list(all_colors.values()),
        "all_sizes": all_sizes, "price_ceil": price_ceil, "active_filters": active, "categories": CATEGORIES,
        "qs": params.urlencode(), "count": page.paginator.count,
    }
    return render(request, "store/shop.html", ctx)


def product_detail(request, pk):
    product = get_object_or_404(products_qs(), pk=pk)
    related = list(products_qs().filter(category=product.category).exclude(pk=pk).order_by("-featured", "-sold")[:4])
    wished = request.user.is_authenticated and Wishlist.objects.filter(user=request.user, product=product).exists()
    return render(request, "store/product_detail.html", {
        "product": product, "related": related, "colors": product.color_list, "stocks": product.stock_list,
        "size_chart": SIZE_CHARTS[product.category], "wished": wished,
    })


# ------------------------------------------------------------------ cart

def cart_view(request):
    cart = Cart(request)
    lines = cart.lines()
    code = request.session.get(COUPON_KEY, "")
    t = totals(lines, code)
    if code and not t["coupon"]:
        request.session.pop(COUPON_KEY, None)
        if t["coupon_message"]:
            messages.warning(request, t["coupon_message"])
    return render(request, "store/cart.html", {"lines": lines, "t": t, "coupons": Coupon.objects.filter(active=True)})


@require_POST
def cart_add(request):
    try:
        pid, qty = int(request.POST.get("product")), max(1, int(request.POST.get("qty") or 1))
    except (TypeError, ValueError):
        return _cart_reply(request, False, "Invalid product")
    size, color = request.POST.get("size", ""), request.POST.get("color", "")
    product = Product.objects.prefetch_related("colors", "stocks", "photos").filter(pk=pid).first()
    if not product or not any(c.name == color for c in product.colors.all()):
        return _cart_reply(request, False, "This product is not available")
    if not size:
        return _cart_reply(request, False, "Please select a size")
    stock = next((s.qty for s in product.stocks.all() if s.size == size), 0)
    cart = Cart(request)
    in_cart = sum(i["qty"] for i in cart.items if i["pid"] == pid and i["size"] == size)
    if stock <= 0:
        return _cart_reply(request, False, f"UK {size} is out of stock")
    if in_cart + qty > stock:
        return _cart_reply(request, False, f"Only {stock} pair(s) available in UK {size}")
    cart.add(pid, size, color, qty)
    return _cart_reply(request, True, f"{product.name} (UK {size}) added to cart")


def _cart_reply(request, ok, message):
    if is_ajax(request):
        return JsonResponse({"ok": ok, "message": message, "count": len(Cart(request))}, status=200 if ok else 400)
    (messages.success if ok else messages.error)(request, message)
    return redirect(request.POST.get("next") or ("cart" if ok else request.META.get("HTTP_REFERER", "shop")))


@require_POST
def cart_update(request):
    cart = Cart(request)
    try:
        idx = int(request.POST.get("idx"))
    except (TypeError, ValueError):
        return redirect("cart")
    action = request.POST.get("action")
    if action == "remove":
        cart.remove(idx)
    elif 0 <= idx < len(cart.items):
        qty = cart.items[idx]["qty"] + (1 if action == "inc" else -1 if action == "dec" else 0)
        line = next((l for l in cart.lines() if l["idx"] == idx), None)
        if line and qty > line["stock"]:
            messages.error(request, f"Only {line['stock']} pair(s) available")
        else:
            cart.set_qty(idx, qty)
    return redirect("cart")


@require_POST
def cart_coupon(request):
    if request.POST.get("remove"):
        request.session.pop(COUPON_KEY, None)
        return redirect("cart")
    code = request.POST.get("code", "").strip().upper()
    lines = Cart(request).lines()
    t = totals(lines, code)
    if t["coupon"]:
        request.session[COUPON_KEY] = code
        messages.success(request, f"Coupon {code} applied")
    else:
        messages.error(request, t["coupon_message"] or "Invalid coupon code")
    return redirect("cart")


# ------------------------------------------------------------------ checkout

def _payment_label(post):
    method = post.get("method")
    if method == "cod":
        return "Cash on Delivery", None
    if method == "upi":
        upi = post.get("upi", "").strip()
        if not re.fullmatch(r"[\w.\-]{2,}@[a-zA-Z]{2,}", upi):
            return None, "Enter a valid UPI ID (like name@okhdfc)"
        return f"UPI ({upi})", None
    if method == "card":
        num = re.sub(r"\D", "", post.get("card", ""))
        if not 13 <= len(num) <= 19:
            return None, "Enter a valid card number"
        if not re.fullmatch(r"(0[1-9]|1[0-2])\s*/\s*\d{2}", post.get("expiry", "").strip()):
            return None, "Enter card expiry as MM/YY"
        if not re.fullmatch(r"\d{3,4}", post.get("cvv", "").strip()):
            return None, "Enter a valid CVV"
        return f"Card ending {num[-4:]}", None  # only the last 4 digits are ever stored
    return None, "Choose a payment method"


@login_required
def checkout(request):
    cart = Cart(request)
    lines = cart.lines()
    if not lines:
        messages.info(request, "Your cart is empty")
        return redirect("cart")
    code = request.session.get(COUPON_KEY, "")
    t = totals(lines, code)
    u = request.user
    initial = {"name": u.get_full_name(), "phone": u.phone, "line": u.address_line, "city": u.city,
               "state": u.state or "Madhya Pradesh", "pin": u.pin}
    payment_error = ""
    if request.method == "POST":
        form = AddressForm(request.POST)
        label, payment_error = _payment_label(request.POST)
        if any(l["problem"] for l in lines):
            messages.error(request, "Some items in your cart are no longer available in that quantity. Please update your cart.")
            return redirect("cart")
        if form.is_valid() and label:
            try:
                order = create_order(u, lines, form.cleaned_data, label, code)
            except OrderError as e:
                messages.error(request, str(e))
                return redirect("cart")
            cart.clear()
            return redirect("order_done", order_id=order.id)
    else:
        form = AddressForm(initial=initial)
    return render(request, "store/checkout.html", {"form": form, "lines": lines, "t": t, "payment_error": payment_error,
                                                   "method": request.POST.get("method", "cod")})


@login_required
def order_done(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items", "events"), pk=order_id)
    if order.user_id != request.user.id and not request.user.is_staff:
        return redirect("home")
    return render(request, "store/order_done.html", {"order": order})


# ------------------------------------------------------------------ auth / account

def _safe_next(request, default="home"):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    return nxt if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}) else reverse(default)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    error = ""
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get("email", "").strip(), password=request.POST.get("password", ""))
        if user:
            login(request, user)
            return redirect(_safe_next(request, "dash_overview" if user.is_staff else "home"))
        error = "Incorrect e-mail or password"
    return render(request, "store/login.html", {"error": error, "next": request.GET.get("next", "")})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="store.backends.EmailBackend")
        messages.success(request, f"Welcome to FootFlex, {user.display_name}!")
        return redirect(_safe_next(request))
    return render(request, "store/register.html", {"form": form, "next": request.GET.get("next", "")})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def account(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items", "events")
    return render(request, "store/account.html", {"orders": orders})


@login_required
@require_POST
def cancel_order(request, order_id):
    try:
        change_status(order_id, "Cancelled", customer=request.user)
        messages.success(request, f"Order {order_id} cancelled. Stock has been returned.")
    except OrderError as e:
        messages.error(request, str(e))
    return redirect("account")


@login_required
def wishlist(request):
    items = Wishlist.objects.filter(user=request.user).select_related("product").prefetch_related("product__colors", "product__stocks", "product__photos")
    return render(request, "store/wishlist.html", {"products": [w.product for w in items]})


@require_POST
def wishlist_toggle(request):
    if not request.user.is_authenticated:
        if is_ajax(request):
            return JsonResponse({"ok": False, "login": f"{reverse('login')}?next={request.POST.get('next', '/')}",
                                 "message": "Please log in to use your wishlist"}, status=401)
        return redirect(f"{reverse('login')}?next={request.POST.get('next', '/')}")
    product = get_object_or_404(Product, pk=request.POST.get("product"))
    obj, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        obj.delete()
    count = Wishlist.objects.filter(user=request.user).count()
    if is_ajax(request):
        return JsonResponse({"ok": True, "on": created, "count": count,
                             "message": "Added to wishlist" if created else "Removed from wishlist"})
    return redirect(request.POST.get("next") or "wishlist")


def track(request):
    order, error, searched = None, "", False
    if request.method == "POST":
        searched = True
        oid = request.POST.get("id", "").strip().upper()
        contact = request.POST.get("contact", "").strip().lower()
        o = Order.objects.prefetch_related("items", "events").filter(pk=oid).first()
        u = request.user
        allowed = o and ((u.is_authenticated and (u.is_staff or o.user_id == u.id))
                         or (contact and contact in (o.email.lower(), o.phone)))
        if allowed:
            order = o
        else:  # one generic message so order IDs can't be guessed
            error = "We could not find an order matching those details"
    return render(request, "store/track.html", {"order": order, "error": error, "searched": searched,
                                                "oid": request.POST.get("id", request.GET.get("id", ""))})


def page_not_found(request, exception=None):
    return render(request, "store/404.html", status=404)
