from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Rol, Usuario

"""
Serializadores para gestión de usuarios, roles y generación de tokens JWT.
"""





class RolSerializer(serializers.ModelSerializer):
    """Serializador para lectura y listado de roles."""

    class Meta:
        model = Rol
        fields = ['id_rol', 'nombre_rol']


class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializador para creación y lectura de usuarios.
    Garantiza el hasheo de contraseñas y ocultamiento en respuestas HTTP.
    """
    nombre_rol = serializers.CharField(source='rol.nombre_rol', read_only=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = Usuario
        fields = [
            'id_usuario',
            'username',
            'rut',
            'first_name',
            'last_name',
            'email',
            'password',
            'rol',
            'nombre_rol',
            'estado_activo',
        ]
        extra_kwargs = {
            'rol': {'required': True, 'allow_null': False}
        }

    def create(self, validated_data: dict) -> Usuario:
        """Encripta la contraseña utilizando el hasher configurado antes de guardar."""
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def validate_rol(self, rol: Rol) -> Rol:
        """Evita escalada de privilegios por parte del perfil Administración."""
        request = self.context.get('request')
        if request and request.user.is_authenticated and not request.user.is_superuser:
            es_solo_administracion = (
                request.user.rol
                and request.user.rol.nombre_rol == Rol.ADMINISTRACION
            )
            if es_solo_administracion and rol.nombre_rol == Rol.ADMIN_GENERAL:
                raise serializers.ValidationError(
                    "El perfil Administración no puede asignar el rol Administrador General."
                )
        return rol

    def update(self, instance: Usuario, validated_data: dict) -> Usuario:
        """Encripta la contraseña si es actualizada en una petición PUT/PATCH."""
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializador JWT personalizado.
    Inyecta claims de rol y RUT directamente en el payload del token y en la respuesta.
    """

    @classmethod
    def get_token(cls, user: Usuario):
        token = super().get_token(user)
        token['rut'] = user.rut
        token['id_rol'] = user.rol.id_rol if user.rol else None
        token['nombre_rol'] = user.rol.nombre_rol if user.rol else None
        return token

    def validate(self, attrs: dict) -> dict:
        data = super().validate(attrs)
        data['id_usuario'] = self.user.id_usuario
        data['rut'] = self.user.rut
        data['id_rol'] = self.user.rol.id_rol if self.user.rol else None
        data['nombre_rol'] = self.user.rol.nombre_rol if self.user.rol else None
        return data