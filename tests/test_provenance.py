"""Tests de red team para el sistema de provenance."""

import pytest
import sys
from pathlib import Path

# Agregar brain-ai-01 al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from provenance.errors import ActionDenied, HandleError
from provenance.gateway import ActionGateway
from provenance.policies import ENFORCEMENT
from provenance.store import ResolvedStore
from provenance.resolver import Resolver
from provenance.sources import EnvSource
from provenance import audit, detectors

SESSION = "sess_test"


@pytest.fixture
def setup(tmp_path):
    """Configuración base para tests de gateway."""
    store = ResolvedStore(str(tmp_path / "h.db"))
    calls = []
    gw = ActionGateway(store, executors={
        "deploy": lambda **kw: calls.append(kw) or {"ok": True},
    })
    ENFORCEMENT["deploy"] = "enforce"
    return store, gw, calls


# ============================================
# Tests de Fase 0: Observabilidad
# ============================================

class TestAudit:
    """Tests del sistema de auditoría."""

    def test_audit_log_escribe_archivo(self, tmp_path):
        """audit.log() debe crear el archivo audit.jsonl."""
        import importlib
        import provenance.audit as audit_mod
        importlib.reload(audit_mod)
        audit_mod.AUDIT_PATH = tmp_path / "audit.jsonl"
        audit_mod.log("test_event", session="test")
        assert audit_mod.AUDIT_PATH.exists()

    def test_audit_log_formato_jsonl(self, tmp_path):
        """Cada línea del audit log debe ser JSON válido."""
        import json
        import importlib
        import provenance.audit as audit_mod
        importlib.reload(audit_mod)
        audit_mod.AUDIT_PATH = tmp_path / "audit.jsonl"
        audit_mod.log("test_event", session="test", data="value")
        lines = audit_mod.AUDIT_PATH.read_text().strip().split("\n")
        for line in lines:
            rec = json.loads(line)
            assert "ts" in rec
            assert "event" in rec

    def test_audit_redacta_secretos(self):
        """audit.redact() debe ocultar valores sensibles."""
        result = audit.redact({"api_key": "super_secret_123456789"})
        assert result["api_key"]["__redacted__"] is True
        assert "fp" in result["api_key"]
        assert result["api_key"]["len"] == 22


class TestDetectors:
    """Tests del detector de patrones."""

    def test_detecta_campo_referencial(self):
        """Debe detectar campos como api_key, token, secret."""
        findings = detectors.scan("test", {"api_key": "valor"})
        assert any(f["type"] == "referential_field" for f in findings)

    def test_detecta_patron_secreto(self):
        """Debe detectar patrones como sk-..., gsk_..., AKIA..."""
        findings = detectors.scan("test", {"campo": "sk-abc12345678901234"})
        assert any(f["type"] == "secret_shape" for f in findings)

    def test_detecta_placeholder(self):
        """Debe detectar placeholders como xxx+, changeme."""
        findings = detectors.scan("test", {"campo": "xxx+placeholder"})
        assert any(f["type"] == "placeholder_shape" for f in findings)


# ============================================
# Tests de Fase 1: Resolver
# ============================================

