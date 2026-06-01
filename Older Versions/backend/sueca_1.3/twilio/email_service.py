import os
from pathlib import Path
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

TEMPLATE_DIR = Path(__file__).resolve().parent / 'templates'


def _read_env_key_from_file(file_path: Path, key: str) -> str | None:
    if not file_path.exists():
        return None

    try:
        for raw_line in file_path.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            k, v = line.split('=', 1)
            if k.strip() != key:
                continue

            value = v.strip().strip('"').strip("'")
            if value:
                return value
    except Exception:
        return None

    return None


def _resolve_env_value(key: str, default: str | None = None) -> str | None:
    env_value = os.getenv(key)
    if env_value:
        return env_value

    twilio_dir = Path(__file__).resolve().parent
    project_root = twilio_dir.parent

    for candidate in (twilio_dir / '.env', project_root / '.env'):
        value = _read_env_key_from_file(candidate, key)
        if value:
            os.environ[key] = value
            return value

    return default


def _resolve_sendgrid_key() -> str | None:
    return _resolve_env_value('SENDGRID_API_KEY')


SEND_FROM_EMAIL = _resolve_env_value('SEND_FROM_EMAIL', 'suecadaojogo@gmail.com')

class EmailService:
    def __init__(self):
        self.api_key = _resolve_sendgrid_key()
        self.from_email = SEND_FROM_EMAIL
        if not self.api_key:
            raise ValueError(
                "SENDGRID_API_KEY não encontrada. "
                "Define a variável de ambiente ou adiciona-a em twilio/.env"
            )
        if self.from_email and self.from_email.lower().endswith('@gmail.com'):
            print(
                "Aviso: SEND_FROM_EMAIL com domínio gmail.com pode falhar por alinhamento "
                "DMARC/SPF/DKIM no SendGrid. Usa um domínio autenticado no SendGrid "
                "(ex: no-reply@teu-dominio.pt)."
            )
        self.sg = SendGridAPIClient(self.api_key)

    def send_email(self, to_email, subject, html_content):
        message = Mail(
            from_email=self.from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        try:
            response = self.sg.send(message)
            print(f"Email enviado com status code: {response.status_code}")
            return response.status_code
        except Exception as e:
            print(f"Erro ao enviar email: {str(e)}")
            return None

    def _load_template(self, template_name: str) -> str:
        template_path = TEMPLATE_DIR / template_name
        return template_path.read_text(encoding='utf-8')

    def send_verification_code(self, to_email: str, code: str, username: str = ''):
        template_html = self._load_template('verification_code.html')
        html_content = (
            template_html
            .replace('{{CODE}}', code)
            .replace('{{USERNAME}}', username or 'jogador')
        )
        return self.send_email(
            to_email=to_email,
            subject='Codigo de verificacao - Sueca',
            html_content=html_content,
        )