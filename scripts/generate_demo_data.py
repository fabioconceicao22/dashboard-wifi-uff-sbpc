"""Gera uma base sintética e reprodutível para a demonstração pública."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SSIDS = ["eduroam", "VISITANTE-UFF", "SBPC2026", "SBPC", "PREFEITO", "PR_Niteroi"]
APS = [f"AP-DEMO-{andar:02d}-{numero:02d}" for andar in range(1, 5) for numero in range(1, 7)]


def _id_sintetico(numero: int) -> str:
    return hashlib.sha256(f"dispositivo-demo-{numero}".encode()).hexdigest()[:16]


def gerar(seed: int = 2026) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    inicio = pd.Timestamp("2026-07-26 08:00:00")
    fim = pd.Timestamp("2026-07-26 20:00:00")
    instantes = pd.date_range(inicio, fim, freq="5min", inclusive="left")
    pesos_ssid = np.array([0.46, 0.20, 0.17, 0.10, 0.04, 0.03])
    registros: list[dict] = []

    for instante in instantes:
        hora = instante.hour + instante.minute / 60
        pico = np.exp(-((hora - 14.0) ** 2) / 7.0)
        ativos = int(85 + 230 * pico + rng.normal(0, 12))
        ativos = max(45, ativos)
        ids = rng.choice(520, size=min(ativos, 520), replace=False)

        for numero in ids:
            ssid = rng.choice(SSIDS, p=pesos_ssid)
            banda = rng.choice(["2,4 GHz", "5 GHz"], p=[0.28, 0.72])
            sinal = int(np.clip(rng.normal(-61 if banda == "5 GHz" else -67, 9), -92, -35))
            snr = int(np.clip(rng.normal(27, 8), 5, 55))
            registros.append(
                {
                    "data_hora": instante + pd.Timedelta(seconds=int(rng.integers(0, 300))),
                    "ssid": ssid,
                    "ap": rng.choice(APS),
                    "dispositivo_id": _id_sintetico(int(numero)),
                    "action": rng.choice(
                        [
                            "client-authentication",
                            "client-ip-detected",
                            "deauth",
                            "layer3-roaming-rehome",
                        ],
                        p=[0.48, 0.34, 0.12, 0.06],
                    ),
                    "signal": sinal,
                    "snr": snr,
                    "channel": int(
                        rng.choice([1, 6, 11] if banda == "2,4 GHz" else [36, 44, 149, 157])
                    ),
                    "radioid": 1 if banda == "2,4 GHz" else 2,
                    "radioband": "802.11g" if banda == "2,4 GHz" else "802.11ac",
                    "banda": banda,
                    "security": "WPA2-Enterprise",
                    "evento_relevante": True,
                    "possui_ip": bool(rng.integers(0, 2)),
                    "registro_id": hashlib.sha256(
                        f"{instante.isoformat()}-{numero}-{ssid}".encode()
                    ).hexdigest()[:24],
                    "arquivo_origem": "DEMO_SINTETICO",
                }
            )

    return pd.DataFrame(registros).sort_values("data_hora").reset_index(drop=True)


if __name__ == "__main__":
    destino = Path(__file__).resolve().parents[1] / "data" / "demo" / "wifi_demo.csv.gz"
    destino.parent.mkdir(parents=True, exist_ok=True)
    dados = gerar()
    dados.to_csv(destino, index=False, compression="gzip")
    print(f"Base sintética criada: {destino} ({len(dados):,} registros)")

