# FootFlex — Django + MySQL

Shoes e-commerce website (Men / Women / Kids, cart, coupons, checkout, orders, wishlist, order tracking, admin dashboard).
Pehle React + Node tha, ab poora **Django + MySQL**. Theme: dark black + electric blue (tumhare reference design jaisa). `static/css/footflex.css` ke `:root` me `--paper`, `--ink`, `--accent` se colours badal sakte ho. Prices ₹ me.

## Setup (Windows PowerShell)
```powershell
cd footflex
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # .env kholke DB_PASSWORD (MySQL root password) daalo
python manage.py create_database   # MySQL me "footflex" database banata hai
python manage.py migrate
python manage.py seed_demo         # 24 shoes, coupons, demo users, demo orders
python manage.py attach_demo_photos # realistic product photos for the demo shoe catalogue
python manage.py runserver
```
Open: http://127.0.0.1:8000

(Agar MySQL abhi nahi hai aur sirf test karna hai: `.env` me `DB_ENGINE=sqlite` kar do.)

## Demo login
| Role | Email | Password |
|---|---|---|
| Customer | demo@footflex.in | demo123 |
| Admin | admin@footflex.in | admin123 |

Coupons: `FOOTFLEX10`, `WELCOME200`, `FLEXFREE`. Test card `4242 4242 4242 4242` (payment simulated).
Track demo order: `FF-25C7D2` + `demo@footflex.in`.

## Pages
- Store: `/`, `/men/`, `/women/`, `/kids/`, `/shop/` (search, filters, sort), `/product/<id>/`, `/cart/`, `/checkout/`, `/wishlist/`, `/account/`, `/track/`
- Admin dashboard: `/dashboard/` (overview, products add/edit/delete, inventory per size, orders status, customers)
- Django admin: `/django-admin/`

## Shoe photos (Zappos jaisa)
Demo catalogue ke liye realistic studio-style shoe photos `media/products/` me bundled hain. `attach_demo_photos` command unhe demo products se jodta hai. Missing photo par ab cartoon/vector shoe ki jagah clean placeholder dikhega. Apne actual stock ke liye supplier ya khud ki product photos upload karein. Asli photos lagane ke 2 tareeke:

**A) Ek saath saari photos (sabse fast).** Ek folder banao (jaise `C:\Users\DC\Desktop\shoe-photos`) aur photos ka naam **product name** rakho:
```
volt-runner-x.jpg        <- main photo
volt-runner-x-2.jpg      <- doosra angle (hover par dikhta hai)
volt-runner-x-3.jpg      <- teesra angle ...
neon-pulse.png
hyper-court-pro.webp
```
Naam = product ka naam lowercase me, spaces ki jagah `-`. Phir:
```powershell
python manage.py import_photos C:\Users\DC\Desktop\shoe-photos
```
(galat naam wali files ki list aur sahi product names screen par aa jate hain. `--replace` lagane se purani photos hat jati hain.)

**B) Dashboard se ek-ek product:** `/dashboard/` → Products → Edit → *Main photo* aur *More photos* (ek saath kai select kar sakte ho, total 8 tak).

**Kaisi photo best lagti hai:** white ya transparent background, shoe ka side view, kam se kam 1000 px, JPG/PNG/WebP, 3 MB tak. Site photo ko card me bina cut kiye fit karti hai.
- Shop card: portrait box, 2nd photo hover par, `+N` badge.
- Product page: left me thumbnails, click par badi photo badalti hai.

> Zappos ya kisi aur site ki photos copy mat karna (copyright). Apne supplier / brand ki photos ya khud ki khinchi photos use karo.

## Structure
```
footflex/   settings, urls          store/   models, views, cart, services (stock transaction), dashboard
templates/  base + store + dashboard    static/css/footflex.css, static/js/app.js
```
Stock order ke time database transaction me kam hota hai; cancel karne par wapas add ho jata hai.
