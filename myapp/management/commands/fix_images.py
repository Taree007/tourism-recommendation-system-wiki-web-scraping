import os
from django.core.management.base import BaseCommand
from django.conf import settings
from PIL import Image
import requests
from io import BytesIO
import re
from django.utils.text import slugify

from myapp.models import PlaceImage, Place # Make sure your models are correctly imported

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com/",
    "DNT": "1"
}

class Command(BaseCommand):
    help = 'Manages place images: deletes specific existing local files and re-downloads them from URLs.'

    def add_arguments(self, parser):
        parser.add_argument('--re-download-all-existing', action='store_true',
                            help='Delete existing local image files for all PlaceImage records with an image_url, then re-download them.')
        parser.add_argument('--delete-local-only', action='store_true',
                            help='Delete only the local image files, but keep the PlaceImage records and their image_url.')
        parser.add_argument('--force-download', action='store_true',
                            help='Force re-download of all images that have an image_url, regardless of local_path status. This will overwrite existing local files.')
        parser.add_argument('--download-missing-only', action='store_true', # <-- NEW ARGUMENT
                            help='Download images ONLY for PlaceImage records that have an image_url but no local_path.')


    def _download_image(self, title, place_id, url, folder="media/images", size=(300, 300)):
        """
        Downloads an image from a URL, resizes it, and saves it locally.
        Returns the relative path (e.g., 'images/filename.jpg') or None on failure.
        """
        os.makedirs(folder, exist_ok=True)
        try:
            self.stdout.write(f"  Attempting to download: {url}")
            response = requests.get(url, headers=headers, timeout=15) # Increased timeout
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

            image = Image.open(BytesIO(response.content)).convert("RGB")
            image = image.resize(size, Image.Resampling.LANCZOS)

            # Sanitize title for filename, keep it concise and unique per place ID
            sanitized_title = slugify(title)[:50] # Limit length for filenames
            filename = f"{place_id}_{sanitized_title}.jpg"
            save_path = os.path.join(folder, filename)

            # Ensure the filename is unique if it already exists (though place_id helps)
            counter = 1
            original_save_path = save_path
            while os.path.exists(save_path):
                filename = f"{place_id}_{sanitized_title}_{counter}.jpg"
                save_path = os.path.join(folder, filename)
                counter += 1

            image.save(save_path, format="JPEG", quality=75)
            self.stdout.write(f"  Saved image: {save_path}")
            return os.path.join("images", filename) # Return path relative to media
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"  Failed to download image from {url}: {e}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  Failed to process/save image from {url}: {e}"))
        return None

    def handle(self, *args, **options):
        download_folder = os.path.join(settings.MEDIA_ROOT, 'images')
        os.makedirs(download_folder, exist_ok=True) # Ensure the directory exists

        # --- Option: Delete local files only ---
        if options['delete_local_only']:
            self.stdout.write(self.style.WARNING("Deleting local image files only (keeping database records)..."))
            deleted_files_count = 0
            for img in PlaceImage.objects.all():
                if img.local_path:
                    full_path = os.path.join(settings.MEDIA_ROOT, img.local_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            img.local_path = '' # Clear the local_path in the DB
                            img.save()
                            self.stdout.write(f"Deleted local file: {full_path} and cleared DB path.")
                            deleted_files_count += 1
                        except OSError as e:
                            self.stderr.write(self.style.ERROR(f"Error deleting file {full_path}: {e}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Local file not found for {img.place.name} at {full_path}. Clearing DB path."))
                        img.local_path = ''
                        img.save()
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_files_count} local image files and updated DB records."))
            return # Exit after this operation, as it's a standalone task

        # --- Option: Force re-download or Re-download all existing or Download missing only ---
        # Determine the queryset based on the options provided
        images_to_process = None
        action_description = ""

        if options['re_download_all_existing']:
            action_description = "Deleting existing local image files and then re-downloading for all PlaceImages..."
            # First, delete all associated local files and clear paths
            self.stdout.write(self.style.WARNING("Performing initial cleanup: Deleting old local image files and clearing DB paths..."))
            deleted_count = 0
            for img in PlaceImage.objects.all():
                if img.local_path:
                    full_path = os.path.join(settings.MEDIA_ROOT, img.local_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            self.stdout.write(f"  Deleted old file: {full_path}")
                            deleted_count += 1
                        except OSError as e:
                            self.stderr.write(self.style.ERROR(f"  Error deleting file {full_path}: {e}"))
                img.local_path = '' # Crucially, clear the local_path for re-download logic
                img.save()
            self.stdout.write(self.style.SUCCESS(f"Finished deleting {deleted_count} old local image files and cleared their DB paths."))
            images_to_process = PlaceImage.objects.exclude(image_url='') # After clearing, all are effectively "missing" local paths
            action_description = "Starting re-download process for all PlaceImages with a URL..."

        elif options['force_download']:
            images_to_process = PlaceImage.objects.exclude(image_url='')
            action_description = "Starting force re-download process for all PlaceImages with a URL..."

        elif options['download_missing_only']: # <-- LOGIC FOR THE NEW ARGUMENT
            images_to_process = PlaceImage.objects.filter(local_path='').exclude(image_url='')
            action_description = "Starting download process for PlaceImages with missing local paths..."

        # If no specific download option is chosen, do nothing in this section
        if images_to_process is None:
            self.stdout.write(self.style.WARNING("No image download/re-download option selected. Use --re-download-all-existing, --force-download, or --download-missing-only."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(action_description))

        total_to_process = images_to_process.count()
        re_downloaded_count = 0
        skipped_count = 0

        if total_to_process == 0:
            self.stdout.write(self.style.SUCCESS("No images found matching the criteria for download."))
            return

        self.stdout.write(f"Found {total_to_process} images to process.")

        for i, img in enumerate(images_to_process):
            if not img.image_url: # Double check, though query should exclude these
                skipped_count += 1
                continue

            self.stdout.write(f"Processing ({i+1}/{total_to_process}) for Place: {img.place.name} (ID: {img.place.id})")

            # Call the download function
            new_local_rel_path = self._download_image(img.place.name, img.place.id, img.image_url, folder=download_folder)

            if new_local_rel_path:
                # Update the local_path in the database
                if img.local_path != new_local_rel_path: # Only save if path changed
                    img.local_path = new_local_rel_path
                    img.save()
                    re_downloaded_count += 1
                    self.stdout.write(f"  Updated DB path for {img.place.name} to: {new_local_rel_path}")
                else:
                    self.stdout.write(f"  Path for {img.place.name} remains unchanged: {new_local_rel_path}")
                    re_downloaded_count += 1 # Count as processed successfully, even if path was already correct
            else:
                self.stdout.write(self.style.WARNING(f"  Failed to download image for {img.place.name} from {img.image_url}."))
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f"""
        Image download process completed!
        Successfully downloaded/updated: {re_downloaded_count} images.
        Skipped/Failed: {skipped_count} images.
        """))