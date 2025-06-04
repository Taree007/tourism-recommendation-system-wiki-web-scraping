from django.urls import path
from . import views

app_name = 'myapp'  # This line registers the namespace

urlpatterns = [
    path('', views.index, name='index'),
    path('city/<int:city_id>/', views.city_view, name='city_view'),
    path('place/<int:place_id>/', views.place_detail, name='place_detail'),
    path('search/', views.search, name='search'),
    #path('about/', views.about, name='about'),
   # path('contact/', views.contact, name='contact'),
   # path('services/', views.services, name='services'),
   # path('blog/', views.blog, name='blog'),
    #path('blog/<int:post_id>/', views.blog_detail, name='blog_detail'),
]