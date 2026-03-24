from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Crea o resetea un usuario admin (is_staff, is_superuser) y su contraseña'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--email', default='admin@example.com')
        parser.add_argument('--password', default=None)

    def handle(self, *args, **opts):
        User = get_user_model()
        username = opts['username']
        email = opts['email']
        password = opts['password']

        user = User.objects.filter(username=username).first()
        if user is None:
            if not password:
                raise CommandError('El usuario no existe. Debes pasar --password para crearlo.')
            user = User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Admin creado: {username}'))
        else:
            if password:
                user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            if email:
                user.email = email
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Admin actualizado: {username}'))
