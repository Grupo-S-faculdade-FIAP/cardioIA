"""PostToolUse: valida o contrato da base de conhecimento ao editar fase2/knowledge_base/*.csv.

Sai com código 2 (feedback para o Claude) se o contrato do SDD §3 for violado
ou se o mapa_conhecimento.csv derivado estiver desatualizado.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TESTES = ["fase2/tests/test_base_conhecimento.py", "fase2/tests/test_mapa_conhecimento.py"]

sys.stderr.reconfigure(encoding="utf-8")

evento = json.load(sys.stdin)
caminho = (evento.get("tool_input") or {}).get("file_path", "").replace("\\", "/")

if "fase2/knowledge_base/" not in caminho or not caminho.endswith(".csv"):
    sys.exit(0)

resultado = subprocess.run(
    [sys.executable, "-m", "pytest", *TESTES, "-q", "--no-header", "-p", "no:cacheprovider"],
    cwd=RAIZ,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
)

if resultado.returncode != 0:
    sys.stderr.write(
        "Base de conhecimento violou o contrato (SDD §3) após esta edição:\n"
        + resultado.stdout[-3000:]
    )
    sys.exit(2)
