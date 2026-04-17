"""tests/test_infisical_secrets.py — Unit tests for infisical_secrets.py"""
import pytest
import os
from unittest.mock import patch, MagicMock

import infisical_secrets


def test_load_secrets_no_token():
    original = infisical_secrets.INFISICAL_TOKEN
    infisical_secrets.INFISICAL_TOKEN = ""
    try:
        result = infisical_secrets.load_secrets()
        assert result is False
    finally:
        infisical_secrets.INFISICAL_TOKEN = original


def test_load_secrets_import_error():
    infisical_secrets.INFISICAL_TOKEN = "test-token"
    try:
        with patch.dict("sys.modules", {"infisical": None}):
            result = infisical_secrets.load_secrets()
            assert result is False
    finally:
        infisical_secrets.INFISICAL_TOKEN = ""


def test_load_secrets_success():
    infisical_secrets.INFISICAL_TOKEN = "test-token"
    try:
        mock_secret = MagicMock()
        mock_secret.secret_name = "LITELLM_MASTER_KEY"
        mock_secret.secret_value = "sk-from-infisical"

        mock_client = MagicMock()
        mock_client.get_all_secrets.return_value = [mock_secret]

        mock_infisical = MagicMock()
        mock_infisical.InfisicalClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {"infisical": mock_infisical}):
            result = infisical_secrets.load_secrets()
            assert result is True
            assert os.environ.get("LITELLM_MASTER_KEY") == "sk-from-infisical"
    finally:
        infisical_secrets.INFISICAL_TOKEN = ""
        os.environ.pop("LITELLM_MASTER_KEY", None)
        os.environ.setdefault("LITELLM_MASTER_KEY", "test-master-key")


def test_load_secrets_infisical_down():
    infisical_secrets.INFISICAL_TOKEN = "test-token"
    try:
        with patch.dict("sys.modules", {"infisical": MagicMock(
            InfisicalClient=MagicMock(side_effect=Exception("Connection refused"))
        )}):
            result = infisical_secrets.load_secrets()
            assert result is False
    finally:
        infisical_secrets.INFISICAL_TOKEN = ""


def test_managed_secrets_list():
    assert "LITELLM_MASTER_KEY" in infisical_secrets.MANAGED_SECRETS
    assert "SURREAL_PASS" in infisical_secrets.MANAGED_SECRETS
    assert "KEYCLOAK_ADMIN_PASSWORD" in infisical_secrets.MANAGED_SECRETS
    assert "OPENFGA_PRESHARED_KEY" in infisical_secrets.MANAGED_SECRETS


def test_non_managed_secrets_not_injected():
    infisical_secrets.INFISICAL_TOKEN = "test-token"
    try:
        mock_secret = MagicMock()
        mock_secret.secret_name = "RANDOM_VAR"
        mock_secret.secret_value = "should-not-inject"

        mock_client = MagicMock()
        mock_client.get_all_secrets.return_value = [mock_secret]

        with patch.dict("sys.modules", {"infisical": MagicMock(InfisicalClient=lambda **kw: mock_client)}):
            result = infisical_secrets.load_secrets()
            assert result is True
            assert os.environ.get("RANDOM_VAR") != "should-not-inject"
    finally:
        infisical_secrets.INFISICAL_TOKEN = ""
