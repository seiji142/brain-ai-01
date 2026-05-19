"""
Pre-procesador: Imagen → Episodio en memoria brain-ai-01

Uso:
  python scripts/img_ingest.py ruta/imagen.jpg
  python scripts/img_ingest.py ruta/imagen.jpg --project proyecto-web --statement "Esta persona es Seiji"
  python scripts/img_ingest.py ruta/imagen.jpg --prompt "Describe la persona" --consolidate
  python scripts/img_ingest.py ruta/imagen.jpg --detail facial --consolidate
  python scripts/img_ingest.py ruta/imagen.jpg --detail full --consolidate
"""
import argparse, base64, httpx, json, os, sys
from pathlib import Path
from datetime import datetime
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_architect.core.config import IMAGES_DIR
from scripts.ingest_utils import mcp_ingest, save_media, build_episode, MCP_URL

OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
VISION_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"

DEFAULT_PROMPTS = {
    "basico": "Describe esta imagen en detalle.",
    "facial": (
        "Describe el ROSTRO de la persona en esta imagen. Indica: "
        "1) color de ojos (exacto), "
        "2) color de pelo, tipo y largo, "
        "3) color de piel/tono, "
        "4) forma de rostro, "
        "5) cejas, nariz, boca, labios, "
        "6) barba/bigote si tiene, "
        "7) edad aproximada, "
        "8) si usa lentes, "
        "9) expresion facial, "
        "10) accesorios faciales (piercings, joyas). "
        "Responde SOLO la informacion, sin introduccion."
    ),
    "full": (
        "Describe COMPLETAMENTE esta imagen con el maximo detalle posible. "
        "Seccion A - PERSONA: color exacto de ojos, color y tipo de pelo, "
        "tono de piel, forma de rostro, edad aparente, expresion, "
        "barba/bigote, lentes, accesorios faciales (piercings, joyas). "
        "Seccion B - VESTIMENTA: colores, marcas visibles, tipo de prendas. "
        "Seccion C - FONDO: ubicacion, clima, objetos notables, vegetacion, "
        "infraestructura. "
        "Seccion D - COMPOSICION: angulo de camara, iluminacion, encuadre. "
        "Responde en español con formato de secciones."
    ),
}


def _api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
        k = os.environ.get(var, "")
        if k:
            return k
    print("Error: OPENROUTER_API_KEY o GROQ_API_KEY no encontrada", file=sys.stderr)
    sys.exit(1)


def _validate_image(path: Path) -> str:
    if not path.exists():
        print(f"Error: archivo no encontrado: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        img = Image.open(path)
        img.verify()
        fmt = img.format
        if fmt not in ("JPEG", "PNG", "WEBP", "GIF", "BMP"):
            print(f"Error: formato {fmt} no soportado (JPG, PNG, WEBP, GIF, BMP)", file=sys.stderr)
            sys.exit(1)
        return fmt
    except Exception as e:
        print(f"Error: archivo no es imagen valida: {e}", file=sys.stderr)
        sys.exit(1)


def _call_vision(prompt: str, img_b64: str, mime: str) -> str:
    api_key = _api_key()
    payload = {
        "model": VISION_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}}
        ]}],
        "max_tokens": 2048,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
               "HTTP-Referer": "https://github.com/brain-ai-01", "X-Title": "brain-ai-01"}
    r = httpx.post(OPENROUTER_API, json=payload, headers=headers, timeout=120)
    if r.status_code != 200:
        print(f"Error vision API ({r.status_code}): {r.text[:300]}", file=sys.stderr)
        sys.exit(1)
    return r.json()["choices"][0]["message"]["content"]


def _describe_image(image_path: Path, prompt: str, detail_level: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    suffix = image_path.suffix.lower()
    mime = "image/png" if suffix in (".png",) else "image/jpeg"

    desc = _call_vision(prompt, b64, mime)

    if detail_level == "full":
        followup = _call_vision(
            "Basado en la misma imagen, responde SOLO esta pregunta: "
            "?Que detalle importante no mencione antes? "
            "Enfocate en: color exacto de ojos, color de pelo, "
            "edad aparente, y cualquier detalle facial que haya omitido.",
            b64, mime
        )
        desc = desc + "\n\n[DETALLES ADICIONALES]\n" + followup

    return desc


def main():
    p = argparse.ArgumentParser(description="Pre-procesador: imagen → episodio en memoria")
    p.add_argument("image", type=str, help="Ruta a la imagen")
    p.add_argument("--project", "-p", default="brain-ai-01", help="Nombre del proyecto")
    p.add_argument("--prompt", "-P", default=None, help="Prompt personalizado (reemplaza --detail)")
    p.add_argument("--detail", "-d", default="basico", choices=list(DEFAULT_PROMPTS.keys()),
                   help="Nivel de detalle: basico, facial (solo rostro), full (completo + refuerzo)")
    p.add_argument("--statement", "-s", default=None, help="Texto de decision (ej: 'Esta persona es Seiji')")
    p.add_argument("--author", "-a", default="seiji", help="Autor del episodio")
    p.add_argument("--tags", "-t", default="imagen", help="Tags separados por coma")
    p.add_argument("--title", "-T", default=None, help="Titulo del episodio")
    p.add_argument("--consolidate", "-c", action="store_true", help="Consolidar despues de ingestar")
    args = p.parse_args()

    image_path = Path(args.image)

    # Validar
    fmt = _validate_image(image_path)
    print(f"[OK] Imagen: {image_path.name} ({fmt})")

    # Seleccionar prompt y describir
    prompt = args.prompt or DEFAULT_PROMPTS[args.detail]
    detail_label = args.detail if not args.prompt else "personalizado"
    print(f"[...] Describiendo (modo: {detail_label}) via {VISION_MODEL}...")
    desc = _describe_image(image_path, prompt, args.detail)
    print(f"[OK] Descripcion ({len(desc)} chars): {desc[:120]}...")

    # Guardar copia
    media_path = save_media(image_path, args.project, IMAGES_DIR)
    rel_path = media_path.relative_to(media_path.parent.parent.parent)
    print(f"[OK] Copia: {rel_path}")

    # Construir episodio
    ep_titl = args.title or f"Imagen: {image_path.name}"
    ep = build_episode(
        project=args.project,
        source_type="image",
        author=args.author,
        title=ep_titl,
        summary=desc,
        decisions=[{"text": args.statement}] if args.statement else None,
        evidence=[{"type": "image", "url_or_path": str(rel_path), "excerpt": desc[:300]}],
        tags=[t.strip() for t in args.tags.split(",") if t.strip()],
    )

    # Ingestar
    print("Ingestando en memoria...")
    res = mcp_ingest(ep)
    print(json.dumps(res, ensure_ascii=False, indent=2))

    # Consolidar opcional
    if args.consolidate:
        print("Consolidando...")
        cr = httpx.post(f"{MCP_URL}/consolidate", json={"project": args.project}, timeout=60)
        print(json.dumps(cr.json(), ensure_ascii=False, indent=2))

    print("[OK] Listo!")


if __name__ == "__main__":
    main()
