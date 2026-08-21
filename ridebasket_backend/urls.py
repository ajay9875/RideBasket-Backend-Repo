from django.contrib import admin
from django.urls import include, path

from Driver.views import home_view

urlpatterns = [
    path('', home_view),
    path('admin/', admin.site.urls),
    path('api/', include('Driver.urls')),
    path('api/', include('Customer.urls')),
]