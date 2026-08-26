import pandas as pd
import pytest

from services.monthly_import import filtrar_mes


def test_filtra_mes_ssid_e_colunas_sensiveis():
    dados = pd.DataFrame(
        {
            "data_hora": pd.to_datetime(["2026-07-15", "2026-08-01", "2026-07-20"]),
            "ssid": ["SBPC2026", "SBPC2026", "REDE-EXTERNA"],
            "dispositivo_id": ["anon-1", "anon-2", "anon-3"],
            "registro_id": ["r1", "r2", "r3"],
            "ap": ["AP-1", "AP-1", "AP-2"],
            "campo_desnecessario": ["x", "y", "z"],
        }
    )
    resultado = filtrar_mes(dados, 2026, 7)
    assert len(resultado) == 1
    assert resultado.iloc[0]["registro_id"] == "r1"
    assert "campo_desnecessario" not in resultado.columns


def test_rejeita_mes_invalido():
    with pytest.raises(ValueError, match="entre 1 e 12"):
        filtrar_mes(pd.DataFrame(), 2026, 13)

