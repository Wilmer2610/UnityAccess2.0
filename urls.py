# ... existing code ...
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def redirect_to_dashboard(request):
    return redirect('appi:dashboard')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('app/', include('appi.urls')),  # Keep this path
    path('', redirect_to_dashboard),
]
# ... existing code ...