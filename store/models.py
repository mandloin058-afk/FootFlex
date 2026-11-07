from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

CATEGORIES = [("men", "Men"), ("women", "Women"), ("kids", "Kids")]
TYPES = ["Running", "Lifestyle", "Basketball", "Training", "Casual", "Sports"]
PATTERNS = [("swoosh", "Swoosh"), ("stripe", "Stripes"), ("dots", "Dots")]
SIZES = {
    "men": ["6", "7", "8", "9", "10", "11"],
    "women": ["3", "4", "5", "6", "7", "8"],
    "kids": ["1", "2", "3", "4", "5"],
}
STATUSES = ["Placed", "Confirmed", "Packed", "Shipped", "Out for Delivery", "Delivered"]

# Ready-made colourways (name -> shoe body colour, accent colour).
COLORWAYS = {
    "Neon Blue": ("#0F2A5E", "#27B6FF"),
    "Black": ("#1D232C", "#1E90FF"),
    "White": ("#F2F2EF", "#0A7DFF"),
    "Grey": ("#AEB4BB", "#0A7DFF"),
    "Navy": ("#16254A", "#4DB2FF"),
    "Royal Blue": ("#1F4FD8", "#FFFFFF"),
    "Red": ("#D3202F", "#FFFFFF"),
    "Volt": ("#C5E83A", "#111111"),
    "Orange": ("#FF7A1A", "#111111"),
    "Pink": ("#F4A6BE", "#FFFFFF"),
}


class User(AbstractUser):
    """Customer or admin (admin = is_staff). The e-mail is also stored in `username`."""
    phone = models.CharField(max_length=15, blank=True)
    address_line = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=60, blank=True, default="Madhya Pradesh")
    pin = models.CharField(max_length=6, blank=True)

    def __str__(self):
        return self.email or self.username

    @property
    def display_name(self):
        return self.get_full_name() or self.username.split("@")[0]


class Product(models.Model):
    name = models.CharField(max_length=120)
    brand = models.CharField(max_length=60, default="FootFlex")
    category = models.CharField(max_length=10, choices=CATEGORIES)
    type = models.CharField(max_length=40, choices=[(t, t) for t in TYPES])
    price = models.PositiveIntegerField(help_text="Selling price in ₹")
    mrp = models.PositiveIntegerField(help_text="MRP in ₹ (must be ≥ price)")
    pattern = models.CharField(max_length=20, choices=PATTERNS, default="swoosh")
    description = models.TextField(blank=True)
    specs = models.TextField(blank=True, help_text="One per line, like  Upper: Engineered mesh")
    image = models.ImageField(upload_to="products/", blank=True, help_text="Optional real photo (PNG/JPG/WebP). If empty, the vector sneaker art is shown.")
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=Decimal("4.5"))
    reviews = models.PositiveIntegerField(default=0)
    featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    sold = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.name

    # ---- helpers used by templates ----
    @property
    def discount_pct(self):
        return round((1 - self.price / self.mrp) * 100) if self.mrp > self.price else 0

    @property
    def stock_list(self):
        rows = list(self.stocks.all())  # uses prefetch cache when available
        return sorted(rows, key=lambda s: int(s.size))

    @property
    def total_stock(self):
        return sum(s.qty for s in self.stocks.all())

    @property
    def color_list(self):
        return list(self.colors.all())

    @property
    def first_color(self):
        cs = self.color_list
        return cs[0] if cs else None

    @property
    def photo_list(self):
        """URLs of every real photo: the main one first, then the extra angles."""
        urls = [self.image.url] if self.image else []
        urls += [ph.image.url for ph in self.photos.all() if ph.image]
        return urls

    @property
    def extra_count(self):
        return max(len(self.photo_list) - 1, 0)

    @property
    def spec_pairs(self):
        out = []
        for line in self.specs.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out.append((k.strip(), v.strip()))
        return out


class ProductPhoto(models.Model):
    """Extra photo (other angle) of a product. The main photo is Product.image."""
    product = models.ForeignKey(Product, related_name="photos", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/")
    sort = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]

    def __str__(self):
        return f"{self.product.name} photo #{self.pk}"


class ProductColor(models.Model):
    product = models.ForeignKey(Product, related_name="colors", on_delete=models.CASCADE)
    name = models.CharField(max_length=40)
    body = models.CharField(max_length=9)
    accent = models.CharField(max_length=9)

    class Meta:
        ordering = ["id"]
        unique_together = [("product", "name")]

    def __str__(self):
        return f"{self.product.name} – {self.name}"


class ProductStock(models.Model):
    product = models.ForeignKey(Product, related_name="stocks", on_delete=models.CASCADE)
    size = models.CharField(max_length=4)
    qty = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("product", "size")]

    def __str__(self):
        return f"{self.product.name} UK{self.size}: {self.qty}"


class Coupon(models.Model):
    TYPE_CHOICES = [("percent", "Percent off"), ("flat", "Flat ₹ off"), ("ship", "Free shipping")]
    code = models.CharField(max_length=30, primary_key=True)
    label = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    value = models.PositiveIntegerField(default=0)
    max_discount = models.PositiveIntegerField(null=True, blank=True)
    min_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    def evaluate(self, subtotal):
        """Returns (ok, discount, free_ship, message)."""
        if not self.active:
            return False, 0, False, "Invalid coupon code"
        if subtotal < self.min_order:
            return False, 0, False, f"Add items worth ₹{self.min_order:,} or more to use {self.code}"
        if self.type == "percent":
            d = round(subtotal * self.value / 100)
            if self.max_discount:
                d = min(d, self.max_discount)
            return True, d, False, ""
        if self.type == "flat":
            return True, min(self.value, subtotal), False, ""
        return True, 0, True, ""


class Order(models.Model):
    id = models.CharField(max_length=16, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    email = models.EmailField()
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line = models.CharField(max_length=255)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=60)
    pin = models.CharField(max_length=6)
    payment = models.CharField(max_length=120)
    subtotal = models.PositiveIntegerField()
    discount = models.PositiveIntegerField(default=0)
    coupon = models.CharField(max_length=30, blank=True)
    shipping = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField()
    status = models.CharField(max_length=24, default="Placed")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.id

    @property
    def step_index(self):
        return STATUSES.index(self.status) if self.status in STATUSES else -1

    @property
    def can_cancel(self):
        return self.status in ("Placed", "Confirmed")


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    price = models.PositiveIntegerField()
    size = models.CharField(max_length=4)
    qty = models.PositiveIntegerField()
    color = models.CharField(max_length=40)
    body = models.CharField(max_length=9)
    accent = models.CharField(max_length=9)

    @property
    def line_total(self):
        return self.price * self.qty


class OrderEvent(models.Model):
    order = models.ForeignKey(Order, related_name="events", on_delete=models.CASCADE)
    status = models.CharField(max_length=24)
    at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["at", "id"]


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "product")]
        ordering = ["-created_at"]
