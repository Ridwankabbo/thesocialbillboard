from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()


class Subscription(models.Model):
    # PACKAGE_CHOICES = [("package-1", "Package 1"), ("package-2", "Package 2")]
    BILLING_CHOICES = [("monthly", "Monthly"), ("yearly", "Yearly")]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=255)
    stripe_subscription_id = models.CharField(max_length=255)
    package = models.CharField(max_length=200)
    billing_interval = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return self.user.email + " - " + self.package + " (" + self.billing_interval + ")"


class SubscriptionPlan(models.Model):
    USER_TYPE_CHOICES = [
        ('parent', 'Parent'),
        ('creator', 'Creator'),
    ]
    INTERVAL_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    name = models.CharField(
        max_length=50, 
        help_text="Plan name/slug (e.g., 'package-1')"
    )
    display_name = models.CharField(max_length=100)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in GBP (£)")
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES)
    features = models.JSONField(blank=True, help_text="Enter features in JSON format")
    
    stripe_product_id = models.CharField(max_length=255, blank=True, help_text="Stripe Product ID (auto-generated)")
    stripe_price_id = models.CharField(max_length=255, blank=True, help_text="Stripe Price ID (auto-generated)")
    success_url = models.CharField(max_length=512, blank=True, null=True, help_text="Custom redirect URL on successful checkout")
    cancel_url = models.CharField(max_length=512, blank=True, null=True, help_text="Custom redirect URL on cancelled checkout")

    class Meta:
        unique_together = ('name', 'interval')

    def __str__(self):
        return f"{self.display_name} - {self.interval.capitalize()} ({self.user_type.capitalize()})"

    @property
    def features_list(self):
        if not self.features:
            return []
        if isinstance(self.features, list):
            return self.features
        if isinstance(self.features, str):
            import json
            try:
                parsed = json.loads(self.features)
                if isinstance(parsed, list):
                    return parsed
            except:
                pass
            return [f.strip() for f in self.features.split("\n") if f.strip()]
        return []

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        price_changed = False

        if not is_new:
            old_instance = SubscriptionPlan.objects.get(pk=self.pk)
            if (old_instance.price != self.price or 
                old_instance.interval != self.interval or 
                old_instance.display_name != self.display_name):
                price_changed = True

        # Sync with Stripe if new, price changed, or Stripe Price ID is missing
        if (is_new or price_changed or not self.stripe_price_id) and self.price > 0:
            import stripe
            from django.conf import settings
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # 1. Handle Stripe Product
            if not self.stripe_product_id:
                try:
                    product = stripe.Product.create(
                        name=f"{self.display_name} ({self.user_type.capitalize()})",
                        description=f"Subscription plan for {self.user_type}"
                    )
                    self.stripe_product_id = product.id
                except Exception as e:
                    print(f"Error creating Stripe product: {e}")

            # 2. Handle Stripe Price
            if self.stripe_product_id:
                stripe_interval = "month" if self.interval == "monthly" else "year"
                try:
                    price_obj = stripe.Price.create(
                        unit_amount=int(self.price * 100),
                        currency="gbp",
                        recurring={"interval": stripe_interval},
                        product=self.stripe_product_id,
                    )
                    
                    # Archive old Stripe Price if present
                    if self.stripe_price_id:
                        try:
                            stripe.Price.modify(self.stripe_price_id, active=False)
                        except Exception as e:
                            print(f"Error archiving old Stripe price: {e}")
                    
                    self.stripe_price_id = price_obj.id
                except Exception as e:
                    print(f"Error creating Stripe price: {e}")

        super().save(*args, **kwargs)
