from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import never_cache
import json
from .models import Usuario, RegistroAcceso
from .forms import UsuarioForm, RegistroAccesoForm, BuscarUsuarioForm, RegistroPersonalForm
from django.contrib.auth.models import Group
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import mm
from django.contrib.staticfiles import finders
from django.core.mail import EmailMessage
from django.conf import settings
from django.urls import reverse
import os
import smtplib
from email.message import EmailMessage as SMTPEmailMessage
import base64

# Verificar si el usuario es administrador
def es_administrador(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)

# Verificar si el usuario es vigilante
def es_vigilante(user):
    return user.is_authenticated and user.groups.filter(name='Vigilantes').exists()

# Verificar si es personal autorizado (Admin o Vigilante)
def es_autorizado(user):
    return es_administrador(user) or es_vigilante(user)

@never_cache
@login_required
@user_passes_test(es_administrador)
def crear_personal(request):
    """Vista para crear usuarios del sistema (Vigilantes)"""
    if request.method == 'POST':
        form = RegistroPersonalForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Asignar grupo Vigilantes
            grupo_vigilantes, created = Group.objects.get_or_create(name='Vigilantes')
            user.groups.add(grupo_vigilantes)
            messages.success(request, f'Vigilante {user.username} creado exitosamente.')
            return redirect('appi:dashboard')
        else:
            messages.error(request, 'Error al crear el usuario. Verifique los datos.')
    else:
        form = RegistroPersonalForm()
    
    return render(request, 'usuarios/crear_personal.html', {'form': form})

def enviar_qr_por_email(request=None, usuario=None):
    try:
        from io import BytesIO
        import qrcode
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings
        
        img = qrcode.make(usuario.numero_documento)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_image = buffer.getvalue()
        
        qr_url = None
        if request is not None:
            qr_url = request.build_absolute_uri(
                reverse('appi:qr_usuario_png', kwargs={'id': usuario.id})
            )
        
        subject = 'UnityAccess – Tu Código QR de Acceso'
        text_content = f'Hola {usuario.nombre_completo}, tu número de documento es {usuario.numero_documento}. Puedes descargar tu código QR aquí: {qr_url if qr_url else ""}'
        
        html_content = f"""
        <div style='font-family: Inter, Arial, sans-serif; background:#0f172a; padding:20px; color:#e5e7eb;'>
            <div style='max-width:600px; margin:auto; background:#111827; border-radius:12px; overflow:hidden;'>
                <div style='background:linear-gradient(135deg,#3b82f6,#06b6d4); padding:16px 20px; color:white;'>
                    <h2 style='margin:0;'>UnityAccess – Código QR de Acceso</h2>
                    <div style='opacity:.85; font-size:14px;'>Se adjunta tu código y enlace de descarga</div>
                </div>
                <div style='padding:20px;'>
                    <p>Hola <strong>{usuario.nombre_completo}</strong>,</p>
                    <p>Tu número de documento: <strong>{usuario.numero_documento}</strong></p>
                    <p>
                        Puedes descargar el código QR desde:
                        <a href='{qr_url if qr_url else ''}' style='color:#60a5fa;'>Descargar QR</a>
                    </p>
                    <p style='font-size:12px; color:#9ca3af;'>Si no ves la imagen, usa el enlace de descarga.</p>
                </div>
            </div>
        </div>
        """

        msg = EmailMultiAlternatives(
            subject, 
            text_content, 
            settings.DEFAULT_FROM_EMAIL, 
            [usuario.email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Adjuntar el código QR como imagen
        msg.attach('codigo_qr.png', qr_image, 'image/png')
        
        msg.send()
        
        if request is not None:
            messages.success(request, f'Correo con QR enviado a {usuario.email}.')
        return True
        
    except Exception as e:
        if request is not None:
            messages.warning(request, f'No se pudo enviar el correo: {str(e)}')
        return False

# Vista de login
def login_view(request):
    if request.user.is_authenticated:
        return redirect('appi:dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido {username}!')
                return redirect('appi:dashboard')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Error en el formulario.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

# Vista de logout
def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('appi:login')

# Dashboard principal
@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_autorizado)
def dashboard_view(request):
    # Estadísticas básicas
    total_usuarios = Usuario.objects.count()
    usuarios_activos = Usuario.objects.filter(estado='activo').count()
    total_accesos_hoy = RegistroAcceso.objects.filter(
        fecha_hora__date=timezone.now().date()
    ).count()
    
    # Últimos registros de acceso
    ultimos_accesos = RegistroAcceso.objects.select_related('usuario').order_by('-fecha_hora')[:5]
    
    context = {
        'total_usuarios': total_usuarios,
        'usuarios_activos': usuarios_activos,
        'total_accesos_hoy': total_accesos_hoy,
        'ultimos_accesos': ultimos_accesos,
    }
    return render(request, 'appi/dashboard.html', context)

@never_cache
@login_required
@user_passes_test(es_administrador)
def estadisticas_view(request):
    return render(request, 'appi/estadisticas.html')

# Vista principal (home)
def home_view(request):
    if request.user.is_authenticated:
        return redirect('appi:dashboard')
    return render(request, 'home.html')

@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_autorizado)
def registrar_invitado(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            # Aseguramos que el estado sea activo
            usuario.estado = 'activo'
            usuario.save()
            
            # Intentar enviar QR, pero no bloquear si falla
            try:
                enviar_qr_por_email(request, usuario)
            except:
                pass
                
            messages.success(request, f'Invitado {usuario.nombre_completo} registrado exitosamente.')
            return redirect('appi:dashboard')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = UsuarioForm()
    
    return render(request, 'usuarios/registrar_invitado.html', {'form': form})

# CRUD DE USUARIOS

# Listar usuarios
@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def lista_usuarios(request):
    form_buscar = BuscarUsuarioForm(request.GET)
    usuarios = Usuario.objects.all()
    
    # Aplicar filtros de búsqueda
    if form_buscar.is_valid():
        buscar = form_buscar.cleaned_data.get('buscar')
        estado = form_buscar.cleaned_data.get('estado')
        
        if buscar:
            usuarios = usuarios.filter(
                Q(nombres__icontains=buscar) |
                Q(apellidos__icontains=buscar) |
                Q(numero_documento__icontains=buscar) |
                Q(email__icontains=buscar)
            )
        
        if estado:
            usuarios = usuarios.filter(estado=estado)
    
    # Paginación
    paginator = Paginator(usuarios, 5)  # 5 usuarios por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'usuarios': page_obj,
        'form_buscar': form_buscar,
        'total_usuarios': usuarios.count(),
        'is_paginated': page_obj.has_other_pages(),
    }
    return render(request, 'usuarios/lista.html', context)

