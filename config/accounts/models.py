from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):

    def create_user(self, user_id, **extra_fields):

        if not user_id:
            raise ValueError(_('The user id must be set'))
        user = self.model(user_id=user_id, **extra_fields)
        user.save()
        return user

    def create_superuser(self, user_id, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(user_id, **extra_fields)


class User(AbstractUser):
    user_email = models.EmailField(max_length=255)
    user_id = models.CharField(max_length=50,primary_key=True)
    user_nickname = models.CharField(max_length=20)
    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.user_id