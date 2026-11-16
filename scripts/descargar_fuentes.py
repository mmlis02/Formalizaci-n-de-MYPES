"""Descarga los PDFs del corpus y los formularios a data/raw/.

- No vuelve a descargar un archivo que ya existe (se puede correr muchas veces).
- Guarda en data/manifiesto_descargas.json la fecha de descarga, el tamaño y la
  huella sha256 de cada archivo, para saber exactamente qué versión se usó.
- Si un enlace falla, lo anota en el manifiesto y sigue con los demás. Solo termina
  con error si falla un documento que va al índice (incluir: true) o un formulario.

Copiado de HW_03_202602 (tarea1_rag_normativo/scripts/descargar_fuentes.py) y
adaptado para descargar también los formularios.

Uso (desde la raíz del proyecto):
    python scripts/descargar_fuentes.py
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import cargar_config, ruta  # noqa: E402


def sha256(archivo: Path) -> str:
    return hashlib.sha256(archivo.read_bytes()).hexdigest()


def descargar(url: str, destino: Path, cfg: dict) -> None:
    """Baja un PDF; lanza un error si la respuesta no es un PDF."""
    cabeceras = {"User-Agent": cfg["descarga"]["user_agent"]}
    r = requests.get(url, headers=cabeceras, timeout=cfg["descarga"]["timeout_segundos"])
    r.raise_for_status()
    # Algunos portales devuelven una página HTML con código 200: se revisa la firma del PDF.
    if not r.content.startswith(b"%PDF"):
        raise ValueError("la respuesta no es un PDF (¿página HTML o bloqueada?)")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(r.content)


def main():
    cfg = cargar_config()
    carpeta_raw = ruta(cfg, "raw")
    ruta_manifiesto = ruta(cfg, "manifiesto_descargas")
    manifiesto = json.loads(ruta_manifiesto.read_text(encoding="utf-8")) if ruta_manifiesto.exists() else {}

    # Documentos del corpus y formularios se descargan igual; solo cambia si son obligatorios.
    entradas = [(d, "documento", d["incluir"]) for d in cfg["documentos"]]
    entradas += [(f, "formulario", True) for f in cfg["formularios"]]

    fallas_obligatorias = []
    for item, tipo, obligatorio in entradas:
        destino = carpeta_raw / item["archivo"]
        if destino.exists():
            print(f"[ya existe] {item['archivo']} ({destino.stat().st_size / 1e6:.2f} MB)")
        else:
            print(f"[descargando] {item['id']} ...")
            try:
                descargar(item["url_pdf"], destino, cfg)
            except Exception as e:  # noqa: BLE001 — se anota cualquier falla y se sigue
                print(f"   ERROR: {e}")
                manifiesto[item["id"]] = {
                    "tipo": tipo, "archivo": item["archivo"], "url_pdf": item["url_pdf"],
                    "error": str(e), "fecha_intento": datetime.now().isoformat(timespec="seconds"),
                }
                if obligatorio:
                    fallas_obligatorias.append(item["id"])
                continue
            print(f"   guardado {item['archivo']} ({destino.stat().st_size / 1e6:.2f} MB)")
            manifiesto[item["id"]] = {"fecha_descarga": datetime.now().isoformat(timespec="seconds")}

        # Siempre se actualizan tamaño y huella (por si alguien bajó el PDF a mano).
        info = manifiesto.setdefault(item["id"], {"fecha_descarga": "desconocida (descarga manual)"})
        info.pop("error", None)
        info.pop("fecha_intento", None)
        info.update({
            "tipo": tipo,
            "archivo": item["archivo"],
            "url_pdf": item["url_pdf"],
            "bytes": destino.stat().st_size,
            "sha256": sha256(destino),
        })

    # Se quitan entradas que ya no están en config.yaml
    ids = {item["id"] for item, _, _ in entradas}
    manifiesto = {k: v for k, v in manifiesto.items() if k in ids}
    ruta_manifiesto.write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Manifiesto actualizado: {ruta_manifiesto}")

    if fallas_obligatorias:
        print(f"FALTAN documentos obligatorios: {', '.join(fallas_obligatorias)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
