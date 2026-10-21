from django.contrib import admin
from .models import BlogPost
from unfold.admin import ModelAdmin
# Register your models here.

# admin.site.register(BlogPost)

#Register Blog Models and auto slug field
class BlogAdmin(ModelAdmin): 
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(BlogPost, BlogAdmin)