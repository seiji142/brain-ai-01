#!/usr/bin/env python3
"""
MCP Bridge para brain-ai-01.
Traduce tool calls MCP → HTTP requests a brain-ai-01.

Uso:
  Configurar en opencode.json:
  {
    "mcp": {
      "brain-ai": {
        "type": "local",
        "command": ["python", "path/to/mcp_bridge.py"],
        "enabled": true
      }
    }
  }

Tools disponibles:
  - memory_search: Busca episodios en memoria
  - memory_save: Guarda episodio en memoria
  - memory_consolidate: Consolida memoria episódica a semántica
  - resolver_referencia: Resuelve una referencia contra fuentes autorizadas
  - describir_handle: Devuelve metadatos de un handle (sin el valor)
  - ejecutar_accion: Ejecuta una acción con efectos (requiere handle verificado)
"""

import json
import sys
import os
import uuid
import subprocess
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from provenance import audit, detectors
    HAS_PROVENANCE = True
except ImportError:
    HAS_PROVENANCE = False

BRAIN_API = os.getenv("BRAIN_AI_URL", "http://localhost:8000")

# Session ID inyectado por el bridge. El modelo NUNCA debe controlar esto.
_SESSION_ID = f"sess_{uuid.uuid4().hex[:12]}"

# --- Auto-start del servidor brain-ai-01 ---
_BRIDGE_DIR = Path(__file__).parent
_LOG_DIR = _BRIDGE_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_last_attempt = 0.0


def _log(message):
    """Escribe mensaje en log de auto-start."""
    try:
        with open(_LOG_DIR / "bridge.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {message}\n")
    except:
        pass


def _is_healthy():
    """Verifica si brain-ai-01 está respondiendo."""
    try:
        return requests.get(f"{BRAIN_API}/health", timeout=2).status_code == 200
    except requests.RequestException:
        return False


def ensure_server(timeout=30):
    """Asegura que brain-ai-01 esté corriendo. Lo inicia si es necesario."""
    global _last_attempt
    
    # Si ya está healthy, no hacer nada
    if _is_healthy():
        return True
    
    # Cooldown anti-spam: no intentar más de una vez por minuto
    if time.time() - _last_attempt < 60:
        return False
    _last_attempt = time.time()
    
    _log(f"=== ensure_server: intentando iniciar brain-ai-01 ===")
    _log(f"Python: {sys.executable}")
    _log(f"Directorio: {_BRIDGE_DIR}")
    
    # Abrir log para uvicorn
    log_file = open(_LOG_DIR / "uvicorn.log", "ab")
    log_file.write(f"\n--- intento {time.ctime()} | python={sys.executable} ---\n".encode())
    log_file.flush()
    
    cmd = [sys.executable, "-m", "uvicorn", 
           "ai_architect.core.mcp_server:app",
           "--host", "127.0.0.1",
           "--port", "8000"]
    
    _log(f"Comando: {' '.join(cmd)}")
    
    # Flags para Windows: sin ventana + breakaway de Job Object
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(_BRIDGE_DIR),
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB
        )
    except OSError:
        # Fallback si breakaway no está permitido
        proc = subprocess.Popen(
            cmd,
            cwd=str(_BRIDGE_DIR),
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=flags
        )
    
    _log(f"Proceso iniciado con PID: {proc.pid}")
    
    # Esperar a que esté listo, detectando muerte temprana
    for i in range(timeout):
        if proc.poll() is not None:
            _log(f"ERROR: Proceso muerto con exit code {proc.returncode}")
            return False
        if _is_healthy():
            _log(f"✅ Servidor brain-ai-01 listo después de {i+1} segundos")
            return True
        time.sleep(1)
    
    _log(f"ERROR: Servidor no respondió después de {timeout} segundos")
    return False

