# myapp/management/commands/generate_colorbars.py
import os
import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.cluster.vq import kmeans2
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings
from myapp.models import PlaceImage

class Command(BaseCommand):
    help = 'Generate color bars for place images'

    def add_arguments(self, parser):
        parser.add_argument('--regenerate', action='store_true', 
                           help='Regenerate color bars even if they already exist')
        
    def handle(self, *args, **options):
        regenerate = options['regenerate']
        
        # Create colorbar directory if it doesn't exist
        colorbar_dir = os.path.join(settings.MEDIA_ROOT, 'colorbars')
        os.makedirs(colorbar_dir, exist_ok=True)
        
        # Get images to process
        if regenerate:
            images = PlaceImage.objects.filter(local_path__isnull=False).exclude(local_path='')
        else:
            images = PlaceImage.objects.filter(
                local_path__isnull=False
            ).exclude(
                local_path=''
            ).filter(
                colorbar_path=''
            )
        
        self.stdout.write(f"Found {images.count()} images to process")
        
        for i, img in enumerate(images):
            if i % 10 == 0:
                self.stdout.write(f"Processing image {i+1}/{images.count()}")
            
            # Skip if no local path
            if not img.local_path:
                continue
            
            # Get the full path to the image
            image_path = os.path.join(settings.MEDIA_ROOT, img.local_path)
            
            # Skip if image doesn't exist
            if not os.path.exists(image_path):
                self.stdout.write(self.style.WARNING(f"Image not found: {image_path}"))
                continue
            
            try:
                # Get dominant colors
                colors = self.get_dominant_colors(image_path)
                
                if not colors:
                    self.stdout.write(self.style.WARNING(f"Could not extract colors from {img.local_path}"))
                    continue
                
                # Store color vector in the database
                img.color_vector = json.dumps(colors)
                
                # Create and save color bar
                colorbar_filename = os.path.splitext(os.path.basename(img.local_path))[0] + "_colors.jpg"
                colorbar_path = os.path.join('colorbars', colorbar_filename)
                full_colorbar_path = os.path.join(settings.MEDIA_ROOT, colorbar_path)
                
                self.create_color_bar(colors, full_colorbar_path)
                
                # Update the database
                img.colorbar_path = colorbar_path
                img.save()
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {img.local_path}: {e}"))
        
        self.stdout.write(self.style.SUCCESS("Color bar generation complete"))
    
    def get_dominant_colors(self, image_path, k=10, resize_dim=(100, 100)):
        """Extract dominant colors using k-means clustering"""
        try:
            image = Image.open(image_path).convert("RGB")
            image = image.resize(resize_dim)
            
            pixels = np.array(image).reshape(-1, 3).astype(np.float32)
            
            centroids, labels = kmeans2(pixels, k=k, minit='points')
            counts = np.bincount(labels)
            
            if np.sum(counts > 0) < k:
                return []
                
            sorted_indices = np.argsort(counts)[::-1]
            dominant_colors = [tuple(map(int, centroids[i])) for i in sorted_indices]
            
            # Flatten the list for storage
            return [c for color in dominant_colors for c in color]
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in get_dominant_colors: {e}"))
            return []
    
    def create_color_bar(self, colors, output_path):
        """Create a visualization of the color palette"""
        try:
            # Reshape colors into RGB tuples
            rgb_colors = [colors[i:i+3] for i in range(0, len(colors), 3)]
            
            # Create color bar
            bar = np.zeros((50, 300, 3), dtype=np.uint8)
            step = 300 // len(rgb_colors)
            
            for i, (r, g, b) in enumerate(rgb_colors):
                bar[:, i * step:(i + 1) * step, :] = [r, g, b]
            
            # Save as file
            plt.figure(figsize=(6, 1))
            plt.axis('off')
            plt.imshow(bar)
            plt.savefig(output_path, format="jpg", bbox_inches='tight', pad_inches=0)
            plt.close()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating color bar: {e}"))
            raise e