from django import forms
from .models import Usuario, RegistroAcceso

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = [
            'numero_documento', 'tipo_documento', 'nombres', 'apellidos',
            'email', 'telefono', 'estado'
        ]
        widgets = {
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el número de documento'
            }),
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'nombres': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese los nombres'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese los apellidos'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ejemplo@correo.com'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono (opcional)'
            }),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'numero_documento': 'Número de Documento',
            'tipo_documento': 'Tipo de Documento',
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'email': 'Correo Electrónico',
            'telefono': 'Teléfono',
            'estado': 'Estado',
        }
    
    def clean_numero_documento(self):
        numero_documento = self.cleaned_data['numero_documento']
        if not numero_documento.replace(' ', '').isdigit():
            raise forms.ValidationError('El número de documento debe contener solo números.')
        return numero_documento.replace(' ', '')
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email=email).exclude(numero_documento=self.instance.numero_documento if self.instance else None).exists():
            raise forms.ValidationError('Ya existe un usuario con este correo electrónico.')
        return email

class RegistroAccesoForm(forms.ModelForm):
    class Meta:
        model = RegistroAcceso
        fields = ['usuario', 'tipo_acceso', 'observaciones']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'tipo_acceso': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Observaciones adicionales (opcional)'
            }),
        }
        labels = {
            'usuario': 'Usuario',
            'tipo_acceso': 'Tipo de Acceso',
            'observaciones': 'Observaciones',
        }

# Formulario de búsqueda para filtrar usuarios
class BuscarUsuarioForm(forms.Form):
    buscar = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre, apellido o documento...'
        })
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos')] + Usuario.ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegistroPersonalForm(UserCreationForm):
    first_name = forms.CharField(label="Nombres", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Apellidos", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label="Correo Electrónico", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user