TOOLS = [
    {
        "name": "memory_search",
        "description": "Busca episodios y conocimiento en la memoria persistente. Usa esto ANTES de responder preguntas sobre decisiones pasadas, configuración anterior, o lecciones aprendidas.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto a buscar en memoria (ej: 'configuración de base de datos', 'error de JWT')"
                },
                "project": {
                    "type": "string",
                    "description": "Nombre del proyecto para filtrar resultados (ej: 'personalizar-comportamiento-01')"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Número máximo de resultados (default: 5)",
                    "default": 5
                },
                "collection": {
                    "type": "string",
                    "description": "Colección a buscar: 'semantic' (conocimiento consolidado) o 'episodic' (eventos crudos)",
                    "enum": ["semantic", "episodic"],
                    "default": "semantic"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "memory_save",
        "description": "Guarda un episodio en la memoria persistente. Usa esto DESPUÉS de tomar una decisión importante, resolver un error, o aprender algo nuevo.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Nombre del proyecto (ej: 'personalizar-comportamiento-01')"
                },
                "decision": {
                    "type": "string",
                    "description": "Decisión tomada o lección aprendida"
                },
                "evidence": {
                    "type": "string",
                    "description": "Evidencia que respalda la decisión (código, configuración, resultado)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags descriptivos (ej: ['jwt', 'seguridad', 'error'])"
                }
            },
            "required": ["project", "decision"]
        }
    },
    {
        "name": "memory_consolidate",
        "description": "Consolida episodios en conocimiento semántico. Ejecutar periódicamente para promover episodios repetidos a conocimiento consolidado.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Nombre del proyecto (opcional, consolida todos si no se especifica)"
                }
            }
        }
    },
    {
        "name": "resolver_referencia",
        "description": (
            "Resuelve una referencia (nombre de variable, ruta, endpoint, credencial) "
            "contra fuentes autorizadas. ÚNICA forma legítima de obtener un valor. "
            "Devuelve resolved | ambiguous | needs_confirmation | unresolved."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "La expresión tal como la escribió el usuario"
                },
                "expected_kind": {
                    "type": "string",
                    "description": "Tipo esperado: secret|env_var|path|endpoint|record_id|config",
                    "enum": ["secret", "env_var", "path", "endpoint", "record_id", "config"]
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "describir_handle",
        "description": "Devuelve metadatos de un handle (key, kind, source). No devuelve el valor.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "handle": {
                    "type": "string",
                    "description": "El handle a describir (vh_...)"
                }
            },
            "required": ["handle"]
        }
    },
    {
        "name": "ejecutar_accion",
        "description": (
            "Ejecuta una acción con efectos. Los campos referenciales requieren "
            "{'handle': 'vh_...'} obtenido de resolver_referencia."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Nombre de la acción a ejecutar"
                },
                "params": {
                    "type": "object",
                    "description": "Parámetros de la acción"
                }
            },
            "required": ["action", "params"]
        }
    }
]


