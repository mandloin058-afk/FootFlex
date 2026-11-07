"""Order placing / status changes. Stock is changed inside DB transactions with row locks."""
import secrets

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .cart import totals
from .models import STATUSES, Coupon, Order, OrderEvent, OrderItem, Product, ProductStock, User


class OrderError(Exception):
    pass


def _new_id():
    return "FF-" + secrets.token_hex(3).upper()


@transaction.atomic
def create_order(user, lines, address, payment, coupon_code=""):
    if not lines:
        raise OrderError("Your cart is empty")

    # Lock stock rows (ordered by id to avoid deadlocks) and decrement atomically.
    merged = {}
    for l in lines:
        key = (l["product"].id, l["size"])
        merged[key] = merged.get(key, 0) + l["qty"]
    for (pid, size), qty in sorted(merged.items()):
        row = ProductStock.objects.select_for_update().filter(product_id=pid, size=size).first()
        name = Product.objects.get(pk=pid).name
        if not row or row.qty < qty:
            left = row.qty if row else 0
            raise OrderError(f"Only {left} pair(s) of {name} (UK {size}) left. Please update your cart." if left
                             else f"{name} (UK {size}) is out of stock. Please update your cart.")
        row.qty -= qty
        row.save(update_fields=["qty"])

    t = totals(lines, coupon_code)
    order_id = _new_id()
    while Order.objects.filter(pk=order_id).exists():
        order_id = _new_id()
    now = timezone.now()
    order = Order.objects.create(
        id=order_id, user=user, email=user.email, name=address["name"], phone=address["phone"],
        address_line=address["line"], city=address["city"], state=address["state"], pin=address["pin"],
        payment=payment, subtotal=t["subtotal"], discount=t["discount"],
        coupon=t["coupon"].code if t["coupon"] else "", shipping=t["shipping"], total=t["total"],
        status="Placed", created_at=now,
    )
    OrderItem.objects.bulk_create([
        OrderItem(order=order, product=l["product"], name=l["product"].name, price=l["price"], size=l["size"],
                  qty=l["qty"], color=l["color"].name, body=l["color"].body, accent=l["color"].accent)
        for l in lines
    ])
    OrderEvent.objects.create(order=order, status="Placed", at=now)
    for l in lines:
        Product.objects.filter(pk=l["product"].pk).update(sold=F("sold") + l["qty"])
    User.objects.filter(pk=user.pk).update(
        address_line=address["line"], city=address["city"], state=address["state"], pin=address["pin"],
        phone=address["phone"],
    )
    return order


@transaction.atomic
def change_status(order_id, new_status, customer=None):
    """Statuses only move forward; 'Cancelled' is possible until delivery and returns stock."""
    order = Order.objects.select_for_update().filter(pk=order_id).first()
    if not order or (customer is not None and order.user_id != customer.id):
        raise OrderError("Order not found")
    if order.status in ("Cancelled", "Delivered"):
        raise OrderError(f"This order is already {order.status.lower()}")
    if new_status not in STATUSES + ["Cancelled"]:
        raise OrderError("Invalid status")
    if customer is not None and not (new_status == "Cancelled" and order.can_cancel):
        raise OrderError("This order can no longer be cancelled")
    if new_status != "Cancelled" and STATUSES.index(new_status) <= STATUSES.index(order.status):
        raise OrderError("Status can only move forward")

    if new_status == "Cancelled":
        for it in order.items.all():
            if it.product_id:
                ProductStock.objects.filter(product_id=it.product_id, size=it.size).update(qty=F("qty") + it.qty)
                Product.objects.filter(pk=it.product_id, sold__gte=it.qty).update(sold=F("sold") - it.qty)
    order.status = new_status
    order.save(update_fields=["status"])
    OrderEvent.objects.create(order=order, status=new_status)
    return order
