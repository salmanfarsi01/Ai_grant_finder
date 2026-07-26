from unittest import mock
import os

from django.test import SimpleTestCase

import STEPO_BACKEND.settings as settings_module


class EmailBackendSettingsTests(SimpleTestCase):
    def test_console_backend_used_in_debug_mode(self):
        with mock.patch.dict(os.environ, {'POSTMARK_SERVER_TOKEN': 'test-token'}, clear=False):
            backend, anymail = settings_module._get_email_backend_config(debug=True)
            self.assertEqual(backend, 'django.core.mail.backends.console.EmailBackend')
            self.assertEqual(anymail, {})