# Crear usuario
@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            enviar_qr_por_email(request, usuario)
            messages.success(request, f'Usuario {usuario.nombre_completo} creado exitosamente.')
            return redirect('appi:lista_usuarios')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = UsuarioForm()
    
    return render(request, 'usuarios/crear.html', {'form': form})

# Ver detalles de usuario
@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def detalle_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    
    # Últimos accesos del usuario
    accesos = RegistroAcceso.objects.filter(usuario=usuario).order_by('-fecha_hora')[:10]
    
    context = {
        'usuario': usuario,
        'accesos': accesos,
    }
    return render(request, 'usuarios/detalle.html', context)

# Editar usuario
@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def editar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario {usuario.nombre_completo} actualizado exitosamente.')
            return redirect('appi:detalle_usuario', id=usuario.id)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = UsuarioForm(instance=usuario)
    
    context = {
        'form': form,
        'usuario': usuario,
    }
    return render(request, 'usuarios/editar.html', context)

# Eliminar usuario
@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def eliminar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    
    if request.method == 'POST':
        nombre_completo = usuario.nombre_completo
        usuario.delete()
        messages.success(request, f'Usuario {nombre_completo} eliminado exitosamente.')
        return redirect('appi:lista_usuarios')
    
    context = {'usuario': usuario}
    return render(request, 'usuarios/eliminar.html', context)

@never_cache
@login_required
@user_passes_test(es_administrador)
def enviar_qr_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    ok = enviar_qr_por_email(request, usuario)
    if ok:
        messages.success(request, f'Código QR enviado a {usuario.email}.')
    return redirect('appi:detalle_usuario', id=usuario.id)

@never_cache
@login_required
@user_passes_test(es_administrador)
def qr_usuario_png(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    from io import BytesIO
    import qrcode
    img = qrcode.make(usuario.numero_documento)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='image/png')

