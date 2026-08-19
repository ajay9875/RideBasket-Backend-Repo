from django.contrib import admin
from django.urls import include, path

from rides.views import home_view

urlpatterns = [
    path('', home_view),
    path('admin/', admin.site.urls),
    path('api/', include('rides.urls')),
]