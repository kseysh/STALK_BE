from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):

    def create_user(self, username, **extra_fields):
        if not username:
            raise ValueError(_('The username must be set'))
        user = self.model(username=username, **extra_fields)
        user.set_password("temp_password")
        user.save()
        return user

    def create_superuser(self, username, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(username, **extra_fields)


class User(AbstractUser):
    username = models.CharField(verbose_name='유저 아이디',max_length=64,unique=True)
    user_email = models.EmailField(verbose_name= "유저 이메일",max_length=255,blank=True)
    user_property = models.IntegerField(verbose_name= "유저 자산",default=0)
    user_nickname = models.CharField(verbose_name="유저 닉네임",max_length=32)
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.username