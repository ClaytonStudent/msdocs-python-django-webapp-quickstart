from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='index'),
    path('hello', views.hello, name='hello'),
    path('stock_value_report/', views.stock_value_report, name='stock_value_report'),
    path('download_file/', views.download_file, name='download_file'),
]