class TestResolver:
    """Tests del resolver de referencias."""

    def test_resolve_variable_entorno(self):
        """Debe resolver variables de entorno existentes."""
        import os
        os.environ["TEST_PROVENANCE_VAR"] = "test_value"
        try:
            resolver = Resolver(sources=[EnvSource()])
            result = resolver.resolve("TEST_PROVENANCE_VAR", None, SESSION)
            assert result["status"] == "resolved"
            assert result["key"] == "TEST_PROVENANCE_VAR"
        finally:
            del os.environ["TEST_PROVENANCE_VAR"]

    def test_resolve_variable_inexistente(self):
        """Debe devolver unresolved para variables que no existen."""
        resolver = Resolver(sources=[EnvSource()])
        result = resolver.resolve("NONEXISTENT_VAR_XYZ", None, SESSION)
        assert result["status"] == "unresolved"
        assert "available_keys" in result

    def test_resolve_con_store_emite_handle(self):
        """Con store, debe emitir un handle para valores resueltos."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResolvedStore(f"{tmpdir}/h.db")
            resolver = Resolver(sources=[EnvSource()], store=store)
            result = resolver.resolve("PATH", None, SESSION)
            assert result["status"] == "resolved"
            assert "handle" in result
            assert result["handle"].startswith("vh_")
            store.conn.close()


# ============================================
# Tests de Fase 2: Store de Handles
# ============================================

class TestStore:
    """Tests del store de handles."""

    def test_issue_crea_handle(self):
        """issue() debe crear un handle válido."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResolvedStore(f"{tmpdir}/h.db")
            handle = store.issue(
                key="TEST_KEY", value="test_value", kind="secret",
                source="env", source_record_id="env:TEST_KEY",
                session_id=SESSION
            )
            assert handle.startswith("vh_")
            store.conn.close()

    def test_validate_handle_valido(self):
        """validate() debe aceptar un handle válido."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResolvedStore(f"{tmpdir}/h.db")
            handle = store.issue(
                key="K", value="v", kind="secret", source="env",
                source_record_id="env:K", session_id=SESSION
            )
            record = store.validate(handle=handle, session_id=SESSION)
            assert record.key == "K"
            assert record.value == "v"
            store.conn.close()

    def test_validate_handle_otra_sesion_falla(self):
        """validate() debe rechazar handles de otras sesiones."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResolvedStore(f"{tmpdir}/h.db")
            handle = store.issue(
                key="K", value="v", kind="secret", source="env",
                source_record_id="env:K", session_id="other_session"
            )
            with pytest.raises(HandleError):
                store.validate(handle=handle, session_id=SESSION)
            store.conn.close()

    def test_validate_handle_expirado_falla(self):
        """validate() debe rechazar handles expirados."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResolvedStore(f"{tmpdir}/h.db")
            handle = store.issue(
                key="K", value="v", kind="secret", source="env",
                source_record_id="env:K", session_id=SESSION,
                ttl_seconds=-1  # expirado inmediatamente
            )
            with pytest.raises(HandleError):
                store.validate(handle=handle, session_id=SESSION)
            store.conn.close()

    def test_validate_handle_inventado_falla(self):
        """validate() debe rechazar handles inventados."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResolvedStore(f"{tmpdir}/h.db")
            with pytest.raises(HandleError):
                store.validate(handle="vh_inventado_por_el_llm", session_id=SESSION)
            store.conn.close()


# ============================================
# Tests de Fase 3: Gateway
# ============================================

