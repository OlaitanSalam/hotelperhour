from django.core.management.base import BaseCommand
from django.conf import settings
from hotels.models import Hotel, Room, HotelImage
from PIL import Image, ImageOps
import os

class Command(BaseCommand):
    help = "Convert all existing hotel and room images to WebP format with compression"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Starting image conversion..."))

        def convert_to_webp(img_path):
            try:
                if not os.path.exists(img_path):
                    return

                if img_path.lower().endswith(".webp"):
                    return

                img = Image.open(img_path)
                img = ImageOps.exif_transpose(img)
                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

                webp_path = os.path.splitext(img_path)[0] + ".webp"
                img.save(webp_path, "WEBP", quality=80, method=6)

                if os.path.exists(webp_path):
                    os.remove(img_path)

                self.stdout.write(f"✅ Converted: {os.path.basename(img_path)} → WEBP")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Failed for {img_path}: {e}"))

        # Process hotel images
        for hotel in Hotel.objects.exclude(image="").exclude(image__icontains="default"):
            try:
                convert_to_webp(hotel.image.path)
            except Exception as e:
                self.stdout.write(f"Hotel error ({hotel.name}): {e}")

        # Process room images
        for room in Room.objects.exclude(image="").exclude(image__icontains="default"):
            try:
                convert_to_webp(room.image.path)
            except Exception as e:
                self.stdout.write(f"Room error ({room.room_type}): {e}")

        # Process gallery images
        for img in HotelImage.objects.exclude(image="").exclude(image__icontains="default"):
            try:
                convert_to_webp(img.image.path)
            except Exception as e:
                self.stdout.write(f"HotelImage error ({img.hotel.name}): {e}")

        self.stdout.write(self.style.SUCCESS("✅ Done! All possible images processed."))