@never_cache
@login_required
@user_passes_test(es_administrador)
def probar_correo(request):
    try:
        dest = request.GET.get('dest') or request.user.email
        from django.core.mail import send_mail
        from django.conf import settings

        send_mail(
            'Prueba de configuración UnityAccess',
            'Este es un correo de prueba para verificar la configuración de correo en UnityAccess.',
            settings.DEFAULT_FROM_EMAIL,
            [dest],
            fail_silently=False,
        )
        return JsonResponse({
            'ok': True,
            'message': f'Correo enviado exitosamente a {dest} usando la configuración de Django.',
            'provider': settings.EMAIL_BACKEND,
            'email': {
                'host': getattr(settings, 'EMAIL_HOST', None),
                'port': getattr(settings, 'EMAIL_PORT', None),
                'use_tls': getattr(settings, 'EMAIL_USE_TLS', None),
                'host_user': getattr(settings, 'EMAIL_HOST_USER', None),
                'from': getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            }
        })
    except Exception as e:
        try:
            from django.conf import settings
            dest = request.GET.get('dest') or getattr(request.user, 'email', None)
            return JsonResponse({
                'ok': False,
                'message': f'Error al enviar correo: {str(e)}',
                'error_type': e.__class__.__name__,
                'email': {
                    'host': getattr(settings, 'EMAIL_HOST', None),
                    'port': getattr(settings, 'EMAIL_PORT', None),
                    'use_tls': getattr(settings, 'EMAIL_USE_TLS', None),
                    'host_user': getattr(settings, 'EMAIL_HOST_USER', None),
                    'from': getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                    'dest': dest,
                },
                'env': {
                    'SMTP_HOST': bool(os.environ.get('SMTP_HOST')),
                    'SMTP_PORT': bool(os.environ.get('SMTP_PORT')),
                    'SMTP_USE_TLS': bool(os.environ.get('SMTP_USE_TLS')),
                    'SMTP_USER': bool(os.environ.get('SMTP_USER')),
                    'SMTP_PASSWORD': bool(os.environ.get('SMTP_PASSWORD')),
                    'SMTP_FROM_EMAIL': bool(os.environ.get('SMTP_FROM_EMAIL')),
                    'BREVO_API_KEY': bool(os.environ.get('BREVO_API_KEY')),
                }
            }, status=500)
        except Exception as inner:
            return HttpResponse(f'Error interno en probar_correo: {inner}', status=500)

# CRUD DE REGISTROS DE ACCESO

# Listar registros de acceso
@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def lista_accesos(request):
    accesos = RegistroAcceso.objects.select_related('usuario').order_by('-fecha_hora')
    
    # Filtros opcionales
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    tipo_acceso = request.GET.get('tipo_acceso')
    usuario_id = request.GET.get('usuario')
    
    if fecha_desde:
        accesos = accesos.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        accesos = accesos.filter(fecha_hora__date__lte=fecha_hasta)
    if tipo_acceso:
        accesos = accesos.filter(tipo_acceso=tipo_acceso)
    if usuario_id:
        accesos = accesos.filter(usuario__numero_documento=usuario_id)
    
    # Paginación
    paginator = Paginator(accesos, 20)  # 20 registros por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Para el filtro de usuarios
    usuarios = Usuario.objects.filter(estado='activo').order_by('apellidos', 'nombres')
    
    context = {
        'page_obj': page_obj,
        'accesos': page_obj,
        'usuarios': usuarios,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'tipo_acceso': tipo_acceso,
        'usuario_id': usuario_id,
        'total_accesos': accesos.count(),
        'is_paginated': page_obj.has_other_pages(),
        'paginator': paginator,
    }
    return render(request, 'accesos/lista.html', context)

@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def accesos_por_usuario(request):
    usuarios = Usuario.objects.order_by('apellidos', 'nombres')
    resumen = []
    for u in usuarios:
        total = RegistroAcceso.objects.filter(usuario=u).count()
        entradas = RegistroAcceso.objects.filter(usuario=u, tipo_acceso='entrada').count()
        salidas = RegistroAcceso.objects.filter(usuario=u, tipo_acceso='salida').count()
        resumen.append({
            'usuario': u,
            'total': total,
            'entradas': entradas,
            'salidas': salidas,
        })
    return render(request, 'accesos/por_usuario.html', {'resumen': resumen})

