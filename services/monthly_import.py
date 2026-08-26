"""Importação segura de uma janela mensal para o histórico local."""

from __future__ import annotations

from calendar import monthrange
from pathlib import Path

import pandas as pd

from config_ssids import SSIDS_INSTITUCIONAIS
from services.parser_fortianalyzer import ler_exportacao_fortianalyzer

COLUNAS_PERSISTIDAS = [
    "data_hora",
    "action",
    "ap",
    "ssid",
    "dispositivo_id",
    "channel",
    "signal",
    "snr",
    "radioid",
    "radioband",
    "security",
    "evento_relevante",
    "banda",
    "possui_ip",
    "registro_id",
]


def filtrar_mes(dados: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    """Mantém apenas o mês e os SSIDs institucionais, sem campos desnecessários."""
    if mes < 1 or mes > 12:
        raise ValueError("O mês deve estar entre 1 e 12.")

    inicio = pd.Timestamp(year=ano, month=mes, day=1)
    ultimo_dia = monthrange(ano, mes)[1]
    fim = pd.Timestamp(year=ano, month=mes, day=ultimo_dia) + pd.Timedelta(days=1)
    filtrado = dados[
        (dados["data_hora"] >= inicio)
        & (dados["data_hora"] < fim)
        & dados["ssid"].isin(SSIDS_INSTITUCIONAIS)
    ].copy()
    colunas = [coluna for coluna in COLUNAS_PERSISTIDAS if coluna in filtrado.columns]
    filtrado = filtrado[colunas]
    if "registro_id" in filtrado:
        filtrado = filtrado.drop_duplicates("registro_id")
    return filtrado.sort_values("data_hora").reset_index(drop=True)


def importar_mes(origem: str | Path, destino: str | Path, ano: int, mes: int) -> pd.DataFrame:
    """Lê, anonimiza em memória e grava somente o recorte mensal solicitado."""
    dados = ler_exportacao_fortianalyzer(origem)
    filtrado = filtrar_mes(dados, ano, mes)
    if filtrado.empty:
        periodo = f"{mes:02d}/{ano}"
        raise ValueError(f"O arquivo não contém registros institucionais em {periodo}.")

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    filtrado.to_pickle(destino)
    return filtrado

