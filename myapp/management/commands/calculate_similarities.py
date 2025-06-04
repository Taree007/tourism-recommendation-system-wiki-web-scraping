# myapp/management/commands/calculate_similarities.py
import os
import numpy as np
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from myapp.models import Place, PlaceImage, PlaceCategory, SimilarPlace
from mpi4py import MPI

class Command(BaseCommand):
    help = 'Calculate similarities between places using parallel processing'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                           help='Clear existing similarities before calculating')
        parser.add_argument('--structural-only', action='store_true',
                           help='Calculate only structural similarities')
        parser.add_argument('--image-only', action='store_true',
                           help='Calculate only image-based similarities')

    def handle(self, *args, **options):
        # Initialize MPI
        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()
        size = comm.Get_size()
        
        if rank == 0:
            self.stdout.write(f"Starting similarity calculation with {size} processes")
        
        clear_existing = options['clear']
        structural_only = options['structural_only']
        image_only = options['image_only']
        
        # If no specific type is selected, do both
        if not structural_only and not image_only:
            structural_only = True
            image_only = True
            
        # Clear existing similarities if requested (only on rank 0)
        if rank == 0 and clear_existing:
            types_to_clear = []
            if structural_only:
                types_to_clear.append('structural')
            if image_only:
                types_to_clear.extend(['image_same_city', 'image_diff_city'])
                
            if types_to_clear:
                count = SimilarPlace.objects.filter(similarity_type__in=types_to_clear).count()
                SimilarPlace.objects.filter(similarity_type__in=types_to_clear).delete()
                self.stdout.write(f"Cleared {count} existing similarities")
        
        # Wait for all processes to sync
        comm.Barrier()
        
        # Get all places
        if rank == 0:
            places = list(Place.objects.all())
            # Partition places for parallel processing
            chunks = [[] for _ in range(size)]
            for i, place in enumerate(places):
                chunks[i % size].append(place)
        else:
            chunks = None
            places = None
            
        # Distribute data to all processes
        my_places = comm.scatter(chunks, root=0)
        
        if rank == 0:
            self.stdout.write(f"Distributed {len(places)} places across {size} processes")
            self.stdout.write(f"Process 0 received {len(my_places)} places")
        
        # Calculate similarities for my chunk of places
        structural_results = []
        image_same_city_results = []
        image_diff_city_results = []
        
        # Get all places for comparison (each process needs all places)
        all_places = list(Place.objects.all())
        
        # Get category data for structural similarity
        if structural_only:
            # Each place needs its categories for structural comparison
            place_categories = {}
            for pc in PlaceCategory.objects.all():
                if pc.place_id not in place_categories:
                    place_categories[pc.place_id] = set()
                place_categories[pc.place_id].add(pc.category_id)
        
        # Get image data for image similarity
        if image_only:
            # Get color vectors for image similarity
            place_colors = {}
            for img in PlaceImage.objects.filter(color_vector__isnull=False).exclude(color_vector=''):
                try:
                    colors = json.loads(img.color_vector)
                    if colors:  # Only store if we have valid colors
                        place_colors[img.place_id] = np.array(colors)
                except:
                    continue
        
        # Process each place in my chunk
        for i, place in enumerate(my_places):
            if i % 10 == 0 and rank == 0:
                self.stdout.write(f"Process {rank} processing place {i+1}/{len(my_places)}")
            
            # Calculate structural similarities
            if structural_only:
                place_cats = place_categories.get(place.id, set())
                
                for other_place in all_places:
                    if place.id == other_place.id:
                        continue  # Skip self-comparison
                    
                    # Get categories for other place
                    other_cats = place_categories.get(other_place.id, set())
                    
                    # Calculate Jaccard similarity if both have categories
                    if place_cats and other_cats:
                        intersection = len(place_cats.intersection(other_cats))
                        union = len(place_cats.union(other_cats))
                        similarity = intersection / union if union > 0 else 0
                        
                        # Same city gives bonus
                        if place.city_id == other_place.city_id:
                            similarity = similarity * 0.7 + 0.3  # 30% boost for same city
                        
                        # Store if significant similarity
                        if similarity > 0.1:  # Threshold to avoid noise
                            structural_results.append({
                                'main_place_id': place.id,
                                'similar_place_id': other_place.id,
                                'similarity_score': round(similarity, 3),
                                'similarity_type': 'structural'
                            })
            
            # Calculate image similarities
            if image_only:
                # Only proceed if this place has color data
                if place.id not in place_colors:
                    continue
                
                place_color_vector = place_colors[place.id]
                
                for other_place in all_places:
                    if place.id == other_place.id or other_place.id not in place_colors:
                        continue  # Skip self or places without colors
                    
                    other_color_vector = place_colors[other_place.id]
                    
                    # Calculate cosine similarity between color vectors
                    try:
                        # Normalize vectors
                        norm1 = np.linalg.norm(place_color_vector)
                        norm2 = np.linalg.norm(other_color_vector)
                        
                        if norm1 == 0 or norm2 == 0:
                            continue
                            
                        # Make sure vectors are same length (crop if needed)
                        min_length = min(len(place_color_vector), len(other_color_vector))
                        v1 = place_color_vector[:min_length]
                        v2 = other_color_vector[:min_length]
                        
                        # Calculate cosine similarity
                        similarity = np.dot(v1, v2) / (norm1 * norm2)
                        similarity = (similarity + 1) / 2  # Convert from [-1,1] to [0,1]
                        
                        # Determine similarity type based on city
                        if place.city_id == other_place.city_id:
                            # Same city
                            image_same_city_results.append({
                                'main_place_id': place.id,
                                'similar_place_id': other_place.id,
                                'similarity_score': round(similarity, 3),
                                'similarity_type': 'image_same_city'
                            })
                        else:
                            # Different city
                            image_diff_city_results.append({
                                'main_place_id': place.id,
                                'similar_place_id': other_place.id,
                                'similarity_score': round(similarity, 3),
                                'similarity_type': 'image_diff_city'
                            })
                    except Exception as e:
                        if rank == 0:
                            self.stdout.write(self.style.WARNING(f"Error calculating image similarity: {e}"))
        
        # Gather results from all processes
        all_structural = comm.gather(structural_results, root=0)
        all_image_same_city = comm.gather(image_same_city_results, root=0)
        all_image_diff_city = comm.gather(image_diff_city_results, root=0)
        
        # Process 0 saves the results to database
         
        if rank == 0:
            # Flatten gathered results
            flat_structural = [item for sublist in all_structural for item in sublist]
            flat_image_same_city = [item for sublist in all_image_same_city for item in sublist]
            flat_image_diff_city = [item for sublist in all_image_diff_city for item in sublist]
            
            total_similarities = len(flat_structural) + len(flat_image_same_city) + len(flat_image_diff_city)
            self.stdout.write(f"Total similarities found: {total_similarities}")
            self.stdout.write(f"- Structural: {len(flat_structural)}")
            self.stdout.write(f"- Image (same city): {len(flat_image_same_city)}")
            self.stdout.write(f"- Image (different city): {len(flat_image_diff_city)}")
            
            # Add this line here:
            batch_size = 1000  # Define batch_size before using it
            
            # Save to database in chunks to avoid memory issues
            with transaction.atomic():
                # Save structural similarities
                if flat_structural:
                    for i in range(0, len(flat_structural), batch_size):
                        batch = flat_structural[i:i+batch_size]
                        SimilarPlace.objects.bulk_create([
                            SimilarPlace(
                                main_place_id=item['main_place_id'],
                                similar_place_id=item['similar_place_id'],
                                similarity_score=item['similarity_score'],
                                similarity_type=item['similarity_type']
                            ) for item in batch
                        ], ignore_conflicts=True)
                        self.stdout.write(f"Saved {i+len(batch)}/{len(flat_structural)} structural similarities")
                
                # Save image same city similarities
                if flat_image_same_city:
                    for i in range(0, len(flat_image_same_city), batch_size):
                        batch = flat_image_same_city[i:i+batch_size]
                        SimilarPlace.objects.bulk_create([
                            SimilarPlace(
                                main_place_id=item['main_place_id'],
                                similar_place_id=item['similar_place_id'],
                                similarity_score=item['similarity_score'],
                                similarity_type=item['similarity_type']
                            ) for item in batch
                        ], ignore_conflicts=True)
                        self.stdout.write(f"Saved {i+len(batch)}/{len(flat_image_same_city)} image same city similarities")
                
                # Save image different city similarities
                if flat_image_diff_city:
                    for i in range(0, len(flat_image_diff_city), batch_size):
                        batch = flat_image_diff_city[i:i+batch_size]
                        SimilarPlace.objects.bulk_create([
                            SimilarPlace(
                                main_place_id=item['main_place_id'],
                                similar_place_id=item['similar_place_id'],
                                similarity_score=item['similarity_score'],
                                similarity_type=item['similarity_type']
                            ) for item in batch
                        ], ignore_conflicts=True)
                        self.stdout.write(f"Saved {i+len(batch)}/{len(flat_image_diff_city)} image different city similarities")
            
            self.stdout.write(self.style.SUCCESS("Successfully calculated and saved all similarities"))