def _api_request(endpoint, data):
    """Realiza una request HTTP a brain-ai-01. Inicia el servidor si no está corriendo."""
    if not HAS_REQUESTS:
        return {"ok": False, "error": "requests library not installed"}
    try:
        r = requests.post(f"{BRAIN_API}{endpoint}", json=data, timeout=30)
        return r.json()
    except requests.ConnectionError:
        # Servidor no está corriendo - intentar iniciarlo automáticamente
        if ensure_server():
            # Servidor iniciado exitosamente - reintentar la petición
            try:
                r = requests.post(f"{BRAIN_API}{endpoint}", json=data, timeout=30)
                return r.json()
            except Exception as e:
                return {"ok": False, "error": f"Error después de iniciar servidor: {str(e)}"}
        # No se pudo iniciar el servidor
        return {"ok": False, "error": "brain-ai-01 no está disponible. Intenta de nuevo en unos segundos."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def observed(tool_name: str, fn):
    """Decorador de observación. Fase 0: no bloquea nada, solo registra."""
    if not HAS_PROVENANCE:
        return fn

    def wrapper(**params):
        findings = detectors.scan(tool_name, params)
        audit.log(
            "tool_call",
            tool=tool_name,
            session=_SESSION_ID,
            params=audit.redact(params),
            findings=findings,
        )
        result = fn(**params)
        audit.log("tool_result", tool=tool_name, session=_SESSION_ID, ok=True)
        return result
    return wrapper


def handle_memory_search(args):
    """Busca episodios en memoria."""
    result = _api_request("/retrieve", {
        "query": args["query"],
        "top_k": args.get("top_k", 5),
        "project": args.get("project"),
        "collection": args.get("collection", "semantic")
    })
    
    if "results" in result:
        items = result["results"]
        if not items:
            return f"No se encontraron resultados para: '{args['query']}'"
        
        lines = [f"Encontrados {len(items)} resultados:"]
        for i, item in enumerate(items, 1):
            text = item.get("text", "")[:200]
            score = item.get("score", 0)
            project = item.get("project", "desconocido")
            lines.append(f"{i}. [{score:.2f}] (Proyecto: {project}) {text}")
        return "\n".join(lines)
    
    return f"Error: {result.get('error', 'Unknown error')}"


def handle_memory_save(args):
    """Guarda un episodio en memoria."""
    result = _api_request("/ingest", {
        "episode": {
            "project": args["project"],
            "source_type": "chat",
            "author": "modelo",
            "title": args["decision"][:50],
            "summary": args["decision"],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "decisions": [{"text": args["decision"]}],
            "evidence": [{"type": "doc", "url_or_path": "", "excerpt": args.get("evidence", "")}] if args.get("evidence") else [],
            "tags": args.get("tags", [])
        }
    })
    
    if result.get("ok"):
        episode_id = result.get("episode_id", "unknown")
        return f"Episodio guardado exitosamente. ID: {episode_id}"
    
    return f"Error al guardar: {result.get('error', 'Unknown error')}"


def handle_memory_consolidate(args):
    """Consolida memoria episódica a semántica."""
    result = _api_request("/consolidate", {
        "project": args.get("project")
    })
    
    promotions = result.get("promotions", 0)
    contradictions = result.get("contradictions", 0)
    
    return f"Consolidación completada: {promotions} episodios promovidos a semántico, {contradictions} contradicciones detectadas."


def handle_resolver_referencia(args):
    """Resuelve una referencia contra fuentes autorizadas."""
    result = _api_request("/resolve_reference", {
        "expression": args["expression"],
        "expected_kind": args.get("expected_kind"),
        "session_id": _SESSION_ID,
    })
    return json.dumps(result, ensure_ascii=False, default=str)


def handle_describir_handle(args):
    """Devuelve metadatos de un handle."""
    result = _api_request("/describe_handle", {
        "handle": args["handle"],
        "session_id": _SESSION_ID,
    })
    if not result:
        return "Handle no encontrado o no pertenece a esta sesión."
    return json.dumps(result, ensure_ascii=False, default=str)


def handle_ejecutar_accion(args):
    """Ejecuta una acción con efectos a través del gateway."""
    result = _api_request("/actions/execute", {
        "action": args["action"],
        "params": args["params"],
        "session_id": _SESSION_ID,
    })
    return json.dumps(result, ensure_ascii=False, default=str)


TOOL_HANDLERS = {
    "memory_search": handle_memory_search,
    "memory_save": handle_memory_save,
    "memory_consolidate": handle_memory_consolidate,
    "resolver_referencia": handle_resolver_referencia,
    "describir_handle": handle_describir_handle,
    "ejecutar_accion": handle_ejecutar_accion,
}


def send_response(response):
    """Envía una respuesta MCP por stdout."""
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def handle_request(request):
    """Procesa una request MCP."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})
    
    if method == "initialize":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "brain-ai-01",
                    "version": "1.0.0"
                }
            }
        })
    
    elif method == "notifications/initialized":
        pass
    
    elif method == "tools/list":
        send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS}
        })
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        handler = TOOL_HANDLERS.get(tool_name)
        if handler:
            try:
                result = handler(arguments)
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": result}]
                    }
                })
            except Exception as e:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error ejecutando {tool_name}: {str(e)}"}],
                        "isError": True
                    }
                })
        else:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
            })
    
    elif method == "ping":
        send_response({"jsonrpc": "2.0", "id": req_id, "result": {}})
    
    elif method.startswith("notifications/"):
        pass
    
    else:
        if req_id is not None:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })


def main():
    """Loop principal MCP via stdio."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        handle_request(request)


if __name__ == "__main__":
    main()
