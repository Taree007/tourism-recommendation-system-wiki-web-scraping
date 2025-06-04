# myapp/admin.py
from django.contrib import admin
from .models import City, Place, Category, PlaceImage, PlaceCategory, SimilarPlace

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class PlaceImageInline(admin.TabularInline):
    model = PlaceImage
    extra = 0

class PlaceCategoryInline(admin.TabularInline):
    model = PlaceCategory
    extra = 0

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'relevance_score')
    list_filter = ('city',)
    search_fields = ('name', 'description')
    inlines = [PlaceImageInline, PlaceCategoryInline]

@admin.register(PlaceImage)
class PlaceImageAdmin(admin.ModelAdmin):
    list_display = ('place', 'is_primary')
    list_filter = ('is_primary',)
    search_fields = ('place__name',)

@admin.register(PlaceCategory)
class PlaceCategoryAdmin(admin.ModelAdmin):
    list_display = ('place', 'category')
    list_filter = ('category',)
    search_fields = ('place__name', 'category__name')

@admin.register(SimilarPlace)
class SimilarPlaceAdmin(admin.ModelAdmin):
    list_display = ('main_place', 'similar_place', 'similarity_type', 'similarity_score')
    list_filter = ('similarity_type',)
    search_fields = ('main_place__name', 'similar_place__name')
    raw_id_fields = ('main_place', 'similar_place')