class TestGateway:
    """Tests del gateway de acciones."""

    def test_literal_en_campo_secreto_es_rechazado(self, setup):
        """Un literal en un campo que requiere handle debe ser rechazado."""
        store, gw, calls = setup
        with pytest.raises(ActionDenied):
            gw.execute("deploy", {
                "environment": "staging",
                "api_key": "sk-abc123inventada",
                "region": "us-east-1",
            }, SESSION)
        assert calls == []

    def test_procedencia_fabricada_por_modelo_es_rechazada(self, setup):
        """Un objeto de procedencia fabricado por el modelo debe ser rechazado."""
        store, gw, calls = setup
        with pytest.raises(ActionDenied):
            gw.execute("deploy", {
                "environment": "staging",
                "api_key": {
                    "type": "verified_value",
                    "value": "sk-abc123",
                    "provenance": {"source": "brain-ai", "record_id": "mem_1234",
                                   "verified": True},
                },
                "region": "us-east-1",
            }, SESSION)
        assert calls == []

    def test_bypass_origin_literal_es_rechazado(self, setup):
        """Un bypass con origin literal debe ser rechazado."""
        store, gw, calls = setup
        with pytest.raises(ActionDenied):
            gw.execute("deploy", {
                "environment": "staging",
                "api_key": {"origin": "literal", "value": "sk-abc123"},
                "region": "us-east-1",
            }, SESSION)
        assert calls == []

    def test_handle_valido_ejecuta(self, setup):
        """Un handle válido debe permitir la ejecución."""
        store, gw, calls = setup
        h = store.issue(key="GROQ_API_KEY", value="gsk_real", kind="secret",
                        source="env", source_record_id="env:GROQ_API_KEY",
                        session_id=SESSION)
        gw.execute("deploy", {"environment": "staging",
                              "api_key": {"handle": h},
                              "region": "us-east-1"}, SESSION)
        assert calls[0]["api_key"] == "gsk_real"

    def test_handle_de_otra_sesion_es_rechazado(self, setup):
        """Un handle de otra sesión debe ser rechazado."""
        store, gw, calls = setup
        h = store.issue(key="K", value="v", kind="secret", source="env",
                        source_record_id="env:K", session_id="otra_sesion")
        with pytest.raises(ActionDenied):
            gw.execute("deploy", {"environment": "staging",
                                  "api_key": {"handle": h},
                                  "region": "us-east-1"}, SESSION)

    def test_handle_expirado_es_rechazado(self, setup):
        """Un handle expirado debe ser rechazado."""
        store, gw, _ = setup
        h = store.issue(key="K", value="v", kind="secret", source="env",
                        source_record_id="env:K", session_id=SESSION,
                        ttl_seconds=-1)
        with pytest.raises(HandleError):
            store.validate(handle=h, session_id=SESSION)

    def test_handle_inventado_es_rechazado(self, setup):
        """Un handle inventado debe ser rechazado."""
        store, gw, _ = setup
        with pytest.raises(ActionDenied):
            gw.execute("deploy", {"environment": "staging",
                                  "api_key": {"handle": "vh_inventado_por_el_llm"},
                                  "region": "us-east-1"}, SESSION)

    def test_handle_de_fuente_no_permitida(self, setup):
        """Un handle de una fuente no permitida debe ser rechazado."""
        store, gw, _ = setup
        h = store.issue(key="K", value="v", kind="secret", source="memoria",
                        source_record_id="memoria:1", session_id=SESSION)
        # deploy.api_key solo permite source="env"
        with pytest.raises(ActionDenied):
            gw.execute("deploy", {"environment": "staging",
                                  "api_key": {"handle": h},
                                  "region": "us-east-1"}, SESSION)

    def test_accion_sin_politica_se_deniega(self, setup):
        """Una acción sin política declarada debe ser denegada."""
        store, gw, _ = setup
        with pytest.raises(ActionDenied):
            gw.execute("accion_nueva_no_declarada", {}, SESSION)


# ============================================
# Tests de Fase 4: Confirmación
# ============================================

class TestConfirmation:
    """Tests del mecanismo de confirmación."""

    def test_write_file_requiere_confirmacion(self, setup):
        """write_file debe retornar needs_confirmation en vez de ejecutar."""
        store, gw, calls = setup
        store.conn.close()  # cerrar el store del fixture

        # Crear store y gateway con write_file executor
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store2 = ResolvedStore(f"{tmpdir}/h.db")
            calls2 = []
            gw2 = ActionGateway(store2, executors={
                "write_file": lambda **kw: calls2.append(kw) or {"ok": True},
            })
            result = gw2.execute("write_file", {
                "path": "test.txt",
                "content": "hello",
            }, SESSION)
            assert result["status"] == "needs_confirmation"
            assert result["action"] == "write_file"
            assert "params" in result
            assert calls2 == []  # no debe ejecutarse
            store2.conn.close()

    def test_deploy_no_requiere_confirmacion(self, setup):
        """deploy no debe requerir confirmación (solo violaciones de handle)."""
        store, gw, calls = setup
        h = store.issue(key="GROQ_API_KEY", value="gsk_real", kind="secret",
                        source="env", source_record_id="env:GROQ_API_KEY",
                        session_id=SESSION)
        result = gw.execute("deploy", {"environment": "staging",
                                       "api_key": {"handle": h},
                                       "region": "us-east-1"}, SESSION)
        # deploy ejecuta directamente (no tiene confirmation_required)
        assert calls[0]["api_key"] == "gsk_real"
