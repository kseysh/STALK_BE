from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, user_id, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not user_id:
            raise ValueError(_('The username must be set'))
        user = self.model(user_id=user_id, **extra_fields)
        user.set_password("temp_password")
        user.save()
        return user

    def create_superuser(self, user_id, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(user_id, **extra_fields)


class User(AbstractUser):
    user_email = models.EmailField(verbose_name= "유저 이메일",max_length=255,blank=True)
    user_property = models.IntegerField(verbose_name= "유저 자산",default=0)
    user_nickname = models.CharField(verbose_name="유저 닉네임",max_length=32)
    user_id = models.CharField(verbose_name="유저 아이디",max_length=255,unique=True)
    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email