from django.contrib import admin

from apps.blog.models import Post, Category, Tag, Comment


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Category, Tag)
class SlugAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(Comment)