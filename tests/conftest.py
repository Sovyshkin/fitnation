import os


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("API_KEY", "test-api-key-long-enough")
os.environ.setdefault("SMTP_HOST", "smtp.example.test")
os.environ.setdefault("SMTP_USER", "hello@example.com")
os.environ.setdefault("SMTP_PASSWORD", "test-password")
os.environ.setdefault("SMTP_FROM", "hello@example.com")
os.environ.setdefault("SMTP_REPLY_TO", "hello@example.com")
