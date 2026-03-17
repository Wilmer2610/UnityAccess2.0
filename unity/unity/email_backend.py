import base64
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, 'BREVO_API_KEY', None) or ''
        api_key = api_key.strip()
        if not api_key:
            if self.fail_silently:
                return 0
            raise ValueError('BREVO_API_KEY no está configurada')

        sender_email = (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()
        sender_name = (getattr(settings, 'BREVO_SENDER_NAME', '') or '').strip() or None
        if not sender_email or '@' not in sender_email:
            if self.fail_silently:
                return 0
            raise ValueError('DEFAULT_FROM_EMAIL no es un correo válido')

        sent = 0
        for msg in email_messages:
            try:
                sent += 1 if self._send_one(msg, api_key, sender_email, sender_name) else 0
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

    def _send_one(self, msg, api_key, sender_email, sender_name):
        to = [{'email': e} for e in (msg.to or []) if e]
        cc = [{'email': e} for e in (getattr(msg, 'cc', None) or []) if e]
        bcc = [{'email': e} for e in (getattr(msg, 'bcc', None) or []) if e]
        if not to and not cc and not bcc:
            return False

        payload = {
            'sender': {'email': sender_email},
            'to': to,
            'subject': msg.subject or '',
        }
        if sender_name:
            payload['sender']['name'] = sender_name
        if cc:
            payload['cc'] = cc
        if bcc:
            payload['bcc'] = bcc

        html_body = None
        for alt, mimetype in getattr(msg, 'alternatives', []) or []:
            if mimetype == 'text/html':
                html_body = alt
                break

        if html_body is not None:
            payload['htmlContent'] = html_body
            payload['textContent'] = msg.body or ''
        else:
            payload['textContent'] = msg.body or ''

        atts = []
        for att in getattr(msg, 'attachments', []) or []:
            if isinstance(att, tuple) and len(att) == 3:
                filename, content, mimetype = att
                content_b64 = base64.b64encode(content).decode('ascii') if isinstance(content, (bytes, bytearray)) else base64.b64encode(str(content).encode('utf-8')).decode('ascii')
                a = {'name': filename, 'content': content_b64}
                if mimetype:
                    a['type'] = mimetype
                atts.append(a)
            elif isinstance(att, tuple) and len(att) == 2:
                filename, content = att
                content_b64 = base64.b64encode(content).decode('ascii') if isinstance(content, (bytes, bytearray)) else base64.b64encode(str(content).encode('utf-8')).decode('ascii')
                atts.append({'name': filename, 'content': content_b64})

        if atts:
            payload['attachment'] = atts

        data = json.dumps(payload).encode('utf-8')
        req = Request(
            'https://api.brevo.com/v3/smtp/email',
            data=data,
            headers={
                'Content-Type': 'application/json',
                'api-key': api_key,
                'Accept': 'application/json',
            },
            method='POST',
        )
        try:
            with urlopen(req, timeout=getattr(settings, 'BREVO_TIMEOUT_SECONDS', 20)) as resp:
                return 200 <= getattr(resp, 'status', 200) < 300
        except HTTPError as e:
            if self.fail_silently:
                return False
            body = ''
            try:
                body = e.read().decode('utf-8', errors='ignore')
            except Exception:
                body = ''
            raise RuntimeError(f'Brevo API error {e.code}: {body or e.reason}')
        except URLError as e:
            if self.fail_silently:
                return False
            raise RuntimeError(f'Brevo API connection error: {e}')

