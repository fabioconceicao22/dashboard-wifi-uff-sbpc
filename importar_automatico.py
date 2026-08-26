from datetime import datetime
from pathlib import Path

from services.parser_fortianalyzer import importar_novos_arquivos


LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "importacao_automatica.log"


def registrar(mensagem: str) -> None:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as arquivo:
        arquivo.write(f"[{agora}] {mensagem}\n")


try:
    resumo = importar_novos_arquivos()
    registrar(
        "Importação concluída: "
        f"{resumo['arquivos_importados']} arquivo(s), "
        f"{resumo['registros_novos']} registro(s) novo(s), "
        f"{resumo['duplicados_descartados']} duplicado(s)."
    )
except Exception as exc:
    registrar(f"ERRO: {exc}")
    raise

