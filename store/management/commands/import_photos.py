"""Attach shoe photos from a folder to products, matching by file name.

  python manage.py import_photos C:\\path\\to\\photos
  python manage.py import_photos C:\\path\\to\\photos --replace

File naming (product name -> lower case, spaces become "-"):
  volt-runner-x.jpg      main photo of "Volt Runner X"
  volt-runner-x-2.jpg    2nd photo (another angle)   (-3, -4 ... for more)
"""
import re
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from store.models import Product, ProductPhoto

EXT = {".jpg", ".jpeg", ".png", ".webp"}


class Command(BaseCommand):
    help = "Import product photos from a folder (file name = product name, add -2, -3 for more angles)."

    def add_arguments(self, parser):
        parser.add_argument("folder")
        parser.add_argument("--replace", action="store_true", help="remove existing photos of matched products first")

    def handle(self, *args, **opts):
        folder = Path(opts["folder"])
        if not folder.is_dir():
            raise CommandError(f"Folder not found: {folder}")
        by_slug = {slugify(p.name): p for p in Product.objects.all()}
        files = sorted(f for f in folder.iterdir() if f.suffix.lower() in EXT)
        if not files:
            raise CommandError("No .jpg / .png / .webp files in that folder")

        groups = {}  # product -> list[(order, path)]
        unmatched = []
        for f in files:
            stem = slugify(f.stem)
            prod, order = by_slug.get(stem), 1
            if not prod:
                m = re.fullmatch(r"(.+?)-(\d+)", stem)
                if m and m.group(1) in by_slug:
                    prod, order = by_slug[m.group(1)], int(m.group(2))
            if prod:
                groups.setdefault(prod, []).append((order, f))
            else:
                unmatched.append(f.name)

        done = 0
        for prod, items in groups.items():
            items.sort(key=lambda x: (x[0], x[1].name))
            if opts["replace"]:
                prod.photos.all().delete()
                prod.image = ""
            for i, (_, path) in enumerate(items):
                with path.open("rb") as fh:
                    if i == 0 and not prod.image:
                        prod.image.save(path.name, File(fh), save=True)
                    else:
                        ph = ProductPhoto(product=prod, sort=i)
                        ph.image.save(path.name, File(fh), save=True)
                done += 1
            self.stdout.write(f"  {prod.name}: {len(items)} photo(s)")
        self.stdout.write(self.style.SUCCESS(f"Imported {done} photo(s) for {len(groups)} product(s)."))
        if unmatched:
            self.stdout.write(self.style.WARNING("No product matched for: " + ", ".join(unmatched)))
            self.stdout.write("Product names: " + ", ".join(sorted(by_slug)))
