from django.urls import path

from . import views

urlpatterns = [
    path('entries/', views.entries, name='entries'),
    path('entries/start/', views.start, name='entry_start'),
    path('entries/stop/', views.stop, name='entry_stop'),
    path('reports/', views.report, name='report'),
]
