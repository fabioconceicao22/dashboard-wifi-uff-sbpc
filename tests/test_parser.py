from pathlib import Path

import pytest

from services.parser_fortianalyzer import _hash_dispositivo, ler_exportacao_fortianalyzer


def test_hash_e_deterministico_e_nao_expoe_mac():
    mac = "AA:BB:CC:DD:EE:FF"
    primeiro = _hash_dispositivo(mac, "segredo-de-teste-com-32-caracteres")
    segundo = _hash_dispositivo(mac, "segredo-de-teste-com-32-caracteres")
    assert primeiro == segundo
    assert mac.lower() not in primeiro
    assert len(primeiro) == 16


def test_importacao_exige_segredo(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("WIFI_HASH_SALT", raising=False)
    arquivo = tmp_path / "logs.csv"
    arquivo.write_text(
        "date=2026-07-26,time=10:00:00,action=client-authentication,ssid=SBPC2026,stamac=AA:BB:CC:DD:EE:FF",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="WIFI_HASH_SALT"):
        ler_exportacao_fortianalyzer(arquivo)


def test_parser_remove_mac_e_ip(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WIFI_HASH_SALT", "segredo-de-teste-com-32-caracteres")
    arquivo = tmp_path / "logs.csv"
    arquivo.write_text(
        "date=2026-07-26,time=10:00:00,action=client-authentication,ssid=SBPC2026,stamac=AA:BB:CC:DD:EE:FF,srcip=10.0.0.10",
        encoding="utf-8",
    )
    dados = ler_exportacao_fortianalyzer(arquivo)
    assert "stamac" not in dados.columns
    assert "srcip" not in dados.columns
    assert dados.loc[0, "possui_ip"]

