"""Staff-only admin dashboard (products, stock, orders, customers)."""
from datetime import timedelta

from django import forms as dj_forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ProductForm
from .models import COLORWAYS, SIZES, STATUSES, Order, Product, ProductColor, ProductPhoto, ProductStock
from .services import OrderError, change_status

User = get_user_model()
staff_required = user_passes_test(lambda u: u.is_active and u.is_staff, login_url="login")
LOW = 5


@staff_required
def overview(request):
    live = Order.objects.exclude(status="Cancelled")
    agg = live.aggregate(revenue=Sum("total"), n=Count("id"))
    today = timezone.localdate()
    days = []
    for k in range(6, -1, -1):
        d = today - timedelta(days=k)
        s = live.filter(created_at__date=d).aggregate(v=Sum("total"))["v"] or 0
        days.append({"label": d.strftime("%a"), "value": s})
    top = max([d["value"] for d in days] + [1])
    for d in days:
        d["pct"] = round(d["value"] / top * 100)
    stock = ProductStock.objects.values("product_id").annotate(t=Sum("qty"))
    ctx = {
        "revenue": agg["revenue"] or 0, "orders_n": agg["n"], "products_n": Product.objects.count(),
        "customers_n": User.objects.filter(is_staff=False).count(),
        "out_n": sum(1 for s in stock if s["t"] == 0),
        "low_sizes": ProductStock.objects.filter(qty__gt=0, qty__lte=LOW).count(),
        "pending": Order.objects.filter(status__in=["Placed", "Confirmed"]).count(),
        "days": days,
        "recent": Order.objects.prefetch_related("items")[:6],
        "top": Product.objects.prefetch_related("colors", "stocks", "photos").order_by("-sold")[:5],
        "by_status": [(s, Order.objects.filter(status=s).count()) for s in STATUSES + ["Cancelled"]],
        "section": "overview",
    }
    return render(request, "dashboard/overview.html", ctx)


@staff_required
def products(request):
    q = request.GET.get("q", "").strip()
    qs = Product.objects.prefetch_related("colors", "stocks", "photos")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(type__icontains=q) | Q(category__icontains=q))
    return render(request, "dashboard/products.html", {"products": qs.order_by("category", "name"), "q": q, "section": "products"})


def _stock_groups(post=None, product=None):
    """Stock inputs for every category; only the chosen category's group is saved."""
    current = {s.size: s.qty for s in product.stocks.all()} if product else {}
    groups = []
    for cat, sizes in SIZES.items():
        rows = []
        for s in sizes:
            name = f"stock_{cat}_{s}"
            if post is not None and name in post:
                val = post.get(name)
            else:
                val = current.get(s, 10) if (product is None or product.category == cat) else 10
            rows.append({"name": name, "size": s, "value": val})
        groups.append({"cat": cat, "rows": rows})
    return groups


