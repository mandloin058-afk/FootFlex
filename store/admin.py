from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Coupon, Order, OrderEvent, OrderItem, Product, ProductColor, ProductPhoto, ProductStock, User, Wishlist


class ColorInline(admin.TabularInline):
    model = ProductColor
    extra = 1


class PhotoInline(admin.TabularInline):
    model = ProductPhoto
    extra = 1


class StockInline(admin.TabularInline):
    model = ProductStock
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "type", "price", "mrp", "featured", "is_new")
    list_filter = ("category", "type", "featured", "is_new")
    search_fields = ("name",)
    inlines = [PhotoInline, ColorInline, StockInline]


class ItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class EventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "total", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "email", "name", "phone")
    inlines = [ItemInline, EventInline]


admin.site.register(User, UserAdmin)
admin.site.register(Coupon)
admin.site.register(Wishlist)