@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def informe_usuario_pdf(request, numero_documento):
    usuario = get_object_or_404(Usuario, numero_documento=numero_documento)
    accesos = RegistroAcceso.objects.filter(usuario=usuario).order_by('fecha_hora')
    
    # Filtros de fecha opcionales
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if fecha_desde:
        accesos = accesos.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        accesos = accesos.filter(fecha_hora__date__lte=fecha_hasta)
        
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="informe_{usuario.numero_documento}.pdf"'
    pdf = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    def header():
        pdf.setFillColor(colors.HexColor('#0f172a'))
        pdf.rect(0, height - 80, width, 80, fill=1, stroke=0)
        logo_path = finders.find('imagen/logo.png')
        if logo_path:
            pdf.drawImage(logo_path, 25, height - 75, width=60, height=60, preserveAspectRatio=True, mask='auto')
        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawString(95, height - 45, 'UnityAccess - Informe de Accesos')
        pdf.setFont('Helvetica', 11)
        pdf.drawString(95, height - 62, f'Usuario: {usuario.nombre_completo} ({usuario.numero_documento})')
        if fecha_desde or fecha_hasta:
            rango = f"Periodo: {fecha_desde or 'Inicio'} a {fecha_hasta or 'Fin'}"
            pdf.drawString(95, height - 75, rango)
        pdf.setFillColor(colors.HexColor('#e5e7eb'))
        pdf.setFont('Helvetica', 9)
        pdf.drawRightString(width - 25, height - 20, timezone.now().strftime('%d/%m/%Y %H:%M'))

    def table_header(y):
        pdf.setFillColor(colors.HexColor('#1f2937'))
        pdf.roundRect(25, y - 22, width - 50, 24, 6, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica-Bold', 11)
        pdf.drawString(35, y - 16, 'Fecha')
        pdf.drawString(120, y - 16, 'Hora')
        pdf.drawString(200, y - 16, 'Tipo de Acceso')
        pdf.drawString(320, y - 16, 'Observaciones')

    def table_row(y, fecha, hora, tipo_acceso, observaciones):
        pdf.setFillColor(colors.HexColor('#111827'))
        pdf.roundRect(25, y - 20, width - 50, 22, 6, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor('#e5e7eb'))
        pdf.setFont('Helvetica', 10)
        pdf.drawString(35, y - 14, fecha)
        pdf.drawString(120, y - 14, hora)
        
        # Color según tipo de acceso
        if tipo_acceso == 'entrada':
            pdf.setFillColor(colors.HexColor('#34d399'))  # Verde para entrada
        else:
            pdf.setFillColor(colors.HexColor('#fbbf24'))  # Amarillo para salida
        
        pdf.drawString(200, y - 14, tipo_acceso.title())
        pdf.setFillColor(colors.HexColor('#e5e7eb'))
        
        # Truncar observaciones si son muy largas
        obs_truncado = observaciones[:25] + '...' if len(observaciones) > 25 else observaciones
        pdf.drawString(320, y - 14, obs_truncado)

    header()

    y = height - 110
    pdf.setFillColor(colors.HexColor('#374151'))
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(25, y, 'Registro individual de entradas y salidas')
    y -= 10
    table_header(y)
    y -= 30

    # Mostrar cada acceso individual
    for acceso in accesos:
        fecha = acceso.fecha_hora.strftime('%d/%m/%Y')
        hora = acceso.fecha_hora.strftime('%H:%M')
        tipo_acceso = acceso.tipo_acceso
        observaciones = acceso.observaciones or '-'
        
        table_row(y, fecha, hora, tipo_acceso, observaciones)
        y -= 26
        
        # Nueva página si no hay espacio suficiente
        if y < 80:
            pdf.showPage()
            header()
            y = height - 110
            pdf.setFillColor(colors.HexColor('#374151'))
            pdf.setFont('Helvetica-Bold', 12)
            pdf.drawString(25, y, 'Registro individual de entradas y salidas')
            y -= 10
            table_header(y)
            y -= 30

    pdf.showPage()
    pdf.save()
    return response

@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def informe_general_pdf(request):
    """Genera un informe PDF con todos los registros de acceso según los filtros aplicados"""
    accesos = RegistroAcceso.objects.select_related('usuario').order_by('-fecha_hora')
    
    # Filtros opcionales
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    tipo_acceso = request.GET.get('tipo_acceso')
    usuario_query = request.GET.get('usuario')
    
    if fecha_desde:
        accesos = accesos.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        accesos = accesos.filter(fecha_hora__date__lte=fecha_hasta)
    if tipo_acceso:
        accesos = accesos.filter(tipo_acceso=tipo_acceso)
    if usuario_query:
        accesos = accesos.filter(
            Q(usuario__nombres__icontains=usuario_query) |
            Q(usuario__apellidos__icontains=usuario_query) |
            Q(usuario__numero_documento__icontains=usuario_query)
        )
        
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="informe_general_accesos.pdf"'
    pdf = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    def header():
        pdf.setFillColor(colors.HexColor('#0f172a'))
        pdf.rect(0, height - 80, width, 80, fill=1, stroke=0)
        logo_path = finders.find('imagen/logo.png')
        if logo_path:
            pdf.drawImage(logo_path, 25, height - 75, width=60, height=60, preserveAspectRatio=True, mask='auto')
        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawString(95, height - 45, 'UnityAccess - Informe General de Accesos')
        pdf.setFont('Helvetica', 11)
        pdf.drawString(95, height - 62, 'Historial completo de entradas y salidas')
        
        # Información de filtros en el header
        filtro_text = []
        if fecha_desde or fecha_hasta:
            filtro_text.append(f"Periodo: {fecha_desde or 'Inicio'} a {fecha_hasta or 'Fin'}")
        if tipo_acceso:
            filtro_text.append(f"Tipo: {tipo_acceso}")
        if usuario_query:
            filtro_text.append(f"Usuario: {usuario_query}")
            
        if filtro_text:
            pdf.drawString(95, height - 75, " | ".join(filtro_text))
            
        pdf.setFillColor(colors.HexColor('#e5e7eb'))
        pdf.setFont('Helvetica', 9)
        pdf.drawRightString(width - 25, height - 20, timezone.now().strftime('%d/%m/%Y %H:%M'))

    def table_header(y):
        pdf.setFillColor(colors.HexColor('#1f2937'))
        pdf.roundRect(25, y - 22, width - 50, 24, 6, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(35, y - 16, 'Usuario')
        pdf.drawString(160, y - 16, 'Documento')
        pdf.drawString(250, y - 16, 'Fecha/Hora')
        pdf.drawString(360, y - 16, 'Tipo')
        pdf.drawString(450, y - 16, 'Observaciones')

    def table_row(y, nombre, documento, fecha_hora, tipo, obs):
        pdf.setFillColor(colors.HexColor('#111827'))
        pdf.roundRect(25, y - 20, width - 50, 22, 6, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor('#e5e7eb'))
        pdf.setFont('Helvetica', 9)
        
        # Truncar nombre si es largo
        nombre_trunc = nombre[:20] + '..' if len(nombre) > 20 else nombre
        pdf.drawString(35, y - 14, nombre_trunc)
        pdf.drawString(160, y - 14, documento)
        pdf.drawString(250, y - 14, fecha_hora)
        
        # Color según tipo
        if tipo == 'entrada':
            pdf.setFillColor(colors.HexColor('#34d399'))
        else:
            pdf.setFillColor(colors.HexColor('#fbbf24'))
        
        pdf.drawString(360, y - 14, tipo.title())
        pdf.setFillColor(colors.HexColor('#e5e7eb'))
        
        obs_trunc = (obs or '-')[:15] + '..' if obs and len(obs) > 15 else (obs or '-')
        pdf.drawString(450, y - 14, obs_trunc)

    header()

    y = height - 110
    pdf.setFillColor(colors.HexColor('#374151'))
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(25, y, 'Listado de Registros de Acceso')
    y -= 10
    table_header(y)
    y -= 30

    for acceso in accesos:
        nombre = acceso.usuario.nombre_completo
        doc = acceso.usuario.numero_documento
        fh = acceso.fecha_hora.strftime('%d/%m/%Y %H:%M')
        tipo = acceso.tipo_acceso
        obs = acceso.observaciones
        
        table_row(y, nombre, doc, fh, tipo, obs)
        y -= 26
        
        if y < 80:
            pdf.showPage()
            header()
            y = height - 110
            pdf.setFillColor(colors.HexColor('#374151'))
            pdf.setFont('Helvetica-Bold', 12)
            pdf.drawString(25, y, 'Listado de Registros de Acceso')
            y -= 10
            table_header(y)
            y -= 30

    pdf.showPage()
    pdf.save()
    return response

# Crear registro de acceso manual
@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def crear_acceso(request):
    if request.method == 'POST':
        form = RegistroAccesoForm(request.POST)
        if form.is_valid():
            acceso = form.save()
            messages.success(request, f'Registro de acceso creado para {acceso.usuario.nombre_completo}.')
            return redirect('appi:lista_accesos')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = RegistroAccesoForm()
    
    # Obtener usuarios activos para el formulario
    usuarios = Usuario.objects.filter(estado='activo').order_by('apellidos', 'nombres')
    
    return render(request, 'accesos/crear.html', {
        'form': form,
        'usuarios': usuarios
    })

# API para estadísticas del dashboard
@never_cache
@never_cache
@never_cache
@login_required
@user_passes_test(es_administrador)
def api_estadisticas_dashboard(request):
    hoy = timezone.now().date()
    hace_7_dias = hoy - timedelta(days=7)
    
    # Accesos por día en los últimos 7 días
    accesos_por_dia = []
    for i in range(7):
        fecha = hace_7_dias + timedelta(days=i)
        # Contar usuarios únicos que han ingresado ese día
        count = RegistroAcceso.objects.filter(
            fecha_hora__date=fecha, 
            tipo_acceso='entrada'
        ).values('usuario').distinct().count()
        
        accesos_por_dia.append({
            'fecha': fecha.strftime('%d/%m'),
            'count': count
        })
    
    # Distribución por tipo de acceso
    tipos_acceso = RegistroAcceso.objects.values('tipo_acceso').annotate(
        count=Count('tipo_acceso')
    )
    
    data = {
        'accesos_por_dia': accesos_por_dia,
        'tipos_acceso': list(tipos_acceso),
        'ultimos_accesos': [
            {
                'usuario': f"{a.usuario.nombres} {a.usuario.apellidos}",
                'tipo_acceso': a.get_tipo_acceso_display(),
                'hora': a.fecha_hora.strftime('%H:%M:%S'),
                'fecha': a.fecha_hora.strftime('%d/%m/%Y'),
                'email': a.usuario.email
            } for a in RegistroAcceso.objects.select_related('usuario').order_by('-fecha_hora')[:10]
        ]
    }
    
    return JsonResponse(data)

# Control de Acceso QR - Sin restricciones de administrador
@never_cache
@login_required
@never_cache
@login_required
@never_cache
@login_required
def control_qr(request):
    """Vista para el control de acceso con códigos QR"""
    return render(request, 'control_qr/scanner.html')

@login_required
@login_required
@login_required
@csrf_exempt
def api_verificar_qr(request):
    """API para verificar códigos QR y registrar accesos alternando entrada/salida"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            codigo_qr = data.get('codigo_qr', '').strip()

            if not codigo_qr:
                return JsonResponse({'success': False, 'message': 'Código QR vacío'})

            try:
                usuario = Usuario.objects.get(numero_documento=codigo_qr, estado='activo')

                try:
                    ultimo = RegistroAcceso.objects.filter(usuario=usuario).order_by('-fecha_hora').first()
                    tipo = 'entrada' if (ultimo is None or ultimo.tipo_acceso == 'salida') else 'salida'

                    registro = RegistroAcceso.objects.create(
                        usuario=usuario,
                        tipo_acceso=tipo,
                        fecha_hora=timezone.now(),
                        observaciones='Acceso registrado vía QR'
                    )

                    return JsonResponse({
                        'success': True,
                        'message': f'{tipo.capitalize()} registrada',
                        'usuario': {
                            'nombre_completo': usuario.nombre_completo,
                            'numero_documento': usuario.numero_documento,
                            'email': usuario.email,
                            'tipo_acceso': tipo,
                            'hora': registro.fecha_hora.strftime('%H:%M:%S'),
                            'fecha': registro.fecha_hora.strftime('%d/%m/%Y')
                        }
                    })

                except Exception as db_error:
                    ahora = timezone.now()
                    ultimo = RegistroAcceso.objects.filter(usuario=usuario).order_by('-fecha_hora').first()
                    tipo = 'entrada' if (ultimo is None or ultimo.tipo_acceso == 'salida') else 'salida'
                    return JsonResponse({
                        'success': True,
                        'message': f'{tipo.capitalize()} autorizada (sin registrar: {str(db_error)})',
                        'usuario': {
                            'nombre_completo': usuario.nombre_completo,
                            'numero_documento': usuario.numero_documento,
                            'email': usuario.email,
                            'tipo_acceso': tipo,
                            'hora': ahora.strftime('%H:%M:%S'),
                            'fecha': ahora.strftime('%d/%m/%Y')
                        }
                    })

            except Usuario.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Usuario no registrado o inactivo'})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Datos JSON inválidos'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error interno: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Método no permitido'})
