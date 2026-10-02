from enum import unique

from django.contrib.auth.base_user import BaseUserManager
from django.db.models import BooleanField, EmailField

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db.models.fields import CharField


class BlogUserManager(BaseUserManager['BlogUser']):
    def create_user(self, email: str, password: str | None, **extra_fields) -> 'BlogUser':
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None, **extra_fields) -> 'BlogUser':
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not extra_fields.get('is_staff') or not extra_fields.get('is_superuser'):
            raise ValueError('Superuser must have is_staff, is_superuser and is_active')
        return self.create_user(email, password, **extra_fields)

class BlogUser(AbstractBaseUser, PermissionsMixin):
    objects = BlogUserManager()
    email = EmailField(unique=True)
    first_name = CharField(max_length=50)
    last_name = CharField(max_length=50)
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email



