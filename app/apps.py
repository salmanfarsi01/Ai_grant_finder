from django.apps import AppConfig
from django.conf import settings

from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        print("preparing app")
        from .models import SiteConfig
        from . import signals
        try:
            settings.SITE_CONFIG = SiteConfig.objects.first()
        except Exception as e:
            print(f"Warning: Could not load SiteConfig during app initialization: {e}")
            settings.SITE_CONFIG = None
        # Small safeguard: clear any stale DatasetUpload.upload_in_progress flags
        try:
            from .models import DatasetUpload
            from django.utils import timezone
            # If any uploads were marked in-progress but never completed, clear only those that are stale.
            # This avoids touching active uploads started just before a restart.
            now = timezone.now()
            stale_qs = DatasetUpload.objects.filter(upload_in_progress=True, updated_at__lt=now - timezone.timedelta(minutes=10))
            if stale_qs.exists():
                for ds in stale_qs:
                    ds.upload_in_progress = False
                    ds.upload_status = DatasetUpload.UPLOAD_STATUS_FAILED
                    ds.upload_error_message = (
                        "Upload interrupted (server restart). Please retry from admin."
                    )
                    ds.save()
                print(f"Recovered {stale_qs.count()} stale DatasetUpload records and marked them failed")
        except Exception:
            # don't raise during startup; migrations or DB may not be ready
            pass

    # def post_ready_callback(self, sender, **kwargs):
