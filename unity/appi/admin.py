from django.contrib import admin
from .models import Usuario, RegistroAcceso

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ['numero_documento', 'nombres', 'apellidos', 'email', 'telefono', 'estado', 'fecha_registro']
    list_filter = ['estado', 'tipo_documento', 'fecha_registro']
    search_fields = ['numero_documento', 'nombres', 'apellidos', 'email']
    readonly_fields = ['fecha_registro', 'fecha_actualizacion']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('numero_documento', 'tipo_documento', 'nombres', 'apellidos')
        }),
        ('Contacto', {
            'fields': ('email', 'telefono')
        }),
        ('Estado y Fechas', {
            'fields': ('estado', 'fecha_registro', 'fecha_actualizacion')
        }),
    )

@admin.register(RegistroAcceso)
class RegistroAccesoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'fecha_hora', 'tipo_acceso', 'observaciones']
    list_filter = ['tipo_acceso', 'fecha_hora']
    search_fields = ['usuario__nombres', 'usuario__apellidos', 'usuario__numero_documento']
    readonly_fields = ['fecha_hora']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario')
