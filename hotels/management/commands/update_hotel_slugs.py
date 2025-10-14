from django.core.management.base import BaseCommand
from hotels.models import Hotel  # Replace with your import

class Command(BaseCommand):
    help = 'Update slugs for all existing hotels based on public name'

    def handle(self, *args, **kwargs):
        hotels = Hotel.objects.all()
        for hotel in hotels:
            old_slug = hotel.slug
            # Force regenerate slug
            hotel.slug = None
            hotel.save()  # This triggers new slug and redirect creation
            self.stdout.write(self.style.SUCCESS(f"Updated {hotel.get_public_name()}: {old_slug} -> {hotel.slug}"))