@staff_required
def product_edit(request, pk=None):
    product = get_object_or_404(Product.objects.prefetch_related("colors", "stocks", "photos"), pk=pk) if pk else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=product,
                       initial={"colorways": [c.name for c in product.colors.all()]} if product else {"pattern": "swoosh"})
    errors = []
    photo_errors, new_photos = [], []
    if request.method == "POST":
        existing = product.photos.count() if product else 0
        gone = {int(x) for x in request.POST.getlist("delete_photo") if x.isdigit()}
        for f in request.FILES.getlist("photos"):
            try:
                if f.size > 3 * 1024 * 1024:
                    raise dj_forms.ValidationError(f"{f.name} is larger than 3 MB")
                new_photos.append(dj_forms.ImageField().clean(f))
            except dj_forms.ValidationError as e:
                photo_errors.append(e.messages[0] if hasattr(e, "messages") else str(e))
        if existing - len(gone) + len(new_photos) > 7:
            photo_errors.append("You can keep at most 7 extra photos (8 with the main one)")
    if request.method == "POST" and form.is_valid() and not photo_errors:
        cat = form.cleaned_data["category"]
        stock = {}
        for s in SIZES[cat]:
            raw = request.POST.get(f"stock_{cat}_{s}", "0").strip() or "0"
            if not raw.isdigit() or int(raw) > 100000:
                errors.append(f"Stock for UK {s} must be a whole number ≥ 0")
            else:
                stock[s] = int(raw)
        if not errors:
            p = form.save(commit=False)
            p.mrp = form.cleaned_data["mrp"]
            if not product:
                p.rating, p.reviews = 4.5, 0
            p.save()
            if product:
                p.photos.filter(pk__in=gone).delete()
            start = (p.photos.order_by("-sort").values_list("sort", flat=True).first() or 0) + 1
            for i, f in enumerate(new_photos):
                ProductPhoto.objects.create(product=p, image=f, sort=start + i)
            p.colors.all().delete()
            ProductColor.objects.bulk_create([ProductColor(product=p, name=n, body=COLORWAYS[n][0], accent=COLORWAYS[n][1])
                                              for n in form.cleaned_data["colorways"]])
            p.stocks.exclude(size__in=stock.keys()).delete()
            for s, qty in stock.items():
                ProductStock.objects.update_or_create(product=p, size=s, defaults={"qty": qty})
            messages.success(request, f"{p.name} saved")
            return redirect("dash_products")
    post = request.POST if request.method == "POST" else None
    return render(request, "dashboard/product_form.html", {
        "form": form, "product": product, "stock_groups": _stock_groups(post, product),
        "stock_errors": errors, "photo_errors": photo_errors, "section": "products",
    })


@staff_required
@require_POST
def product_delete(request, pk):
    p = get_object_or_404(Product, pk=pk)
    name = p.name
    p.delete()
    messages.success(request, f"{name} deleted")
    return redirect("dash_products")


@staff_required
def inventory(request):
    if request.method == "POST":
        p = get_object_or_404(Product, pk=request.POST.get("product"))
        for s in SIZES[p.category]:
            raw = request.POST.get(f"qty_{s}", "")
            if raw.isdigit() and int(raw) <= 100000:
                ProductStock.objects.update_or_create(product=p, size=s, defaults={"qty": int(raw)})
        messages.success(request, f"Stock updated for {p.name}")
        return redirect(request.get_full_path())
    flt = request.GET.get("show", "all")
    rows = []
    for p in Product.objects.prefetch_related("stocks").order_by("category", "name"):
        sizes = {s.size: s.qty for s in p.stocks.all()}
        total = sum(sizes.values())
        if flt == "low" and not any(0 < v <= LOW for v in sizes.values()):
            continue
        if flt == "out" and total != 0:
            continue
        rows.append({"p": p, "sizes": [(s, sizes.get(s, 0)) for s in SIZES[p.category]], "total": total})
    return render(request, "dashboard/inventory.html", {"rows": rows, "show": flt, "low": LOW, "section": "inventory"})


@staff_required
def orders(request):
    if request.method == "POST":
        try:
            change_status(request.POST.get("order"), request.POST.get("status", ""))
            messages.success(request, f"Order {request.POST.get('order')} updated")
        except OrderError as e:
            messages.error(request, str(e))
        return redirect(request.get_full_path())
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    qs = Order.objects.prefetch_related("items")
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(id__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    rows = []
    for o in qs[:200]:
        nxt = STATUSES[o.step_index + 1:] if o.step_index >= 0 and o.status != "Cancelled" else []
        rows.append({"o": o, "next": nxt, "closed": o.status in ("Delivered", "Cancelled")})
    return render(request, "dashboard/orders.html", {"rows": rows, "status": status, "q": q, "statuses": STATUSES + ["Cancelled"], "section": "orders"})


@staff_required
def customers(request):
    users = (User.objects.filter(is_staff=False)
             .annotate(n=Count("orders", filter=~Q(orders__status="Cancelled")),
                       spend=Sum("orders__total", filter=~Q(orders__status="Cancelled")))
             .order_by("-spend", "id"))
    return render(request, "dashboard/customers.html", {"customers": users, "section": "customers"})
