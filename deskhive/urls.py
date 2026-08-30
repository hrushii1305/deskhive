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
    path('signup/', TemplateView.as_view(template_name='signup.html'), name='signup-page'),
    path('pending/', TemplateView.as_view(template_name='pending.html'), name='pending-page'),
    path('api/', include('tickets.urls')),
    path('api/', include('organizations.urls')),
    path('api/', include('accounts.urls')),
    path('register-owner/', TemplateView.as_view(template_name='register_owner.html'), name='register-owner-page'),
    path('approvals/', TemplateView.as_view(template_name='approvals.html'), name='approvals-page'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('tickets/<int:ticket_id>/', TemplateView.as_view(template_name='ticket_detail.html'), name='ticket-detail-page'),
]