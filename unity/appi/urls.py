from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'appi'

urlpatterns = [
    # Página principal - Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # CRUD Usuarios
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:id>/', views.detalle_usuario, name='detalle_usuario'),
    path('usuarios/<int:id>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:id>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
    path('usuarios/<int:id>/enviar-qr/', views.enviar_qr_usuario, name='enviar_qr_usuario'),
    path('usuarios/<int:id>/qr.png', views.qr_usuario_png, name='qr_usuario_png'),
    path('correo/test/', views.probar_correo, name='probar_correo'),
    
    # CRUD Registros de Acceso
    path('accesos/', views.lista_accesos, name='lista_accesos'),
    path('accesos/crear/', views.crear_acceso, name='crear_acceso'),
    path('accesos/usuarios/', views.accesos_por_usuario, name='accesos_por_usuario'),
    path('accesos/usuarios/<str:numero_documento>/pdf/', views.informe_usuario_pdf, name='informe_usuario_pdf'),
    
    # Control de Acceso QR
    path('control-qr/', views.control_qr, name='control_qr'),
    path('api/verificar-qr/', views.api_verificar_qr, name='api_verificar_qr'),
    
    # API para estadísticas
    path('api/estadisticas/', views.api_estadisticas_dashboard, name='estadisticas_api'),

    # Cambiar contraseña (usuario logueado)
    path(
        "registration/password_change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change.html",
            success_url=reverse_lazy("appi:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "registration/password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),

    # Solicitud de reset (usuario no logueado)
    path(
        "registration/password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset.html",
            success_url=reverse_lazy("appi:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "registration/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),

    # Link que llega por email
    path(
        "registration/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("appi:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "registration/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
