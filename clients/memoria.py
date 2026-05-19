"""
Helper Python para conectarse al servidor MCP de brain-ai-01.

COPY CANÓNICA — Esta es la versión oficial. Los proyectos la copian a su raíz:

    copy brain-ai-01\\clients\\memoria.py tu-proyecto\\memoria.py

El script detecta automáticamente la ubicación de brain-ai-01:
  - Si está dentro de brain-ai-01/clients/ → sube un nivel
  - Si está en un proyecto hermano → busca ../brain-ai-01/

Uso básico:
    from memoria import guardar, buscar, consolidar
    guardar("proyecto", "decisión", tags=["tag"])

Secretos con contexto:
    r = guardar_secreto("TELEFONO_ALGUIEN", "099XXXXXX")
    if r["contexto_faltante"]:
        guardar_contexto(r["nombre_base"], "es mi hermana")
"""

import requests, re
from datetime import datetime
from pathlib import Path

API = "http://localhost:8000"

def _find_brain_dir() -> Path:
    p = Path(__file__).resolve().parent
    if p.parent.name == "brain-ai-01":
        return p.parent
    candidate = p.parent / "brain-ai-01"
    if candidate.is_dir():
        return candidate
    raise FileNotFoundError(f"brain-ai-01 directory not found from {__file__}")

BRAIN_DIR = _find_brain_dir()
SECRETS_FILE = BRAIN_DIR / ".env.secrets"

_NO_ENTITY = {"CASA", "TRABAJO", "MADRE", "KEY", "API", "URL", "TOKEN",
              "SECRET", "ID", "HOST", "PORT", "USER", "PASS", "GMAIL",
              "CELULAR", "EMAIL", "TELEFONO"}

_PRIVACY_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?:\+?\d[\d\s\-\.]{7,}\d)\b"),
]

_DESCRIPCIONES = {
    "GMAIL": "El correo electr\u00f3nico",
    "CELULAR": "El celular",
    "EMAIL_TRABAJO": "El correo del trabajo",
    "TELEFONO_CASA": "El n\u00famero de casa",
    "TELEFONO_MADRE": "El n\u00famero de mi madre",
    "TELEFONO_NISHI": "El n\u00famero de Nishi",
    "TELEFONO_SHIZUMI": "El n\u00famero de Shizumi",
    "TELEFONO_JHONA": "El n\u00famero de Jhona",
    "TELEFONO_METSUKI": "El n\u00famero de Metsuki",
    "EMAIL_NISHI": "El correo electr\u00f3nico de Nishi",
    "EMAIL_SHIZUMI": "El correo electr\u00f3nico de Shizumi",
}


def _marcar_privado(texto: str) -> str:
    import sys
    marca = "\U0001F511" if sys.stdout.encoding.upper() in ("UTF-8", "UTF8") else "[PRIVADO]"
    sufijo = f" {marca} (informaci\u00f3n privada)"
    for pat in _PRIVACY_PATTERNS:
        texto = pat.sub(lambda m, s=sufijo: m.group(0) + s, texto)
    return texto


def _extraer_nombre_base(nombre_variable: str) -> str | None:
    partes = nombre_variable.split("_", 1)
    if len(partes) == 2:
        sufijo = partes[1].upper()
        if sufijo not in _NO_ENTITY:
            return partes[1].lower()
    return None


def check_contexto(nombre_base: str, proyecto: str | None = None) -> dict:
    r = requests.post(f"{API}/check_contexto", json={
        "nombre_base": nombre_base,
        "proyecto": proyecto,
    })
    return r.json()


def guardar_contexto(nombre_base: str, contexto: str, proyecto: str = "brain-ai-01"):
    r = requests.post(f"{API}/guardar_contexto", json={
        "nombre_base": nombre_base,
        "contexto": contexto,
        "proyecto": proyecto,
    })
    return r.json()


def guardar(proyecto, decision, evidencia="", source_type="chat", author="yo", tags=None):
    r = requests.post(f"{API}/ingest", json={"episode": {
        "project": proyecto,
        "source_type": source_type,
        "author": author,
        "title": decision[:50],
        "summary": decision,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decisions": [{"text": decision}],
        "evidence": [{"type": "doc", "url_or_path": "", "excerpt": evidencia}] if evidencia else [],
        "tags": tags or []
    }})
    return r.json()


def buscar(query, proyecto=None, top_k=5, coleccion=None, privado=True):
    if coleccion is None:
        colecciones = ["episodic", "semantic"]
    else:
        colecciones = [coleccion]

    seen_ids = set()
    all_results = []

    for col in colecciones:
        r = requests.post(f"{API}/retrieve", json={
            "query": query,
            "top_k": top_k * 2,
            "project": proyecto,
            "collection": col
        })
        for item in r.json().get("results", []):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                all_results.append(item)

    all_results.sort(key=lambda x: x["score"], reverse=True)
    all_results = all_results[:top_k]

    if privado:
        for item in all_results:
            item["text"] = _marcar_privado(item["text"])
    return all_results


def consolidar(proyecto=None):
    r = requests.post(f"{API}/consolidate", json={"project": proyecto})
    return r.json()


def evaluar(query, proyecto=None, top_k=5, coleccion="semantic"):
    r = requests.post(f"{API}/evaluate", json={
        "query": query,
        "project": proyecto,
        "top_k": top_k,
        "collection": coleccion
    })
    return r.json()


def _leer_env(nombre_variable):
    if not SECRETS_FILE.exists():
        return None
    for line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k == nombre_variable:
                return v
    return None


def leer_secreto(nombre_variable, privado=False, formato="sentencia"):
    valor = _leer_env(nombre_variable)
    if valor is None:
        return {"ok": False, "error": f"Variable {nombre_variable} no encontrada en .env.secrets"}
    if privado:
        valor = _marcar_privado(valor)
    sentencia = None
    if formato == "sentencia":
        import sys
        marca = "\U0001F511" if sys.stdout.encoding.upper() in ("UTF-8", "UTF8") else "[PRIVADO]"
        desc = _DESCRIPCIONES.get(nombre_variable, f"La variable {nombre_variable}")
        sentencia = f"{desc} es {valor} {marca} (informaci\u00f3n privada)."
    res = {"ok": True, "variable": nombre_variable, "valor": valor}
    if sentencia:
        res["sentencia"] = sentencia
    return res


def mostrar_secreto(nombre_variable):
    res = leer_secreto(nombre_variable)
    if not res["ok"]:
        print(res["error"])
        return
    print(res.get("sentencia", res["valor"]))


def guardar_secreto(nombre_variable, valor, proyecto="proyecto-web", tags=None):
    SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SECRETS_FILE.exists():
        SECRETS_FILE.write_text("", encoding="utf-8")

    lines = SECRETS_FILE.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{nombre_variable}="):
            lines[i] = f"{nombre_variable}={valor}"
            found = True
            break
    if not found:
        lines.append(f"{nombre_variable}={valor}")
    SECRETS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    desc = nombre_variable.lower().replace("_", " ")
    ref = f"La variable {nombre_variable} del .env.secrets contiene mi {desc}"
    all_tags = (tags or []) + ["secreto", "env", nombre_variable.lower()]

    nombre_base = _extraer_nombre_base(nombre_variable)
    contexto_faltante = False
    if nombre_base:
        ctx = check_contexto(nombre_base, proyecto)
        contexto_faltante = not ctx.get("tiene_contexto", False)

    guardar(proyecto, ref, tags=all_tags)
    return {
        "ok": True,
        "variable": nombre_variable,
        "nombre_base": nombre_base,
        "contexto_faltante": contexto_faltante,
    }
