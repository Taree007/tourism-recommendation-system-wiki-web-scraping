# myapp/management/commands/enhanced_structural.py
from django.core.management.base import BaseCommand
from django.db import transaction
from myapp.models import Place, SimilarPlace
import numpy as np

class Command(BaseCommand):
    help = 'Create enhanced structural similarities based on city and page views'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                           help='Clear existing structural similarities')
        parser.add_argument('--city-weight', type=float, default=0.6,
                           help='Weight for city matching (default: 0.6)')
        parser.add_argument('--views-weight', type=float, default=0.4,
                           help='Weight for page views similarity (default: 0.4)')

    def handle(self, *args, **options):
        clear = options['clear']
        city_weight = options['city_weight']
        views_weight = options['views_weight']
        
        if city_weight + views_weight != 1.0:
            self.stdout.write(self.style.WARNING(f"Weights sum to {city_weight + views_weight}, not 1.0. Normalizing..."))
            total = city_weight + views_weight
            city_weight /= total
            views_weight /= total
        
        # Clear existing structural similarities if requested
        if clear:
            count = SimilarPlace.objects.filter(similarity_type='structural').count()
            SimilarPlace.objects.filter(similarity_type='structural').delete()
            self.stdout.write(f"Cleared {count} existing structural similarity records")
        
        # Get all places
        places = list(Place.objects.all())
        self.stdout.write(f"Processing {len(places)} places...")
        
        # Get page view statistics for normalization
        page_views = [place.page_views or 0 for place in places]
        max_views = max(page_views) if page_views else 1
        min_views = min(page_views) if page_views else 0
        range_views = max_views - min_views or 1  # Avoid division by zero
        
        self.stdout.write(f"Page views range: {min_views} to {max_views}")
        
        # Calculate similarities
        similarities = []
        for i, place1 in enumerate(places):
            if i % 100 == 0:
                self.stdout.write(f"Processing place {i+1}/{len(places)}")
            
            # Normalize page views to [0,1] range
            views1 = (place1.page_views or 0 - min_views) / range_views
            
            for j, place2 in enumerate(places):
                if i == j:  # Skip self comparison
                    continue
                
                # City similarity component (1.0 if same city, 0.0 if different)
                city_similarity = 1.0 if place1.city_id == place2.city_id else 0.0
                
                # Page views similarity component
                views2 = (place2.page_views or 0 - min_views) / range_views
                
                # Calculate page views similarity (smaller difference = higher similarity)
                views_difference = abs(views1 - views2)
                views_similarity = 1.0 - views_difference
                
                # Combine the two components with weights
                combined_similarity = (
                    city_weight * city_similarity + 
                    views_weight * views_similarity
                )
                
                # Only create similarities above a threshold or in the same city
                if combined_similarity > 0.3 or city_similarity == 1.0:
                    similarities.append({
                        'main_place_id': place1.id,
                        'similar_place_id': place2.id,
                        'similarity_score': round(combined_similarity, 3),
                        'similarity_type': 'structural'
                    })
        
        self.stdout.write(f"Calculated {len(similarities)} structural similarities")
        
        # Save to database in batches
        batch_size = 1000
        with transaction.atomic():
            for i in range(0, len(similarities), batch_size):
                batch = similarities[i:i+batch_size]
                SimilarPlace.objects.bulk_create([
                    SimilarPlace(
                        main_place_id=item['main_place_id'],
                        similar_place_id=item['similar_place_id'],
                        similarity_score=item['similarity_score'],
                        similarity_type=item['similarity_type']
                    ) for item in batch
                ], ignore_conflicts=True)
                self.stdout.write(f"Saved batch {i//batch_size + 1}/{(len(similarities)-1)//batch_size + 1}")
        
        # Summary
        count = SimilarPlace.objects.filter(similarity_type='structural').count()
        self.stdout.write(self.style.SUCCESS(f"Successfully saved {count} enhanced structural similarities"))