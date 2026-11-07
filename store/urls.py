from django.urls import path

from . import views, dashboard

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("men/", views.shop, {"category": "men"}, name="men"),
    path("women/", views.shop, {"category": "women"}, name="women"),
    path("kids/", views.shop, {"category": "kids"}, name="kids"),
    path("product/<int:pk>/", views.product_detail, name="product"),

    path("cart/", views.cart_view, name="cart"),
    path("cart/add/", views.cart_add, name="cart_add"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/coupon/", views.cart_coupon, name="cart_coupon"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<str:order_id>/done/", views.order_done, name="order_done"),

    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("account/", views.account, name="account"),
    path("account/cancel/<str:order_id>/", views.cancel_order, name="cancel_order"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/toggle/", views.wishlist_toggle, name="wishlist_toggle"),
    path("track/", views.track, name="track"),

    # Admin dashboard (staff only)
    path("dashboard/", dashboard.overview, name="dash_overview"),
    path("dashboard/products/", dashboard.products, name="dash_products"),
    path("dashboard/products/new/", dashboard.product_edit, name="dash_product_new"),
    path("dashboard/products/<int:pk>/edit/", dashboard.product_edit, name="dash_product_edit"),
    path("dashboard/products/<int:pk>/delete/", dashboard.product_delete, name="dash_product_delete"),
    path("dashboard/inventory/", dashboard.inventory, name="dash_inventory"),
    path("dashboard/orders/", dashboard.orders, name="dash_orders"),
    path("dashboard/customers/", dashboard.customers, name="dash_customers"),
]
