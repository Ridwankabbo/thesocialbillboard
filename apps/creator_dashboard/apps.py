from django.apps import AppConfig


class CreatorDashboardConfig(AppConfig):
    name = 'apps.creator_dashboard'

    def ready(self):
        import apps.creator_dashboard.signals