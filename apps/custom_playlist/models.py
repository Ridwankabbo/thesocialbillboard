from django.db import models

# Create your models here.

class CustomPlaylist(models.Model):
    class AGE_SELECTION_CHOICES(models.TextChoices):
        AGE_3_5   = '3-5', '3-5'
        AGE_6_8  = '6-8', '6-8'
        AGE_9_11 = '9-11', '9-11'
        AGE_12_14 = '12-14', '12-14'
        AGE_15_16 = '15-16', '15-16'
        AGE_17_18 = '17-18', '17-18'
        
        
    class PLAYLIST_LANGUAGE_CHOICES(models.TextChoices):
        ENGLISH = 'ENGLISH', "English"
        SPANISH = 'SPANISH', 'Spanish'
        FRENCH = 'FRENCH', "FRENCH"
        GERMAN = "GERMAN", "German"
        ARABIC = 'ARABIC', 'Arabic'
        ITALIAN = 'ITALIAN', "Italian"
        OTHERS = 'OTHERS', 'Others'
    class PLAYLIST_TONE_CHOICES(models.TextChoices):
        CALM = 'CALM', "Calm"
        BALANCED = 'BALANCED', 'Balanced'
        HIGH_ENERGY = 'HIGH_ENERGY', 'High_energy'
        
    class TIME_OF_THE_DAY_CHOICES(models.TextChoices):
        MORNING = "MORNING", "Morning"
        AFTER_SCHOOL = "AFTER_SCHOOL", "After_school",
        BED_TIME = 'BED_TIME', 'Bed_time'
        
    class PLAYLIST_LENGTH(models.TextChoices):
        MINITES_40 = '40 MINITES', '40 Minites',
        MINITES_30 = '30 MINITES', '30 Minites',
        MINITES_20 = '20 MINITES', '20 Minites'
        
    name = models.CharField()
    age_group = models.CharField(max_length=10, choices=AGE_SELECTION_CHOICES.choices)
    language = models.CharField(max_length=10, choices=PLAYLIST_LANGUAGE_CHOICES.choices)
    tone = models.CharField(max_length=20, choices=PLAYLIST_TONE_CHOICES.choices)
    time_of_the_day = models.CharField(max_length=50,choices=TIME_OF_THE_DAY_CHOICES.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)
    playlist_length = models.CharField(null=True, blank=True, choices=PLAYLIST_LENGTH.choices)
    playlist_thumbnails = models.ImageField(upload_to='custom_playlist_thumbnails/', null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    
class CustomPlaylistItems(models.Model):
    playlist = models.ForeignKey(CustomPlaylist, on_delete=models.CASCADE, related_name='items')
    item_url = models.URLField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

from django.contrib.auth import get_user_model
User = get_user_model()

class SavedCustomPlaylist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_custom_playlists')
    custom_playlist = models.ForeignKey(CustomPlaylist, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'custom_playlist')

    def __str__(self):
        return f"{self.user} - {self.custom_playlist.name}"
    