"""Embeddings por API de OpenAI (text-embedding-3-small).

Copiado de HW_03_202602 (comun/embeddings.py). Cambios:
- Solo queda la implementación OpenAI: el despliegue en Streamlit Cloud no lleva torch.
- Se mantiene la clase base `Embedder`: si algún día se agrega otro modelo, el resto del
  código no cambia (solo `embeddings.modelo_activo` en config.yaml).
"""
import os
import time

import numpy as np

from src.costos import ahora_utc, calcular_costo, limpiar_error, registrar_llamada


class Embedder:
    """Interfaz común. Devuelve vectores normalizados (producto punto = similitud coseno)."""

    nombre: str
    alias: str
    dimension: int

    def embed_pasajes(self, textos: list[str]) -> np.ndarray:
        raise NotImplementedError

    def embed_consulta(self, texto: str) -> np.ndarray:
        raise NotImplementedError

    def contar_tokens(self, texto: str) -> int:
        raise NotImplementedError


class EmbedderOpenAI(Embedder):
    """text-embedding-3-small por API. Cada llamada cuesta dinero y queda en logs/costos_llm.csv."""

    def __init__(self, mcfg: dict, cfg: dict):
        from dotenv import load_dotenv
        from openai import OpenAI
        import tiktoken

        load_dotenv()
        self.nombre, self.alias, self.lote = mcfg["nombre"], mcfg["alias"], mcfg["lote"]
        self.cliente = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.tokenizador = tiktoken.get_encoding("cl100k_base")
        self.dimension = 1536
        self.cfg = cfg
        self.tokens_usados = 0
        self.costo_usd = 0.0

    def _llamar(self, textos):
        """Cada llamada se registra en el log de costos, con éxito o error."""
        momento, inicio = ahora_utc(), time.time()
        fila = {"fecha_hora_utc": momento.isoformat(timespec="seconds"), "modelo": self.nombre,
                "pregunta": f"[embeddings] lote de {len(textos)} textos"}
        try:
            r = self.cliente.embeddings.create(model=self.nombre, input=textos)
        except Exception as ex:
            fila.update(latencia_s=round(time.time() - inicio, 3), exito=False, error=limpiar_error(ex))
            registrar_llamada(self.cfg, fila)
            raise
        self.ultima_latencia = time.time() - inicio
        tokens = r.usage.total_tokens
        costo, franja = calcular_costo(self.cfg, self.nombre, momento, tokens, 0)
        self.tokens_usados += tokens
        self.costo_usd += costo
        fila.update(tokens_entrada=tokens, tokens_salida=0, latencia_s=round(self.ultima_latencia, 3),
                    costo_usd=f"{costo:.8f}", franja=franja, exito=True)
        registrar_llamada(self.cfg, fila)
        return np.array([d.embedding for d in r.data], dtype=np.float32)

    def embed_pasajes(self, textos):
        partes = [self._llamar(textos[i:i + self.lote]) for i in range(0, len(textos), self.lote)]
        return np.vstack(partes)

    def embed_consulta(self, texto):
        return self._llamar([texto])[0]

    def contar_tokens(self, texto):
        return len(self.tokenizador.encode(texto))


def crear_embedder(cfg: dict, modelo: str | None = None) -> Embedder:
    """`modelo` = clave en cfg['embeddings']['modelos'] (por defecto, el modelo activo)."""
    clave = modelo or cfg["embeddings"]["modelo_activo"]
    mcfg = cfg["embeddings"]["modelos"][clave]
    if mcfg["tipo"] == "openai":
        return EmbedderOpenAI(mcfg, cfg)
    raise ValueError(f"Tipo de embeddings desconocido: {mcfg['tipo']}")
