# myapp/management/commands/test_similar.py
from django.core.management.base import BaseCommand
from myapp.models import Place, PlaceImage, SimilarPlace
import json
import numpy as np

class Command(BaseCommand):
    help = 'Test similar places functionality'

    def add_arguments(self, parser):
        parser.add_argument('--place-id', type=int, default=None,
                           help='Specific place ID to check')
        parser.add_argument('--create', action='store_true',
                           help='Create test similarity records')

    def handle(self, *args, **options):
        place_id = options['place_id']
        create_test = options['create']
        
        # Check if SimilarPlace records exist
        total = SimilarPlace.objects.count()
        self.stdout.write(f"Total SimilarPlace records: {total}")
        
        # Check counts by type
        types = SimilarPlace.objects.values_list('similarity_type', flat=True).distinct()
        self.stdout.write(f"Similarity types in database: {list(types)}")
        
        for sim_type in types:
            count = SimilarPlace.objects.filter(similarity_type=sim_type).count()
            self.stdout.write(f"  - {sim_type}: {count} records")
        
        # Check a specific place if provided
        if place_id:
            try:
                place = Place.objects.get(id=place_id)
                self.stdout.write(f"Checking place: {place.name} (ID: {place_id})")
                
                # Check similar places
                similar = SimilarPlace.objects.filter(main_place=place)
                self.stdout.write(f"Similar places for {place.name}: {similar.count()}")
                
                # Check by type
                for sim_type in types:
                    count = similar.filter(similarity_type=sim_type).count()
                    self.stdout.write(f"  - {sim_type}: {count} records")
                
                # Show some examples
                if similar.exists():
                    self.stdout.write("Examples:")
                    for sim in similar[:5]:
                        self.stdout.write(f"  - {sim.similarity_type}: {sim.main_place.name} -> {sim.similar_place.name} (score: {sim.similarity_score})")
                
                # Create test similarities if requested
                if create_test and similar.count() == 0:
                    self.stdout.write("Creating test similarity records...")
                    
                    # Find some other places to link to
                    other_places = Place.objects.exclude(id=place_id)
                    
                    # Create a few test records of each type
                    for i, other in enumerate(other_places[:3]):
                        # Structural similarity
                        SimilarPlace.objects.create(
                            main_place=place,
                            similar_place=other,
                            similarity_score=0.9 - (i * 0.1),
                            similarity_type='structural'
                        )
                        
                        # Image same city (if same city)
                        if place.city_id == other.city_id:
                            SimilarPlace.objects.create(
                                main_place=place,
                                similar_place=other,
                                similarity_score=0.8 - (i * 0.1),
                                similarity_type='image_same_city'
                            )
                        
                        # Image different city (if different city)
                        if place.city_id != other.city_id:
                            SimilarPlace.objects.create(
                                main_place=place,
                                similar_place=other,
                                similarity_score=0.7 - (i * 0.1),
                                similarity_type='image_diff_city'
                            )
                    
                    # Check the created records
                    similar = SimilarPlace.objects.filter(main_place=place)
                    self.stdout.write(f"Created {similar.count()} test similarity records")
            
            except Place.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Place with ID {place_id} does not exist"))
        
        # Analyze the SimilarPlace table
        if total > 0:
            # Check for places with no similar places
            all_places = Place.objects.count()
            places_with_similar = Place.objects.filter(similar_to_me__isnull=False).distinct().count()
            self.stdout.write(f"Places with at least one similar place: {places_with_similar} out of {all_places}")
            
            # Check for invalid records
            invalid = SimilarPlace.objects.filter(similar_place__isnull=True).count()
            self.stdout.write(f"Invalid records (null similar_place): {invalid}")
            
            # Check similarity score distribution
            min_score = SimilarPlace.objects.order_by('similarity_score').values_list('similarity_score', flat=True).first()
            max_score = SimilarPlace.objects.order_by('-similarity_score').values_list('similarity_score', flat=True).first()
            self.stdout.write(f"Similarity score range: {min_score} to {max_score}")