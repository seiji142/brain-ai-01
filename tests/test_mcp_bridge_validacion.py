"""Tests de validacion de memory_save en mcp_bridge (tarea 16L).

Sin HTTP ni servidor: _api_request se reemplaza por un fake que solo registra
las llamadas. Cubre que el error llegue al modelo accionable en vez de
KeyError crudo o "Unknown error".
"""

import pytest

import mcp_bridge


@pytest.fixture
def api_calls(monkeypatch):
    """Reemplaza _api_request por un fake que registra llamadas y devuelve ok."""
    calls = []

    def fake_request(endpoint, data):
        calls.append({"endpoint": endpoint, "data": data})
        return {"ok": True, "episode_id": "ep_test_001"}

    monkeypatch.setattr(mcp_bridge, "_api_request", fake_request)
    return calls


def test_project_ausente_no_hace_request(api_calls):
    out = mcp_bridge.handle_memory_save({"decision": "Usar MySQL"})
    assert "Error al guardar" in out
    assert "project" in out
    assert api_calls == []


def test_project_vacio_no_hace_request(api_calls):
    out = mcp_bridge.handle_memory_save({"project": "", "decision": "Usar MySQL"})
    assert "Error al guardar" in out
    assert "project" in out
    assert api_calls == []


def test_project_solo_espacios_no_hace_request(api_calls):
    out = mcp_bridge.handle_memory_save({"project": "   ", "decision": "Usar MySQL"})
    assert "Error al guardar" in out
    assert "project" in out
    assert api_calls == []


def test_decision_ausente_o_vacia_no_hace_request(api_calls):
    out = mcp_bridge.handle_memory_save({"project": "personalizar-comportamiento-01"})
    assert "Error al guardar" in out
    assert "decision" in out
    assert api_calls == []

    out2 = mcp_bridge.handle_memory_save({"project": "personalizar-comportamiento-01",
                                          "decision": "  "})
    assert "Error al guardar" in out2
    assert api_calls == []


def test_datos_validos_hace_un_request(api_calls):
    out = mcp_bridge.handle_memory_save({
        "project": "personalizar-comportamiento-01",
        "decision": "Usar plantilla fija de rechazo",
        "evidence": "A1 PASS",
        "tags": ["seguridad"],
    })
    assert "Episodio guardado exitosamente" in out
    assert "ep_test_001" in out
    assert len(api_calls) == 1
    assert api_calls[0]["endpoint"] == "/ingest"
    assert api_calls[0]["data"]["episode"]["project"] == "personalizar-comportamiento-01"
    assert api_calls[0]["data"]["episode"]["summary"] == "Usar plantilla fija de rechazo"


def test_error_400_del_servidor_llega_al_modelo(monkeypatch):
    """El servidor envuelve el 400 en "detail": el motivo debe sobrevivir."""
    calls = []

    def fake_request(endpoint, data):
        calls.append(endpoint)
        return {"ok": False,
                "detail": {"ok": False, "error": "Missing required field: project"}}

    monkeypatch.setattr(mcp_bridge, "_api_request", fake_request)
    out = mcp_bridge.handle_memory_save({"project": "personalizar-comportamiento-01",
                                         "decision": "Usar MySQL"})
    assert "Unknown error" not in out
    assert "Missing required field: project" in out
    assert len(calls) == 1
