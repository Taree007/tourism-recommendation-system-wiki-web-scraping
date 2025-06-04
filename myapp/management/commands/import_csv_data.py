import csv
import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings
from PIL import Image
import requests
from io import BytesIO
import re

from myapp.models import City, Place, Category, PlaceImage, PlaceCategory


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com/",
    "DNT": "1"
}
class Command(BaseCommand):
    help = 'Import data from CSV file'

    #def add_arguments(self, parser):
       # parser.add_argument('csv_file', type=str, help='Path to the CSV file')
       # parser.add_argument('--images-dir', type=str, help='Path to the images directory')

    def downloadImage(title, id, url, folder="images", size=(300, 300)):
        os.makedirs(folder, exist_ok=True)
        # print(f"Trying to download: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content)).convert("RGB")
                image = image.resize(size, Image.Resampling.LANCZOS)

                name = re.sub(r'[<>:"/\\|?* ,.\']', '', title)
                filename = str(id)+"_"+name+".jpg"
                save_path = os.path.join(folder, filename)
                image.save(save_path, format="JPEG", quality=60)
                print(f"Saved image: {save_path}")
                return save_path
            else:
                print(f"Error {response.status_code} on {url}")
        except Exception as e:
            print(f"Failed to download image from {url}: {e}")
        return None

    def handle(self, *args, **options):
       # csv_file = options['csv_file']
        #images_dir = options.get('images_dir')
        images = PlaceImage.objects.filter(local_path='')
        updated_count = 0
        # Hardcoded paths
        csv_file = os.path.join(settings.BASE_DIR, r"C:\Users\ginta\OneDrive - Kaunas University of Technology\4sem\bigdata\projektas\smthfordjango\cleaned_TourismObjects.csv")
        images_dir = os.path.join(settings.BASE_DIR, 'media', 'images')

        if not os.path.exists(images_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {images_dir}"))
            return
        
        image_files = os.listdir(images_dir)
        self.stdout.write(f"Found {len(image_files)} image files in directory")

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f"File not found: {csv_file}"))
            return
        
         # Create two separate mappings for IDs and names
        id_map = {}
        name_map = {}
        
        for filename in image_files:
            # Extract the place ID from the filename if it starts with a number followed by underscore
            parts = filename.split('_', 1)
            if len(parts) > 1 and parts[0].isdigit():
                place_id = int(parts[0])
                id_map[place_id] = filename
            
            # Always add to name map for fuzzy matching
            name_slug = os.path.splitext(filename)[0].lower()
            name_map[name_slug] = filename
        
        # Update the database
        for img in images:
            place = img.place
            
            # Try to find image by place ID
            if place.id in id_map:
                filename = id_map[place.id]
                img.local_path = f"images/{filename}"
                img.save()
                updated_count += 1
                self.stdout.write(f"Updated {place.name} with {filename}")
                continue
                
            # Try to find by matching name parts
            place_name_slug = slugify(place.name).lower()
            matched = False
            
            # Try exact match first
            if place_name_slug in name_map:
                filename = name_map[place_name_slug]
                img.local_path = f"images/{filename}"
                img.save()
                updated_count += 1
                self.stdout.write(f"Updated {place.name} with {filename} (exact name match)")
                matched = True
                continue
            
            # Try fuzzy matching
            for name_slug, filename in name_map.items():
                # Check if the place name contains the filename or vice versa
                if place_name_slug in name_slug or any(word in name_slug for word in place_name_slug.split('-')):
                    img.local_path = f"images/{filename}"
                    img.save()
                    updated_count += 1
                    self.stdout.write(f"Updated {place.name} with {filename} (fuzzy name match)")
                    matched = True
                    break
            
            
            if not matched:
                self.stdout.write(self.style.WARNING(f"Could not find image for {place.name}"))
        
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} out of {images.count()} images"))
        # Clear existing data if needed
        # Uncomment these lines if you want to clear existing data before import
        # self.stdout.write("Clearing existing data...")
        # Place.objects.all().delete()
        # City.objects.all().delete()
        # Category.objects.all().delete()
        # PlaceImage.objects.all().delete()
        
        # Track counters for summary
        cities_created = 0
        places_created = 0
        categories_created = 0
        images_created = 0
        
        # Dictionary to store created cities
        city_dict = {}
        category_dict = {}
        
        with open(csv_file, encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            total_rows = sum(1 for row in csv.reader(open(csv_file, encoding='utf-8'))) - 1
            
            self.stdout.write(f"Starting import of {total_rows} rows...")
            
            # Reset file pointer
            f.seek(0)
            next(reader)  # Skip header row
            
            # Process each row
            for i, row in enumerate(reader):
                # Check if we have the city column
                city_name = row.get('City', '')
                if not city_name:
                    self.stdout.write(self.style.WARNING(f"Row {i+2}: Missing city name, skipping"))
                    continue
                
                # Create or get city
                if city_name not in city_dict:
                    city, created = City.objects.get_or_create(name=city_name)
                    city_dict[city_name] = city
                    if created:
                        cities_created += 1
                city = city_dict[city_name]
                
                # Create place
                place_name = row.get('Title', '')
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
                
                # Process image if available
                image_url = row.get('Image link', '')
                if image_url:
                    # Check if image already exists
                    if not PlaceImage.objects.filter(place=place, image_url=image_url).exists():
                        # Create image record
                        image = PlaceImage(
                            place=place,
                            image_url=image_url,
                            is_primary=True  # First image is primary
                        )
                        
                        # If we have an images directory, check for local path
                        if images_dir:
                            # Construct possible filenames
                            possible_filenames = [
                                f"{place.id}_{slugify(place.name)}.jpg",
                                f"{place.id}_{place.name.replace(' ', '_')}.jpg",
                                f"{slugify(place.name)}.jpg",
                            ]
                            
                            # Check if any of these files exist
                            for filename in possible_filenames:
                                local_path = os.path.join(images_dir, filename)
                                if os.path.exists(local_path):
                                    # Get path relative to media directory
                                    rel_path = os.path.relpath(local_path, 'media')
                                    image.local_path = rel_path
                                    break
                        
                        image.save()
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
                            if category_name not in category_dict:
                                category, created = Category.objects.get_or_create(name=category_name)
                                category_dict[category_name] = category
                                if created:
                                    categories_created += 1
                            category = category_dict[category_name]
                            
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
        Images created: {images_created}
        """))
    
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