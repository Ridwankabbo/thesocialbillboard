from django.db.models.signals import post_save
from django.dispatch import receiver   
from .models import CreatorProfile
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def create_creator_profile(sender, instance, created, **kwargs):
    # Create CreatorProfile if user is being created as creator, or if user_type is updated to creator
    if instance.user_type == 'creator':
        print("User created signal received for user:", instance.name)
        CreatorProfile.objects.get_or_create(user=instance)
    else:
        # Delete CreatorProfile if user_type is changed away from creator
        if not created:  # Only on updates, not on creation
            CreatorProfile.objects.filter(user=instance).delete()