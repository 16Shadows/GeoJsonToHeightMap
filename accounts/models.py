# accounts/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Profile(models.Model):
    """ Profile model to represent user profiles """

    USER_TYPE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(_('User type'), max_length=20, choices=USER_TYPE_CHOICES)

    def __str__(self):
        return f"{self.user.email}'s Profile"
