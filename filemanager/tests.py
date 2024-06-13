from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
import os

class TestFileManager(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email='testuser@gmail.com',
            password='password'
        )

    def test_upload_file_access(self):
        response = self.client.post('/filemanager/upload/')
        self.assertEqual(response.status_code, 302)

    def test_upload_file_valid_extenction_file(self):
        self.client.login(email='testuser@gmail.com', password='password')
        valid_file = SimpleUploadedFile('valid_file.geojson', b'{"type": "FeatureCollection", "features": []}')
        response = self.client.post('/filemanager/upload/', {'file': valid_file})
        self.assertRedirects(response, '/filemanager/files/')
        
    def test_upload_file_invalid_extenction_file(self):
        self.client.login(email='testuser@gmail.com', password='password')
        invalid_file = SimpleUploadedFile('invalid_file.txt', b'{"type": "FeatureCollection", "features": []}')
        response = self.client.post('/filemanager/upload/', {'file': invalid_file})
        self.assertEqual(len(response.context['form'].errors['file']), 1)

    def test_upload_file_none_file(self):
        self.client.login(email='testuser@gmail.com', password='password')
        response = self.client.post('/filemanager/upload/', {})
        self.assertEqual(len(response.context['form'].errors['file']), 1)
