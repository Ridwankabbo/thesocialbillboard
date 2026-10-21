from django.db import models


PRODUCT_CATEGORY_CHOICES=[
    ('creator_camera', 'Creator Camera'),
    ('creator_microphone', 'Creator Microphone'),
    ('streaming_tools', 'Streaming Tools'),
    ('creator_lens', 'Creator Lens'),
    ('creator_tripod', 'Creator Tripod'),
    ('creator_light', 'Creator Light'),
    ('creator_backdrop', 'Creator Backdrop'),
    ('creator_gimbal', 'Creator Gimbal'),
    ('creator_other', 'Creator Other'),
]

class CreatorProduct(models.Model):
    name=models.CharField(max_length=255)
    catagory=models.CharField(max_length=255,choices=PRODUCT_CATEGORY_CHOICES)
    product_slogan=models.CharField(max_length=255)
    description=models.TextField()
    subtitle=models.CharField(max_length=255)
    product_image=models.ImageField(upload_to='creator_product_images/')
    product_price=models.DecimalField(max_digits=10, decimal_places=2)
    buy_link=models.URLField(max_length=255, blank=True, null=True)


    def __str__(self):
        return self.name
    
