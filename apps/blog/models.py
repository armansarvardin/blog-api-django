from django.db.models import CharField, TextChoices
from django.db.models.base import Model
from django.db.models.deletion import CASCADE, SET_NULL
from django.db.models.fields import SlugField, TextField, DateField, DateTimeField
from django.db.models.fields.related import ForeignKey, ManyToManyField

from apps.auths.models import BlogUser


class Category(Model):
    name = CharField(max_length=50)
    slug = SlugField(unique=True)

class Tag(Model):
    name = CharField(max_length=50)
    slug = SlugField(unique=True)

class Post(Model):
    class Status(TextChoices):
        DRAFT = 'draft'
        PUBLISHED = 'published'
    author = ForeignKey(BlogUser, on_delete=CASCADE)
    title = CharField(max_length=200)
    slug = SlugField(unique=True)
    body = TextField()
    category = ForeignKey(Category, on_delete=SET_NULL, null=True)
    tags = ManyToManyField(Tag)
    status = CharField(choices=Status.choices, default=Status.DRAFT)
    created_at = DateTimeField(auto_now=True)
    updated_at = DateTimeField(auto_now=True)

class Comment(Model):
    post = ForeignKey(Post, on_delete=CASCADE)
    author = ForeignKey(BlogUser, on_delete=CASCADE)
    body = TextField()
    created_at = DateTimeField(auto_now=True)