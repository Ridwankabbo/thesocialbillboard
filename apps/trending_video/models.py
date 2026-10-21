from django.db import models
from django.utils import timezone

class SmartMatchAiData(models.Model): 
    name = models.CharField(max_length=255, unique=True)  
    data = models.JSONField()
    fetched_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class TopTenUkCreatorsAiData(models.Model):
    name= models.CharField(max_length=255, unique=True)
    data=models.JSONField()
    fetched_at=models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
class SafeChannelCurratedForChild(models.Model):
    name= models.CharField(max_length=255, unique=True)
    data=models.JSONField()
    fetched_at=models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
class ClimbingTheChart(models.Model):
    name= models.CharField(max_length=255, unique=True)
    data=models.JSONField()
    fetched_at=models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
    