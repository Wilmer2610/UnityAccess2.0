from django.db import models
from django.utils import timezone

# Modelo simplificado de Usuario para CRUD básico
class Usuario(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('CC', 'Cédula de Ciudadanía'),
        ('TI', 'Tarjeta de Identidad'),
        ('CE', 'Cédula de Extranjería'),
        ('PP', 'Pasaporte'),
    ]
    
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    ]
    
    numero_documento = models.CharField(max_length=20, unique=True, verbose_name="Número de Documento")
    tipo_documento = models.CharField(max_length=2, choices=TIPO_DOCUMENTO_CHOICES, default='CC', verbose_name="Tipo de Documento")
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    email = models.EmailField(verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo', verbose_name="Estado")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ['apellidos', 'nombres']
    
    def __str__(self):
        return f"{self.nombres} {self.apellidos} - {self.numero_documento}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

# Modelo simplificado de Registro de Acceso
class RegistroAcceso(models.Model):
    TIPO_ACCESO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
    ]
    
    usuario = models.ForeignKey(Usuario, to_field='numero_documento', on_delete=models.CASCADE, verbose_name="Usuario")
    fecha_hora = models.DateTimeField(default=timezone.now, verbose_name="Fecha y Hora")
    tipo_acceso = models.CharField(max_length=10, choices=TIPO_ACCESO_CHOICES, verbose_name="Tipo de Acceso")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    class Meta:
        verbose_name = "Registro de Acceso"
        verbose_name_plural = "Registros de Acceso"
        ordering = ['-fecha_hora']
    
    def __str__(self):
        return f"{self.usuario.nombre_completo} - {self.tipo_acceso} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
     

    