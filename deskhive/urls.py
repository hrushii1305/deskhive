from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('tickets/', TemplateView.as_view(template_name='tickets.html'), name='tickets-page'),
    path('admin/', admin.site.urls),
    path('api/', include('tickets.urls')),
    path('api/', include('accounts.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('tickets/<int:ticket_id>/', TemplateView.as_view(template_name='ticket_detail.html'), name='ticket-detail-page'),
]