# myapp/management/commands/calculate_enhanced_pagerank.py
import numpy as np
from django.core.management.base import BaseCommand
from django.db.models import Max
from myapp.models import Place, Category, PlaceCategory

class Command(BaseCommand):
    help = 'Calculate enhanced PageRank scores incorporating popularity metrics'

    def add_arguments(self, parser):
        parser.add_argument('--damping', type=float, default=0.85,
                            help='Damping factor (default: 0.85)')
        parser.add_argument('--iterations', type=int, default=100,
                            help='Maximum number of iterations (default: 100)')
        parser.add_argument('--tolerance', type=float, default=0.0001,
                            help='Convergence tolerance (default: 0.0001)')
        parser.add_argument('--pageview-weight', type=float, default=0.3,
                            help='Weight for page view influence (default: 0.3)')
        parser.add_argument('--language-weight', type=float, default=0.2,
                            help='Weight for language count influence (default: 0.2)')
        parser.add_argument('--min-score', type=float, default=0.1,
                            help='Minimum final score (default: 0.1)')
        parser.add_argument('--max-score', type=float, default=5.0,
                            help='Maximum final score (default: 5.0)')

    def handle(self, *args, **options):
        damping = options['damping']
        max_iterations = options['iterations']
        tolerance = options['tolerance']
        pageview_weight = options['pageview_weight']
        language_weight = options['language_weight']
        min_score = options['min_score']
        max_score = options['max_score']
        
        # Connection weight (remaining percentage after page views and languages)
        connection_weight = 1.0 - (pageview_weight + language_weight)
        
        if connection_weight <= 0:
            self.stdout.write(self.style.ERROR("Error: Combined weights exceed 1.0"))
            return
        
        self.stdout.write("Building enhanced PageRank model...")
        self.stdout.write(f"Weights: Connections={connection_weight:.2f}, PageViews={pageview_weight:.2f}, Languages={language_weight:.2f}")
        
        # Get all places
        places = list(Place.objects.all())
        if not places:
            self.stdout.write(self.style.ERROR("No places found in database"))
            return
            
        n = len(places)
        self.stdout.write(f"Found {n} places")
        
        # Create a mapping of place ID to index
        place_indices = {place.id: i for i, place in enumerate(places)}
        
        # Get category data
        place_categories = {}
        for pc in PlaceCategory.objects.all():
            if pc.place_id not in place_indices:
                continue
                
            if pc.place_id not in place_categories:
                place_categories[pc.place_id] = set()
            place_categories[pc.place_id].add(pc.category_id)
        
        # Create adjacency matrix with weighted connections
        M = np.zeros((n, n))
        
        # Populate the matrix
        for i, place1 in enumerate(places):
            for j, place2 in enumerate(places):
                if i == j:  # No self-links
                    continue
                
                weight = 0
                
                # Places in same city have a connection
                if place1.city_id == place2.city_id:
                    weight += 0.5
                
                # Category similarity
                cats1 = place_categories.get(place1.id, set())
                cats2 = place_categories.get(place2.id, set())
                
                if cats1 and cats2:
                    # Jaccard similarity for categories
                    similarity = len(cats1.intersection(cats2)) / len(cats1.union(cats2))
                    weight += similarity * 0.5
                
                if weight > 0:
                    M[i, j] = weight
        
        # Normalize the matrix so each row sums to 1
        row_sums = M.sum(axis=1)
        for i in range(n):
            if row_sums[i] > 0:
                M[i] = M[i] / row_sums[i]
        
        # Get popularity metrics
        max_page_views = max(place.page_views or 0 for place in places)
        max_languages = max(place.number_of_languages or 0 for place in places)
        
        if max_page_views == 0:
            max_page_views = 1  # Avoid division by zero
        if max_languages == 0:
            max_languages = 1  # Avoid division by zero
        
        # Create popularity vectors (normalized)
        page_view_vector = np.array([(place.page_views or 0) / max_page_views for place in places])
        language_vector = np.array([(place.number_of_languages or 0) / max_languages for place in places])
        
        # Make sure vectors sum to 1 for proper weighting
        if page_view_vector.sum() > 0:
            page_view_vector = page_view_vector / page_view_vector.sum()
        if language_vector.sum() > 0:
            language_vector = language_vector / language_vector.sum()
        
        # Initialize PageRank vector
        pagerank = np.ones(n) / n
        
        # Power iteration method with added popularity influence
        for iteration in range(max_iterations):
            # Standard PageRank calculation (weighted by connection_weight)
            connection_influence = M.T.dot(pagerank)
            
            # Combined calculation with popularity metrics
            new_pagerank = (1 - damping) / n + damping * (
                connection_weight * connection_influence +
                pageview_weight * page_view_vector + 
                language_weight * language_vector
            )
            
            # Normalize to ensure sum=1
            new_pagerank = new_pagerank / new_pagerank.sum()
            
            # Check convergence
            diff = np.linalg.norm(new_pagerank - pagerank)
            pagerank = new_pagerank
            
            if iteration % 10 == 0 or diff < tolerance:
                self.stdout.write(f"Iteration {iteration}: change = {diff:.6f}")
            
            if diff < tolerance:
                self.stdout.write(self.style.SUCCESS(f"Converged after {iteration+1} iterations"))
                break
        else:
            self.stdout.write(self.style.WARNING(f"Reached maximum iterations ({max_iterations}) without convergence"))
        
        # Scale scores to desired range
        min_raw = pagerank.min()
        max_raw = pagerank.max()
        
        # Avoid division by zero if all scores are identical
        if max_raw == min_raw:
            scaled_scores = np.ones(n) * ((min_score + max_score) / 2)
        else:
            scaled_scores = min_score + (pagerank - min_raw) * (max_score - min_score) / (max_raw - min_raw)
        
        # Update database with PageRank scores
        for i, place in enumerate(places):
            place.relevance_score = round(float(scaled_scores[i]), 2)
            place.save()
            
            self.stdout.write(f"Updated {place.name}: {place.relevance_score}")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully updated enhanced PageRank scores for {n} places"))