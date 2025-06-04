from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import City, Place, Category, PlaceImage, PlaceCategory, SimilarPlace

def index(request):
    """View function for home page"""
    # List all cities
    cities = City.objects.all()
    
    # Get a default city to display if available
    default_city = cities.first()
    
    # Get places for the default city
    places = []
    if default_city:
        # Handle sorting
        sort = request.GET.get('sort', 'score')  # Default to 'score'
        if sort == 'name':
            places = Place.objects.filter(city=default_city).order_by('name')
        else:  # Default to score sorting
            places = Place.objects.filter(city=default_city).order_by('-relevance_score')
            
    context = {
        'cities': cities,
        'selected_city': default_city,
        'places': places,
    }
    
    return render(request, 'myapp/index.html', context)

def city_view(request, city_id):
    """View showing places in a specific city"""
    # Get the selected city
    selected_city = get_object_or_404(City, pk=city_id)
    
    # Get all cities for the navigation
    cities = City.objects.all()
    
   # Handle sorting
    sort = request.GET.get('sort', 'score')  # Default to 'score'
    
    if sort == 'name':
        places = Place.objects.filter(city=selected_city).order_by('name')
    else:  # Default to score sorting
        places = Place.objects.filter(city=selected_city).order_by('-relevance_score')
    
    context = {
        'cities': cities,
        'selected_city': selected_city,
        'places': places,
        'sort': sort,
    }
    
    return render(request, 'myapp/city_view.html', context)

# myapp/views.py
def place_detail(request, place_id):
    """View showing details of a specific place"""
    # Get the selected place
    place = get_object_or_404(Place, pk=place_id)
    
    print(f"Viewing place: {place.name} (ID: {place.id})")
    
    # Get the place's city
    city = place.city
    
    # Get primary image
    primary_image = place.images.filter(is_primary=True).first() or place.images.first()
    
    # Get categories for this place
    categories = Category.objects.filter(placecategory__place=place)
    
    # Get similar places with detailed debugging
    print(f"Looking for similar places for place ID: {place.id}")
    
    # Check if this place has any similar places at all
    total_similar = SimilarPlace.objects.filter(main_place=place).count()
    print(f"Total similar places found: {total_similar}")
    
    # Check exact values used in the filter
    similarity_types = SimilarPlace.objects.values_list('similarity_type', flat=True).distinct()
    print(f"Available similarity types in database: {list(similarity_types)}")
    
    # Get similar places based on structural info
    similar_places_structural = SimilarPlace.objects.filter(
        main_place=place, 
        similarity_type='structural'
    ).select_related('similar_place').order_by('-similarity_score')[:3]
    
    print(f"Structural similar places: {similar_places_structural.count()}")
    
    # Get similar places based on image in same city
    similar_places_same_city = SimilarPlace.objects.filter(
        main_place=place, 
        similarity_type='image_same_city'
    ).select_related('similar_place').order_by('-similarity_score')[:3]
    
    print(f"Image similar places (same city): {similar_places_same_city.count()}")
    
    # Get similar places based on image in different cities
    similar_places_other_cities = SimilarPlace.objects.filter(
        main_place=place, 
        similarity_type='image_diff_city'
    ).select_related('similar_place').order_by('-similarity_score')[:3]
    
    print(f"Image similar places (other cities): {similar_places_other_cities.count()}")
    
    # Try different filter to see if any similar places exist for this place
    any_similar = SimilarPlace.objects.filter(main_place=place)
    print(f"Any similar places with different filter: {any_similar.count()}")
    if any_similar.exists():
        for sim in any_similar[:3]:
            print(f"  - {sim.similarity_type}: {sim.main_place.name} -> {sim.similar_place.name} (score: {sim.similarity_score})")
    
    context = {
        'place': place,
        'city': city,
        'primary_image': primary_image,
        'categories': categories,
        'similar_places_structural': similar_places_structural,
        'similar_places_same_city': similar_places_same_city,
        'similar_places_other_cities': similar_places_other_cities,
    }
    
    return render(request, 'myapp/place_detail.html', context)

# myapp/views.py
def place_detail(request, place_id):
    """View showing details of a specific place"""
    # Get the selected place
    place = get_object_or_404(Place, pk=place_id)
    
    print(f"Viewing place: {place.name} (ID: {place.id})")
    
    # Get the place's city
    city = place.city
    
    # Get primary image
    primary_image = place.images.filter(is_primary=True).first() or place.images.first()
    
    # Get categories for this place
    categories = Category.objects.filter(placecategory__place=place)
    
    # Get similar places with detailed debugging
    print(f"Looking for similar places for place ID: {place.id}")
    
    # Check if this place has any similar places at all
    total_similar = SimilarPlace.objects.filter(main_place=place).count()
    print(f"Total similar places found: {total_similar}")
    
    # Check exact values used in the filter
    similarity_types = SimilarPlace.objects.values_list('similarity_type', flat=True).distinct()
    print(f"Available similarity types in database: {list(similarity_types)}")
    
    # Get similar places based on structural info
    similar_places_structural = SimilarPlace.objects.filter(
        main_place=place, 
        similarity_type='structural'
    ).select_related('similar_place').order_by('-similarity_score')[:3]
    
    print(f"Structural similar places: {similar_places_structural.count()}")
    
    # Get similar places based on image in same city
    similar_places_same_city = SimilarPlace.objects.filter(
        main_place=place, 
        similarity_type='image_same_city'
    ).select_related('similar_place').order_by('-similarity_score')[:3]
    
    print(f"Image similar places (same city): {similar_places_same_city.count()}")
    
    # Get similar places based on image in different cities
    similar_places_other_cities = SimilarPlace.objects.filter(
        main_place=place, 
        similarity_type='image_diff_city'
    ).select_related('similar_place').order_by('-similarity_score')[:3]
    
    print(f"Image similar places (other cities): {similar_places_other_cities.count()}")
    
    # Try different filter to see if any similar places exist for this place
    any_similar = SimilarPlace.objects.filter(main_place=place)
    print(f"Any similar places with different filter: {any_similar.count()}")
    if any_similar.exists():
        for sim in any_similar[:3]:
            print(f"  - {sim.similarity_type}: {sim.main_place.name} -> {sim.similar_place.name} (score: {sim.similarity_score})")
    
    context = {
        'place': place,
        'city': city,
        'primary_image': primary_image,
        'categories': categories,
        'similar_places_structural': similar_places_structural,
        'similar_places_same_city': similar_places_same_city,
        'similar_places_other_cities': similar_places_other_cities,
    }
    
    return render(request, 'myapp/place_detail.html', context)

def search(request):
    """Simple search view"""
    query = request.GET.get('q', '')
    results = []
    
    if query:
        results = Place.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )
    
    context = {
        'query': query,
        'results': results,
    }
    
    return render(request, 'myapp/search_results.html', context)