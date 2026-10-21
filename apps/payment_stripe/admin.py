from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Subscription, SubscriptionPlan

@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = ["user", "package", "billing_interval", "is_active", "auto_renew"]

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(ModelAdmin):
    list_display = ["display_name", "name", "user_type", "price", "interval", "stripe_price_id"]
    list_filter = ["user_type", "interval"]