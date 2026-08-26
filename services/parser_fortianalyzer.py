from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

CAMPOS_PERMITIDOS = {
    "date",
    "time",
    "eventtime",
    "action",
    "ap",
    "ssid",
    "stamac",
    "radioid",
    "radioband",
    "channel",
    "signal",
    "snr",
    "srcip",
    "logdesc",
    "reason",
    "security",
    "sn",
    "vap",
    "level",
    "msg",
}

EVENTOS_RELEVANTES = {
    "client-authentication",
    "client-ip-detected",
    "deauth",
    "layer3-roaming-rehome",
    "client-association-failure",
}


def _abrir_texto(caminho: Path):
    if caminho.suffix.lower() == ".gz":
        return gzip.open(caminho, "rt", encoding="utf-8-sig", errors="replace", newline="")
    return caminho.open("r", encoding="utf-8-sig", errors="replace", newline="")


def _normalizar_valor(valor: str) -> str:
    valor = valor.strip()
    if len(valor) >= 2 and valor[0] == '"' and valor[-1] == '"':
        valor = valor[1:-1]
    return valor.replace(r"\"", '"').strip()


def _parse_celula(celula: str):
    celula = celula.strip()
    if "=" not in celula:
        return None, None
    chave, valor = celula.split("=", 1)
    chave = chave.strip()
    if not re.fullmatch(r"[A-Za-z0-9_]+", chave):
        return None, None
    return chave, _normalizar_valor(valor)


def _obter_segredo_hash() -> str:
    segredo = os.getenv("WIFI_HASH_SALT", "").strip()
    if len(segredo) < 16:
        raise RuntimeError(
            "Defina WIFI_HASH_SALT com pelo menos 16 caracteres antes de importar logs. "
            "Nunca publique esse segredo no repositório."
        )
    return segredo


def _hash_dispositivo(mac: str, segredo: str | None = None) -> str:
    if not mac:
        return ""
    segredo = segredo or _obter_segredo_hash()
    return hashlib.sha256(f"{segredo}|{mac.lower()}".encode()).hexdigest()[:16]


def _hash_registro(registro: dict) -> str:
    campos = [
        str(registro.get("eventtime", "")),
        str(registro.get("date", "")),
        str(registro.get("time", "")),
        str(registro.get("action", "")),
        str(registro.get("ap", "")),
        str(registro.get("ssid", "")),
        str(registro.get("dispositivo_id", "")),
        str(registro.get("channel", "")),
        str(registro.get("radioid", "")),
    ]
    return hashlib.sha256("|".join(campos).encode("utf-8")).hexdigest()[:24]


def _identificar_banda(linha: pd.Series) -> str:
    canal = linha.get("channel")
    radio = str(linha.get("radioband", "") or "").lower()

    if pd.notna(canal):
        try:
            canal = int(float(canal))
            return "2,4 GHz" if canal <= 14 else "5 GHz"
        except (ValueError, TypeError):
            pass

    if "11ac" in radio or "11a" in radio:
        return "5 GHz"
    if "11g" in radio or "11b" in radio:
        return "2,4 GHz"
    return "Não identificado"


def ler_exportacao_fortianalyzer(caminho: str | Path) -> pd.DataFrame:
    caminho = Path(caminho)
    registros = []

    with _abrir_texto(caminho) as arquivo:
        leitor = csv.reader(arquivo)
        for linha in leitor:
            registro = {}
            for celula in linha:
                chave, valor = _parse_celula(celula)
                if chave and chave in CAMPOS_PERMITIDOS:
                    registro[chave] = valor

            if not registro:
                continue

            mac = registro.pop("stamac", "")
            registro["dispositivo_id"] = _hash_dispositivo(mac)
            registro["possui_ip"] = bool(registro.pop("srcip", ""))
            registro.pop("msg", None)
            registro["registro_id"] = _hash_registro(registro)
            registros.append(registro)

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)

    for coluna in ["date", "time", "action", "ap", "ssid", "radioband", "security"]:
        if coluna not in df.columns:
            df[coluna] = ""

    df["data_hora"] = pd.to_datetime(
        df["date"].fillna("") + " " + df["time"].fillna(""),
        errors="coerce",
    )

    for coluna in ["channel", "signal", "snr", "radioid"]:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    df["evento_relevante"] = df["action"].isin(EVENTOS_RELEVANTES)
    df["banda"] = df.apply(_identificar_banda, axis=1)
    return df


