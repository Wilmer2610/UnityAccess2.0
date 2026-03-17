from django.test import TestCase
from django.urls import reverse
from django.core import signing

from .models import Usuario


class QrPublicoTests(TestCase):
    def test_qr_publico_png_ok(self):
        u = Usuario.objects.create(
            numero_documento='123456',
            tipo_documento='CC',
            nombres='Ana',
            apellidos='Perez',
            email='ana@example.com',
            estado='activo',
        )
        token = signing.dumps({'id': u.id}, salt='qr_usuario_publico')
        url = reverse('appi:qr_usuario_publico', kwargs={'token': token})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get('Content-Type'), 'image/png')
        self.assertTrue(resp.content.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_qr_publico_png_token_invalido(self):
        url = reverse('appi:qr_usuario_publico', kwargs={'token': 'invalido'})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)
