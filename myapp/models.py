from django.db import models

class City(models.Model):
    """Model representing a city with tourist attractions"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Cities"
        ordering = ['name']


class Category(models.Model):
    """Model representing categories of tourist attractions"""
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"


class Place(models.Model):
    """Model representing a tourist attraction/point of interest"""
    name = models.CharField(max_length=200)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='places')
    description = models.TextField(blank=True)
    wikipedia_link = models.URLField(blank=True, verbose_name="Link")
    
    # Fields from your CSV data
    title = models.CharField(max_length=255, blank=True)  # Sometimes different from name
    page_views = models.IntegerField(null=True, blank=True, verbose_name="Page Views")
    number_of_categories = models.IntegerField(null=True, blank=True, verbose_name="Number of Categories")
    number_of_languages = models.IntegerField(null=True, blank=True, verbose_name="Number of Languages")
    number_of_references = models.IntegerField(null=True, blank=True, verbose_name="Number of References")
    number_of_sections = models.IntegerField(null=True, blank=True, verbose_name="Number of Sections")
    number_of_links = models.IntegerField(null=True, blank=True, verbose_name="Number of Links")
    number_of_images = models.IntegerField(null=True, blank=True, verbose_name="Number of Images")
    number_of_external_links = models.IntegerField(null=True, blank=True, verbose_name="Number of External Links")
    page_length = models.IntegerField(null=True, blank=True, verbose_name="Page Length")
    date_created = models.DateTimeField(null=True, blank=True, verbose_name="Date created")
    
    # Add any other fields from your CSV
    linkshere = models.IntegerField(null=True, blank=True)
    total_links = models.IntegerField(null=True, blank=True)
    revision_count = models.IntegerField(null=True, blank=True)
    language_links = models.IntegerField(null=True, blank=True)
    category_count = models.IntegerField(null=True, blank=True)
    
    # We'll use this temporarily until we implement PageRank
    relevance_score = models.FloatField(default=0)
    
    def __str__(self):
        return f"{self.name} ({self.city.name})"
    
    class Meta:
        ordering = ['-relevance_score']


class PlaceImage(models.Model):
    """Model representing images of tourist attractions"""
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField(verbose_name="Image link")
    local_path = models.CharField(max_length=255, blank=True)
    color_vector = models.TextField(blank=True)  # Store color vector data
    colorbar_path = models.CharField(max_length=255, blank=True)  # New field for color bar path
    is_primary = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Image for {self.place.name}"


class PlaceCategory(models.Model):
    """Junction table for Place and Category with explicit model"""
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.place.name} - {self.category.name}"
    
    class Meta:
        unique_together = ('place', 'category')
        verbose_name_plural = "Place Categories"

        
class SimilarPlace(models.Model):
    SIMILARITY_TYPES = [
        ('structural', 'Structural similarity'),
        ('image_same_city', 'Image similarity (same city)'),
        ('image_diff_city', 'Image similarity (different city)'),
    ]
    
    main_place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='similar_to_me')
    similar_place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='similar_to_others')
    similarity_score = models.FloatField()
    similarity_type = models.CharField(max_length=20, choices=SIMILARITY_TYPES)
    
    class Meta:
        unique_together = ('main_place', 'similar_place', 'similarity_type')