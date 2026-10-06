import pandas as pd
import pytest

from carregador_base import carregar_base_conhecimento, carregar_relatos

ALTO = ["dor forte no peito que não passa", "aperto no peito com suor frio",
        "desmaiei de repente na rua", "falta de ar mesmo parado"]
BAIXO = ["leve incômodo nas costas", "cansaço leve no fim do dia",
         "dor no joelho ao caminhar", "um pouco de sono depois do almoço"]


@pytest.fixture
def dataset_sintetico():
    """240 frases que cumprem o contrato do SDD §4 — não é dado do projeto."""
    linhas = [
        {
            "frase": f"{sintoma} há {n} dias",
            "situacao": rotulo,
            "origem": "manual" if n < 6 else "template",
            "particao": "teste" if n < 6 else "treino",
        }
        for rotulo, sintomas in (("alto risco", ALTO), ("baixo risco", BAIXO))
        for sintoma in sintomas
        for n in range(30)
    ]
    return pd.DataFrame(linhas)


@pytest.fixture
def caminho_dataset_sintetico(dataset_sintetico, tmp_path):
    caminho = tmp_path / "frases_risco.csv"
    dataset_sintetico.to_csv(caminho, index=False, encoding="utf-8")
    return caminho


@pytest.fixture(scope="session")
def base():
    return carregar_base_conhecimento()


@pytest.fixture(scope="session")
def relatos():
    return {relato["id"]: relato["texto"] for relato in carregar_relatos()}