def _historico_path(pasta_historico: Path) -> Path:
    return pasta_historico / "wifi_historico.pkl"


def importar_novos_arquivos(
    pasta_importar: str | Path = "data/importar",
    pasta_historico: str | Path = "data/historico",
    pasta_arquivados: str | Path = "data/arquivados",
    pasta_rejeitados: str | Path = "data/rejeitados",
) -> dict:
    pasta_importar = Path(pasta_importar)
    pasta_historico = Path(pasta_historico)
    pasta_arquivados = Path(pasta_arquivados)
    pasta_rejeitados = Path(pasta_rejeitados)

    for pasta in [pasta_importar, pasta_historico, pasta_arquivados, pasta_rejeitados]:
        pasta.mkdir(parents=True, exist_ok=True)

    historico_path = _historico_path(pasta_historico)
    manifest_path = pasta_historico / "manifesto_importacao.json"

    historico = pd.read_pickle(historico_path) if historico_path.exists() else pd.DataFrame()

    arquivos = sorted(list(pasta_importar.glob("*.csv")) + list(pasta_importar.glob("*.csv.gz")))

    # Valida a configuração antes do processamento para não mover um arquivo
    # válido para rejeitados apenas porque o ambiente ainda não foi configurado.
    if arquivos:
        _obter_segredo_hash()

    resumo = {
        "arquivos_encontrados": len(arquivos),
        "arquivos_importados": 0,
        "arquivos_rejeitados": 0,
        "registros_lidos": 0,
        "registros_novos": 0,
        "duplicados_descartados": 0,
        "detalhes": [],
    }

    partes = []

    for arquivo in arquivos:
        try:
            df = ler_exportacao_fortianalyzer(arquivo)
            if df.empty:
                raise ValueError("Nenhum registro FortiAnalyzer reconhecido.")

            df["arquivo_origem"] = arquivo.name
            df["importado_em"] = pd.Timestamp.now()
            resumo["registros_lidos"] += len(df)
            partes.append(df)

            carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino = pasta_arquivados / f"{carimbo}_{arquivo.name}"
            contador = 1
            while destino.exists():
                destino = pasta_arquivados / f"{carimbo}_{contador}_{arquivo.name}"
                contador += 1

            shutil.move(str(arquivo), str(destino))
            resumo["arquivos_importados"] += 1
            resumo["detalhes"].append(
                {
                    "arquivo": arquivo.name,
                    "status": "importado",
                    "registros": len(df),
                    "arquivado_como": destino.name,
                }
            )

        except Exception as exc:  # noqa: BLE001 - um arquivo inválido não interrompe o lote
            carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino = pasta_rejeitados / f"{carimbo}_{arquivo.name}"
            contador = 1
            while destino.exists():
                destino = pasta_rejeitados / f"{carimbo}_{contador}_{arquivo.name}"
                contador += 1
            shutil.move(str(arquivo), str(destino))
            resumo["arquivos_rejeitados"] += 1
            resumo["detalhes"].append(
                {
                    "arquivo": arquivo.name,
                    "status": "rejeitado",
                    "erro": str(exc),
                }
            )

    if partes:
        novos = pd.concat(partes, ignore_index=True)
        antes = len(novos)
        novos = novos.drop_duplicates(subset=["registro_id"], keep="first")
        resumo["duplicados_descartados"] += antes - len(novos)

        if not historico.empty:
            ids_existentes = set(historico["registro_id"].astype(str))
            mascara = ~novos["registro_id"].astype(str).isin(ids_existentes)
            resumo["duplicados_descartados"] += int((~mascara).sum())
            novos = novos[mascara]

        resumo["registros_novos"] = len(novos)

        if historico.empty:
            historico = novos.copy()
        elif not novos.empty:
            historico = pd.concat([historico, novos], ignore_index=True)

        historico = historico.sort_values("data_hora")
        historico.to_pickle(historico_path)

    manifest = {
        "ultima_execucao": datetime.now().isoformat(timespec="seconds"),
        "total_registros_historico": len(historico),
        **resumo,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    resumo["total_registros_historico"] = len(historico)
    return resumo


def carregar_historico(pasta_historico: str | Path = "data/historico") -> pd.DataFrame:
    caminho = _historico_path(Path(pasta_historico))
    if not caminho.exists():
        return pd.DataFrame()
    return pd.read_pickle(caminho)

