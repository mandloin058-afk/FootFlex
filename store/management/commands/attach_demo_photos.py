"""Attach the bundled realistic demo shoe photos to matching products.

Run after migrations and after demo products exist:
    python manage.py attach_demo_photos
"""
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from store.models import Product


class Command(BaseCommand):
    help = "Attach bundled realistic product photos to demo products without overwriting existing photos."

    def handle(self, *args, **options):
        photo_dir = Path(__file__).resolve().parents[3] / "media" / "products"
        attached = 0
        missing = []
        for product in Product.objects.all():
            filename = f"{slugify(product.name)}.jpg"
            photo_path = photo_dir / filename
            if not photo_path.is_file():
                missing.append(product.name)
                continue
            if product.image:
                continue
            product.image.name = f"products/{filename}"
            product.save(update_fields=["image"])
            attached += 1
            self.stdout.write(f"  Added photo: {product.name}")
        self.stdout.write(self.style.SUCCESS(f"Attached {attached} product photo(s)."))
        if missing:
            self.stdout.write(self.style.WARNING("No bundled photo for: " + ", ".join(missing)))
