import csv
import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings

from myapp.models import City, Place, Category, PlaceImage, PlaceCategory


class Command(BaseCommand):
    help = 'Import data from CSV file into City, Place, Category, PlaceImage, and PlaceCategory models.'

    # Optional: If you want to allow dynamic CSV file path
    # def add_arguments(self, parser):
    #     parser.add_argument('csv_file_path', type=str, help='Path to the CSV file')

    def _safe_int(self, value):
        """Convert value to int safely"""
        try:
            return int(value) if value else None
        except (ValueError, TypeError):
            return None

    def _safe_float(self, value):
        """Convert value to float safely"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0

    def handle(self, *args, **options):
        # Hardcoded path for the CSV file
        csv_file = os.path.join(settings.BASE_DIR, r"C:\Users\ginta\OneDrive - Kaunas University of Technology\4sem\bigdata\projektas\smthfordjango\cleaned_TourismObjects.csv")
        # images_dir is not directly used for import, only for checking existence of pre-downloaded images
        # images_dir = os.path.join(settings.BASE_DIR, 'media', 'images') # No longer needed here

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f"File not found: {csv_file}"))
            return

        # Clear existing data if needed before a fresh import
        self.stdout.write(self.style.WARNING("Clearing existing data before import..."))
        PlaceCategory.objects.all().delete() # Delete junction table first
        PlaceImage.objects.all().delete()
        Place.objects.all().delete()
        Category.objects.all().delete()
        City.objects.all().delete()


        # Track counters for summary
        cities_created = 0
        places_created = 0
        categories_created = 0
        images_created = 0

        # Dictionary to store created cities and categories to avoid redundant DB queries
        city_dict = {}
        category_dict = {}

        with open(csv_file, encoding='utf-8') as f:
            # Read all lines to get total_rows count, then reset file pointer
            reader_for_count = csv.reader(open(csv_file, encoding='utf-8'))
            total_rows = sum(1 for row in reader_for_count) - 1 # Subtract 1 for header

            f.seek(0) # Reset file pointer to the beginning
            reader = csv.DictReader(f, delimiter=';')
            next(reader)  # Skip header row if DictReader doesn't handle it automatically (it usually does with fieldnames)

            self.stdout.write(f"Starting import of {total_rows} rows...")

            # Process each row
            for i, row in enumerate(reader):
                # Check if we have the city column
                city_name = row.get('City', '').strip() # .strip() to remove leading/trailing whitespace
                if not city_name:
                    self.stdout.write(self.style.WARNING(f"Row {i+2}: Missing city name, skipping"))
                    continue

                # Create or get city
                city, created = City.objects.get_or_create(name=city_name)
                if created:
                    cities_created += 1
                city_dict[city_name] = city # Cache the city object

                # Create place
                place_name = row.get('Title', '').strip()
                if not place_name:
                    self.stdout.write(self.style.WARNING(f"Row {i+2}: Missing place name, skipping"))
                    continue

                # Get or create place
                place, created = Place.objects.get_or_create(
                    name=place_name,
                    city=city,
                    defaults={
                        'wikipedia_link': row.get('Link', ''),
                        'title': place_name,
                        'page_views': self._safe_int(row.get('Page Views')),
                        'number_of_categories': self._safe_int(row.get('Number of Categories')),
                        'number_of_languages': self._safe_int(row.get('Number of Languages')),
                        'number_of_references': self._safe_int(row.get('Number of References')),
                        'number_of_sections': self._safe_int(row.get('Number of Sections')),
                        'number_of_links': self._safe_int(row.get('Number of Links')),
                        'number_of_images': self._safe_int(row.get('Number of Images')),
                        'number_of_external_links': self._safe_int(row.get('Number of External Links')),
                        'page_length': self._safe_int(row.get('Page Length')),
                        'linkshere': self._safe_int(row.get('linkshere')),
                        'total_links': self._safe_int(row.get('total_links')),
                        'revision_count': self._safe_int(row.get('revision_count')),
                        'language_links': self._safe_int(row.get('language_links')),
                        'category_count': self._safe_int(row.get('category_count')),
                        'relevance_score': self._safe_float(row.get('pagerank_score') or row.get('relevance_score') or 0),
                    }
                )

                if created:
                    places_created += 1

                # Process image if available (only creating the PlaceImage record with image_url)
                image_url = row.get('Image link', '').strip()
                if image_url:
                    # Check if image already exists for this place/url to avoid duplicates if re-running
                    if not PlaceImage.objects.filter(place=place, image_url=image_url).exists():
                        PlaceImage.objects.create(
                            place=place,
                            image_url=image_url,
                            is_primary=True # First image is primary
                        )
                        images_created += 1


                # Process categories
                if 'categories' in row and row['categories']:
                    try:
                        categories = row['categories'].split(',')
                        for category_name in categories:
                            category_name = category_name.strip()
                            if not category_name:
                                continue

                            # Get or create category
                            category, created_cat = Category.objects.get_or_create(name=category_name)
                            if created_cat:
                                categories_created += 1
                            category_dict[category_name] = category # Cache the category object

                            # Create relationship if it doesn't exist
                            if not PlaceCategory.objects.filter(place=place, category=category).exists():
                                PlaceCategory.objects.create(place=place, category=category)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Error processing categories for {place_name}: {e}"))

                # Print progress every 10 rows
                if (i + 1) % 10 == 0:
                    self.stdout.write(f"Processed {i+1}/{total_rows} rows...")

        # Print summary
        self.stdout.write(self.style.SUCCESS(f"""
        Import completed successfully!
        Cities created: {cities_created}
        Places created: {places_created}
        Categories created: {categories_created}
        Images created (records only, not downloaded files): {images_created}
        """))