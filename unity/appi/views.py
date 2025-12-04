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
from .forms import UsuarioForm, RegistroAccesoForm, BuscarUsuarioForm
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

def enviar_qr_por_email(request=None, usuario=None):
    try:
        from io import BytesIO
        import qrcode
        img = qrcode.make(usuario.numero_documento)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_url = None
        if request is not None:
            qr_url = request.build_absolute_uri(
                reverse('appi:qr_usuario_png', kwargs={'id': usuario.id})
            )
        body_text = f'Hola {usuario.nombre_completo}, descarga tu código QR: {qr_url if qr_url else ""}'
        body_html = f"""
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

        sg_key = os.getenv('SENDGRID_API_KEY')
        sg_from = os.getenv('SENDGRID_FROM_EMAIL')
        service_url = os.getenv('MAIL_SERVICE_URL', 'http://127.0.0.1:5000/send-qr')
        try:
            import requests
            payload = {
                'email': usuario.email,
                'name': usuario.nombre_completo,
                'documento': usuario.numero_documento,
                'subject': 'Código QR de acceso',
                'text': body_text,
                'html': body_html,
                'qr_png_base64': base64.b64encode(buffer.getvalue()).decode('ascii')
            }
            resp = requests.post(service_url, json=payload, timeout=10)
            if 200 <= resp.status_code < 300 and resp.json().get('ok'):
                if request is not None:
                    messages.success(request, f'Correo enviado vía servicio a {usuario.email}.')
                return True
        except Exception:
            pass
        if sg_key and sg_from:
            try:
                import requests
                payload = {
                    'personalizations': [
                        {
                            'to': [{'email': usuario.email}],
                            'subject': 'Código QR de acceso'
                        }
                    ],
                    'from': {'email': sg_from},
                    'content': [
                        {'type': 'text/plain', 'value': body_text},
                        {'type': 'text/html', 'value': body_html}
                    ],
                    'attachments': [
                        {
                            'content': base64.b64encode(buffer.getvalue()).decode('ascii'),
                            'filename': f'qr_{usuario.numero_documento}.png',
                            'type': 'image/png'
                        }
                    ]
                }
                headers = {
                    'Authorization': f'Bearer {sg_key}',
                    'Content-Type': 'application/json'
                }
                resp = requests.post('https://api.sendgrid.com/v3/mail/send', headers=headers, data=json.dumps(payload), timeout=10)
                if 200 <= resp.status_code < 300:
                    if request is not None:
                        messages.success(request, f'Correo enviado por SendGrid a {usuario.email}.')
                    return True
                else:
                    if request is not None:
                        messages.error(request, f'SendGrid no aceptó el envío ({resp.status_code}). {resp.text[:200]}')
            except Exception:
                if request is not None:
                    messages.error(request, 'Error al enviar con SendGrid.')

        try:
            host = os.getenv('SMTP_HOST')
            port = int(os.getenv('SMTP_PORT', '587'))
            user = os.getenv('SMTP_USER')
            password = os.getenv('SMTP_PASSWORD')
            use_tls = os.getenv('SMTP_USE_TLS', '1').lower() in ['1', 'true', 'yes']
            if host and user and password:
                msg = SMTPEmailMessage()
                msg['Subject'] = 'Código QR de acceso'
                msg['From'] = user
                msg['To'] = usuario.email
                msg.set_content(body_text)
                msg.add_alternative(body_html, subtype='html')
                msg.add_attachment(buffer.getvalue(), maintype='image', subtype='png', filename=f'qr_{usuario.numero_documento}.png')
                with smtplib.SMTP(host, port, timeout=15) as smtp:
                    if use_tls:
                        smtp.starttls()
                    smtp.login(user, password)
                    smtp.send_message(msg)
                if request is not None:
                    messages.success(request, f'Correo enviado por SMTP a {usuario.email}.')
                return True
        except Exception:
            if request is not None:
                messages.error(request, 'Fallo envío SMTP. Verifica variables SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS.')

        email = EmailMessage(
            subject='Código QR de acceso',
            body=body_text,
            to=[usuario.email]
        )
        email.attach(f'qr_{usuario.numero_documento}.png', buffer.getvalue(), 'image/png')
        email.send(fail_silently=True)
        if request is not None:
            messages.warning(request, 'No hay proveedor configurado. Se usó backend local de desarrollo.')
        return False
    except Exception:
        try:
            email = EmailMessage(
                subject='Código QR de acceso',
                body=f'Hola {usuario.nombre_completo}, no fue posible adjuntar el QR. Usa tu documento {usuario.numero_documento} para generar el código en el sistema.',
                to=[usuario.email]
            )
            email.send(fail_silently=True)
        finally:
            if request is not None:
                messages.error(request, 'Fallo al generar o enviar el QR por correo.')
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
@user_passes_test(es_administrador)
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

# Vista principal (home)
def home_view(request):
    if request.user.is_authenticated:
        return redirect('appi:dashboard')
    return render(request, 'home.html')

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
    dest = request.GET.get('dest') or request.user.email
    sg_key = os.getenv('SENDGRID_API_KEY')
    sg_from = os.getenv('SENDGRID_FROM_EMAIL')
    if sg_key and sg_from:
        try:
            import requests
            payload = {
                'personalizations': [
                    {
                        'to': [{'email': dest}],
                        'subject': 'Prueba SendGrid'
                    }
                ],
                'from': {'email': sg_from},
                'content': [{'type': 'text/plain', 'value': 'Correo de prueba SendGrid desde UnityAccess'}]
            }
            headers = {
                'Authorization': f'Bearer {sg_key}',
                'Content-Type': 'application/json'
            }
            resp = requests.post('https://api.sendgrid.com/v3/mail/send', headers=headers, data=json.dumps(payload), timeout=10)
            return JsonResponse({'ok': 200 <= resp.status_code < 300, 'status': resp.status_code, 'body': resp.text[:200], 'provider': 'sendgrid'})
        except Exception as e:
            return JsonResponse({'ok': False, 'message': str(e), 'provider': 'sendgrid'})
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', '587'))
    user = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASSWORD')
    use_tls = os.getenv('SMTP_USE_TLS', '1').lower() in ['1', 'true', 'yes']
    detail = {
        'dest': dest,
        'host': host,
        'port': port,
        'user': user,
        'use_tls': use_tls,
        'provider': 'smtp'
    }
    try:
        if not all([dest, host, user, password]):
            return JsonResponse({'ok': False, 'message': 'Variables SMTP incompletas', 'detail': detail})
        msg = SMTPEmailMessage()
        msg['Subject'] = 'Prueba SMTP'
        msg['From'] = user
        msg['To'] = dest
        msg.set_content('Correo de prueba SMTP desde UnityAccess')
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
        return JsonResponse({'ok': True, 'message': 'Correo de prueba enviado', 'detail': detail})
    except Exception as e:
        return JsonResponse({'ok': False, 'message': str(e), 'detail': detail})

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
        pdf.setFillColor(colors.HexColor('#e5e7eb'))
        pdf.setFont('Helvetica', 9)
        pdf.drawRightString(width - 25, height - 20, timezone.now().strftime('%d/%m/%Y %H:%M'))

    def table_header(y):
        pdf.setFillColor(colors.HexColor('#1f2937'))
        pdf.roundRect(25, y - 22, width - 50, 24, 6, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica-Bold', 11)
        pdf.drawString(35, y - 16, 'Semana')
        pdf.drawString(160, y - 16, 'Entradas')
        pdf.drawString(250, y - 16, 'Salidas')
        pdf.drawString(340, y - 16, 'Total')

    def table_row(y, semana_label, entradas, salidas):
        pdf.setFillColor(colors.HexColor('#111827'))
        pdf.roundRect(25, y - 20, width - 50, 22, 6, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor('#e5e7eb'))
        pdf.setFont('Helvetica', 10)
        pdf.drawString(35, y - 14, semana_label)
        pdf.setFillColor(colors.HexColor('#34d399'))
        pdf.drawString(160, y - 14, str(entradas))
        pdf.setFillColor(colors.HexColor('#fbbf24'))
        pdf.drawString(250, y - 14, str(salidas))
        pdf.setFillColor(colors.HexColor('#93c5fd'))
        pdf.drawString(340, y - 14, str(entradas + salidas))

    header()

    y = height - 110
    pdf.setFillColor(colors.HexColor('#374151'))
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(25, y, 'Resumen semanal de entradas y salidas')
    y -= 10
    table_header(y)
    y -= 30

    semanas = {}
    for a in accesos:
        iso = a.fecha_hora.isocalendar()
        key = (iso.year, iso.week)
        if key not in semanas:
            semanas[key] = {'entradas': 0, 'salidas': 0}
        if a.tipo_acceso == 'entrada':
            semanas[key]['entradas'] += 1
        else:
            semanas[key]['salidas'] += 1

    ordenadas = sorted(semanas.items(), key=lambda x: (x[0][0], x[0][1]))
    for (year, week), data in ordenadas:
        label = f'Semana {week} - {year}'
        table_row(y, label, data['entradas'], data['salidas'])
        y -= 26
        if y < 80:
            pdf.showPage()
            header()
            y = height - 110
            pdf.setFillColor(colors.HexColor('#374151'))
            pdf.setFont('Helvetica-Bold', 12)
            pdf.drawString(25, y, 'Resumen semanal de entradas y salidas')
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
        count = RegistroAcceso.objects.filter(fecha_hora__date=fecha).count()
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
