"""CLI para importar um único mês sem persistir dados brutos."""

from __future__ import annotations

import argparse
from pathlib import Path

from services.monthly_import import importar_mes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="CSV ou CSV.GZ exportado do FortiAnalyzer")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/historico/wifi_historico.pkl"),
    )
    args = parser.parse_args()

    dados = importar_mes(args.source, args.output, args.year, args.month)
    print(
        f"Importação concluída: {len(dados):,} eventos anonimizados, "
        f"{dados['dispositivo_id'].nunique():,} dispositivos."
    )


if __name__ == "__main__":
    main()

