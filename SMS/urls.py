from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("", TemplateView.as_view(template_name="accounts/index.html"), name="index"),
    path('django-admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('company/', include('company.urls')),
    path('accounts/', include('accounts.urls')),
    path('inventory/', include('inventory.urls')),
    path('notifications/', include('notifications.urls')),

    path('training/', include('training.urls')),
    path('staff/', include('training.staff_urls')),

    path('logistics/', include('logistics.urls')),
]

# Media files serving in development and production
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]