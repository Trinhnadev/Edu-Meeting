from .models import PageView
from django.utils.timezone import now
from . import models
from django.db.models import F
from .models import UserProfile


class PageViewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not request.path.startswith('/ad') and response.status_code == 200:
            url_name = request.resolver_match.url_name if request.resolver_match else None

            if url_name:
                page_view, created = PageView.objects.update_or_create(
                    name=url_name,
                    defaults={'last_viewed': now()}
                )
                
                if not created:
                    PageView.objects.filter(name=url_name).update(views=F('views') + 1)

        return response
