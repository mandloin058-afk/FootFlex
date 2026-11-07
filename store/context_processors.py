from django.conf import settings

from .cart import Cart
from .models import STATUSES, Wishlist


def shop(request):
    wished = set()
    if request.user.is_authenticated:
        wished = set(Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True))
    return {
        "cart_count": len(Cart(request)),
        "wished_ids": wished,
        "wish_count": len(wished),
        "FREE_SHIP_ABOVE": settings.FREE_SHIP_ABOVE,
        "SHIPPING_FEE": settings.SHIPPING_FEE,
        "statuses": STATUSES,
    }
