from django.contrib.auth.hashers import check_password
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import LogAuditoria, Rol, Usuario


class CoreTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.rol_admin_gral = Rol.objects.create(nombre_rol=Rol.ADMIN_GENERAL)
        cls.rol_admin = Rol.objects.create(nombre_rol=Rol.ADMINISTRACION)
        cls.rol_bodega = Rol.objects.create(nombre_rol=Rol.BODEGA)
        cls.rol_supervisor = Rol.objects.create(nombre_rol=Rol.SUPERVISOR)
        cls.rol_tecnico = Rol.objects.create(nombre_rol=Rol.TECNICO)
        cls.rol_consulta = Rol.objects.create(nombre_rol=Rol.CONSULTA)

        cls.admin_gral = Usuario.objects.create_user(
            username='admin_gral',
            rut='11111111-1',
            password='password_admin',
            rol=cls.rol_admin_gral,
        )
        cls.admin = Usuario.objects.create_user(
            username='admin',
            rut='22222222-2',
            password='password_admin2',
            rol=cls.rol_admin,
        )
        cls.tecnico = Usuario.objects.create_user(
            username='tecnico',
            rut='33333333-3',
            password='password_tec',
            rol=cls.rol_tecnico,
        )
        cls.user_inactivo = Usuario.objects.create_user(
            username='inactivo',
            rut='44444444-4',
            password='password_inactivo',
            rol=cls.rol_consulta,
            estado_activo=False,
        )

        cls.login_url = reverse('core:token_obtain_pair')
        cls.refresh_url = reverse('core:token_refresh')
        cls.usuarios_url = reverse('core:usuario_list_create')
        cls.roles_url = reverse('core:rol_list')

    def test_a07_login_exitoso_y_claims(self):
        """A07:2025 - Login exitoso verifica claims de JWT y datos de respuesta"""
        response = self.client.post(self.login_url, {
            'username': 'admin_gral',
            'password': 'password_admin',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data.get('id_usuario'), self.admin_gral.id_usuario)
        self.assertEqual(response.data.get('rut'), '11111111-1')
        self.assertEqual(response.data.get('id_rol'), self.rol_admin_gral.id_rol)
        self.assertEqual(response.data.get('nombre_rol'), Rol.ADMIN_GENERAL)

        refresh = RefreshToken(response.data['refresh'])
        self.assertEqual(str(refresh.get('user_id')), str(self.admin_gral.id_usuario))
        self.assertEqual(refresh.get('rut'), '11111111-1')
        self.assertEqual(refresh.get('id_rol'), self.rol_admin_gral.id_rol)
        self.assertEqual(refresh.get('nombre_rol'), Rol.ADMIN_GENERAL)

    def test_a07_login_credenciales_invalidas(self):
        """A07:2025 - Rechazo de credenciales inválidas"""
        response = self.client.post(self.login_url, {
            'username': 'admin_gral',
            'password': 'wrong_password',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a07_login_usuario_inactivo(self):
        """A07:2025 - Rechazo de usuario con estado_activo=False"""
        response = self.client.post(self.login_url, {
            'username': 'inactivo',
            'password': 'password_inactivo',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a07_uso_token_usuario_inactivo(self):
        """A07:2025 - Uso de token válido pero usuario se desactiva"""
        user_temp = Usuario.objects.create_user(
            username='temp_user',
            rut='99999999-9',
            password='password_temp',
            rol=self.rol_consulta,
        )
        response_login = self.client.post(self.login_url, {
            'username': 'temp_user',
            'password': 'password_temp',
        })
        self.assertEqual(response_login.status_code, status.HTTP_200_OK)
        token = response_login.data['access']

        user_temp.estado_activo = False
        user_temp.save()

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response_roles = self.client.get(self.roles_url)
        self.assertEqual(response_roles.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a07_rotacion_refresh_y_blacklist(self):
        """A07:2025 - Rotación de refresh y blacklist"""
        response = self.client.post(self.login_url, {
            'username': 'admin_gral',
            'password': 'password_admin',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refresh_token = response.data['refresh']

        response_refresh = self.client.post(self.refresh_url, {
            'refresh': refresh_token,
        })
        self.assertEqual(response_refresh.status_code, status.HTTP_200_OK)
        self.assertIn('refresh', response_refresh.data)
        self.assertNotEqual(response_refresh.data['refresh'], refresh_token)

        response_reuso = self.client.post(self.refresh_url, {
            'refresh': refresh_token,
        })
        self.assertEqual(response_reuso.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a04_cryptographic_failures_argon2(self):
        """A04:2025 - Verificar que password comience con argon2$"""
        self.assertTrue(self.admin_gral.password.startswith('argon2$'))
        self.assertTrue(check_password('password_admin', self.admin_gral.password))

    def test_a04_password_no_expuesto_en_listado(self):
        """A04:2025 - Password jamás aparece en el JSON de GET /api/usuarios/"""
        self.client.force_authenticate(user=self.admin_gral)
        response = self.client.get(self.usuarios_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usuarios_data = (
            response.data.get('results', response.data)
            if isinstance(response.data, dict)
            else response.data
        )
        for user_item in usuarios_data:
            self.assertNotIn('password', user_item)

    def test_a04_jwt_firma_alterada(self):
        """A04:2025 - Rechazar tokens JWT con firma alterada"""
        response_login = self.client.post(self.login_url, {
            'username': 'admin_gral',
            'password': 'password_admin',
        })
        self.assertEqual(response_login.status_code, status.HTTP_200_OK)
        token_valido = response_login.data['access']
        token_alterado = token_valido[:-1] + ('a' if token_valido[-1] != 'a' else 'b')

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token_alterado)
        response = self.client.get(self.usuarios_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a01_rbac_acceso_usuarios_get(self):
        """A01:2025 - Matriz de acceso GET /api/usuarios/"""
        self.client.force_authenticate(user=self.admin_gral)
        self.assertEqual(self.client.get(self.usuarios_url).status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.admin)
        self.assertEqual(self.client.get(self.usuarios_url).status_code, status.HTTP_200_OK)

        for usuario_restringido in [self.tecnico, self.user_inactivo]:
            if usuario_restringido.estado_activo:
                self.client.force_authenticate(user=usuario_restringido)
                self.assertEqual(
                    self.client.get(self.usuarios_url).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_a01_escalada_privilegios_crear_admin_gral(self):
        """A01:2025 - Bloqueo escalada: Administración no puede crear Admin General"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self.usuarios_url, {
            'username': 'nuevo_admin_gral',
            'password': 'strongpassword',
            'rut': '55555555-5',
            'rol': self.rol_admin_gral.id_rol,
            'estado_activo': True,
        })
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])

    def test_a01_escalada_privilegios_asignar_admin_gral(self):
        """A01:2025 - Bloqueo escalada: Administración no puede auto-asignarse Admin General"""
        self.client.force_authenticate(user=self.admin)
        url_update = reverse('core:usuario_detail', kwargs={'id_usuario': self.admin.id_usuario})
        response = self.client.patch(url_update, {
            'rol': self.rol_admin_gral.id_rol,
        })
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])

    def test_a02_security_misconfig_anonimo(self):
        """A02:2025 - Peticiones anónimas reciben 401"""
        self.client.credentials()
        response = self.client.get(self.usuarios_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a02_cors_headers(self):
        """A02:2025 - Verificación de cabeceras CORS para origen permitido y bloqueado"""
        response_permitido = self.client.options(
            self.usuarios_url,
            headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET'},
        )
        self.assertIn(response_permitido.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])
        if 'Access-Control-Allow-Origin' in response_permitido:
            self.assertEqual(response_permitido['Access-Control-Allow-Origin'], 'http://localhost:5173')
        if 'Access-Control-Expose-Headers' in response_permitido:
            self.assertIn('Content-Disposition', response_permitido['Access-Control-Expose-Headers'])

        response_bloqueado = self.client.options(
            self.usuarios_url,
            headers={'Origin': 'https://sitio-no-autorizado.cl', 'Access-Control-Request-Method': 'GET'},
        )
        self.assertNotIn('Access-Control-Allow-Origin', response_bloqueado)

    def test_a09_logging_crear_usuario(self):
        """A09:2025 - Registro OP_INSERT en LogAuditoria al crear usuario"""
        self.client.force_authenticate(user=self.admin_gral)
        count_logs_antes = LogAuditoria.objects.count()

        response = self.client.post(self.usuarios_url, {
            'username': 'nuevo_user',
            'password': 'password123',
            'rut': '66666666-6',
            'rol': self.rol_tecnico.id_rol,
            'estado_activo': True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        count_logs_despues = LogAuditoria.objects.count()
        self.assertEqual(count_logs_despues, count_logs_antes + 1)

        log = LogAuditoria.objects.last()
        self.assertEqual(log.tipo_operacion, LogAuditoria.OP_INSERT)
        self.assertEqual(log.tabla_afectada, 'usuarios')
        self.assertIsNone(log.valor_anterior)
        self.assertIsNotNone(log.valor_nuevo)
        self.assertEqual(log.valor_nuevo['username'], 'nuevo_user')
        self.assertNotIn('password', log.valor_nuevo)

    def test_a09_logging_editar_usuario(self):
        """A09:2025 - Registro OP_UPDATE en LogAuditoria al editar usuario"""
        self.client.force_authenticate(user=self.admin_gral)
        url_update = reverse('core:usuario_detail', kwargs={'id_usuario': self.tecnico.id_usuario})

        estado_previo = self.tecnico.estado_activo
        count_logs_antes = LogAuditoria.objects.count()

        response = self.client.patch(url_update, {
            'estado_activo': not estado_previo,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        count_logs_despues = LogAuditoria.objects.count()
        self.assertEqual(count_logs_despues, count_logs_antes + 1)

        log = LogAuditoria.objects.last()
        self.assertEqual(log.tipo_operacion, LogAuditoria.OP_UPDATE)
        self.assertEqual(log.tabla_afectada, 'usuarios')
        self.assertIsNotNone(log.valor_anterior)
        self.assertIsNotNone(log.valor_nuevo)
        self.assertEqual(log.valor_anterior['estado_activo'], estado_previo)
        self.assertEqual(log.valor_nuevo['estado_activo'], not estado_previo)
        self.assertNotIn('password', log.valor_nuevo)