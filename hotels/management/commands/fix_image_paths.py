# hotels/management/commands/fix_image_paths.py
import os
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage

from hotels.models import Hotel, Room, HotelImage


class Command(BaseCommand):
    help = "Move legacy image paths to the new UploadToPath structure (hotel-first)."

    def handle(self, *args, **options):
        total = 0
        for hotel in Hotel.objects.all():
            self.stdout.write(f"Processing hotel: {hotel.name} (slug: {hotel.slug})")

            # ---------- Hotel cover ----------
            if hotel.image and hotel.image.name:
                new_name = f"hotels/{hotel.slug}/cover/{Path(hotel.image.name).name}"
                if self._move_if_needed(hotel.image, new_name):
                    hotel.image.name = new_name
                    hotel.save(update_fields=["image"])
                    total += 1

            # ---------- Gallery images ----------
            for hi in hotel.images.all():
                if hi.image and hi.image.name:
                    new_name = f"hotels/{hotel.slug}/gallery/{Path(hi.image.name).name}"
                    if self._move_if_needed(hi.image, new_name):
                        hi.image.name = new_name
                        hi.save(update_fields=["image"])
                        total += 1

            # ---------- Room images ----------
            for room in hotel.rooms.all():
                if room.image and room.image.name:
                    new_name = f"hotels/{hotel.slug}/rooms/{room.pk}_{Path(room.image.name).name}"
                    if self._move_if_needed(room.image, new_name):
                        room.image.name = new_name
                        room.save(update_fields=["image"])
                        total += 1

        self.stdout.write(
            self.style.SUCCESS(f"Finished – {total} image record(s) updated.")
        )

    def _move_if_needed(self, field, new_name):
        """
        Returns True if the DB field was changed.
        * Skips default placeholders (they have no real file)
        * Skips if the file already lives at new_name
        * Copies the file via storage (works on Windows & S3)
        * DOES NOT delete old file (you will do it manually)
        """
        old_name = field.name

        # 1. Skip defaults or non-existent files
        if "default" in old_name.lower() or not default_storage.exists(old_name):
            return False

        # 2. Already in the correct place
        if old_name == new_name:
            return False

        # 3. Copy old → new
        try:
            with default_storage.open(old_name, "rb") as src:
                default_storage.save(new_name, src)
            self.stdout.write(f"   Copied: {old_name} → {new_name}")
            return True
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"   Failed {old_name} → {new_name}: {e}")
            )
            return False