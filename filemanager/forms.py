from django import forms
from .models import UploadedFile
from django.contrib.auth import get_user_model


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file']

User = get_user_model()

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'image', 'description', 'department']
        widgets = {
            'email': forms.EmailInput(attrs={'readonly': 'readonly'}),
        }
