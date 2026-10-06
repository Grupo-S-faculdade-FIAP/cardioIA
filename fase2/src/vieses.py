"""Ferramentas para medir vieses do extrator e do classificador (SDD Fase 2, §6)."""

import re

# Adjetivos que concordam com o gênero de quem relata ("estou cansado/cansada").
# Ficam de fora palavras que costumam concordar com partes do corpo ou com
# outros substantivos ("pernas inchadas", "dor fraca").
PARES_GENERO = [
    ("cansado", "cansada"),
    ("tonto", "tonta"),
    ("pálido", "pálida"),
    ("sentado", "sentada"),
    ("deitado", "deitada"),
    ("parado", "parada"),
    ("nervoso", "nervosa"),
    ("enjoado", "enjoada"),
    ("suado", "suada"),
    ("preocupado", "preocupada"),
    ("zonzo", "zonza"),
    ("exausto", "exausta"),
    ("esgotado", "esgotada"),
    ("assustado", "assustada"),
    ("acordado", "acordada"),
]

_TROCAS = {
    **{masculino: feminino for masculino, feminino in PARES_GENERO},
    **{feminino: masculino for masculino, feminino in PARES_GENERO},
}
_PADRAO_GENERO = re.compile(r"\b(" + "|".join(_TROCAS) + r")\b", re.IGNORECASE)


def tem_marca_de_genero(texto):
    """Indica se o texto tem algum adjetivo flexionado no gênero de quem relata."""
    return _PADRAO_GENERO.search(texto) is not None


def trocar_genero(texto):
    """Troca o gênero gramatical de quem relata: 'fiquei tonto' ↔ 'fiquei tonta'."""

    def _trocar(achado):
        palavra = achado.group(0)
        nova = _TROCAS[palavra.lower()]
        return nova.capitalize() if palavra[0].isupper() else nova

    return _PADRAO_GENERO.sub(_trocar, texto)
