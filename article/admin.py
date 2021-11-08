from django.contrib import admin

# Register your models here.

from .models import ArtcilePost,ArticleColumn

admin.site.register(ArtcilePost)
admin.site.register(ArticleColumn)
