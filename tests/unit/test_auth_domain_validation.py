import pytest

from apps.api.src.api.exceptions import BadRequestException, DisallowedEmailDomainException
from apps.api.src.services.auth_service import AuthService


def test_verify_valid_acme_domain():
    assert AuthService._verify_email_domain("john@acme.com") == "john@acme.com"
    assert AuthService._verify_email_domain("ALEX.MORGAN@ACME.COM") == "alex.morgan@acme.com"
    assert AuthService._verify_email_domain(" dev@acme.com ") == "dev@acme.com"


def test_verify_invalid_domains_rejected():
    with pytest.raises(DisallowedEmailDomainException) as exc1:
        AuthService._verify_email_domain("user@gmail.com")
    assert exc1.value.code == "DISALLOWED_EMAIL_DOMAIN"
    assert "acme.com" in exc1.value.message

    with pytest.raises(DisallowedEmailDomainException) as exc2:
        AuthService._verify_email_domain("user@fake-acme.com")
    assert exc2.value.code == "DISALLOWED_EMAIL_DOMAIN"

    with pytest.raises(DisallowedEmailDomainException) as exc3:
        AuthService._verify_email_domain("user@acme.com.attacker.org")
    assert exc3.value.code == "DISALLOWED_EMAIL_DOMAIN"


def test_verify_malformed_email_rejected():
    with pytest.raises(BadRequestException) as exc:
        AuthService._verify_email_domain("invalid-no-at-symbol")
    assert exc.value.code == "INVALID_EMAIL"
