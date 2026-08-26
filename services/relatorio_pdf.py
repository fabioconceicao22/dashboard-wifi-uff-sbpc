from __future__ import annotations

from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

AZUL = "#075DB8"
AZUL_ESCURO = "#06447E"
AZUL_CLARO = "#EAF4FF"
TEXTO = "#173B5E"
CINZA = "#64748B"


def _numero(v):
    return f"{v:,.0f}".replace(",", ".")


def _duracao(segundos):
    segundos = max(0, int(segundos))
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _png(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _grafico_ssid(dados):
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    d = dados.sort_values("clientes")
    ax.barh(d["ssid"], d["clientes"], color=AZUL)
    ax.set_title("Clientes distintos por SSID", loc="left", fontweight="bold")
    ax.set_xlabel("Clientes")
    ax.grid(axis="x", alpha=0.25)
    for i, v in enumerate(d["clientes"]):
        ax.text(v, i, f" {_numero(v)}", va="center", fontsize=8)
    fig.tight_layout()
    return _png(fig)


def _grafico_tempo(dados, granularidade):
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    d = dados.sort_values("intervalo")
    if len(d) == 1:
        ax.bar(d["intervalo"].dt.strftime("%H:%M"), d["clientes"], color=AZUL)
    else:
        ax.plot(d["intervalo"], d["clientes"], marker="o", color=AZUL, linewidth=2)
        fig.autofmt_xdate(rotation=30)
    ax.set_title(f"Clientes observados no tempo ({granularidade})", loc="left", fontweight="bold")
    ax.set_ylabel("Clientes")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return _png(fig)


def _grafico_ap(dados):
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    d = dados.head(10).sort_values("clientes")
    ax.barh(d["ap"], d["clientes"], color=AZUL)
    ax.set_title("Top 10 pontos de acesso", loc="left", fontweight="bold")
    ax.set_xlabel("Clientes")
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(axis="x", alpha=0.25)
    for i, v in enumerate(d["clientes"]):
        ax.text(v, i, f" {_numero(v)}", va="center", fontsize=8)
    fig.tight_layout()
    return _png(fig)


def gerar_relatorio_pdf(
    *,
    filtrado,
    inicio,
    fim,
    granularidade,
    clientes_nos_ssids,
    dispositivos_unicos_gerais,
    pico,
    horario_pico,
    ssid_lider,
    ssid_lider_pct,
    ap_lider,
    ap_lider_n,
    tempo_medio,
    ssid_eventos_lider,
    ssids_selecionados,
    logo_path=None,
):
    saida = BytesIO()
    doc = SimpleDocTemplate(
        saida,
        pagesize=A4,
        leftMargin=1.3 * cm,
        rightMargin=1.3 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
        title="Relatório de Monitoramento Wi-Fi Institucional - UFF",
        author="Universidade Federal Fluminense",
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TituloUFF",
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            textColor=colors.HexColor(AZUL_ESCURO),
        )
    )
    styles.add(
        ParagraphStyle(name="SubUFF", fontSize=9.5, leading=13, textColor=colors.HexColor(CINZA))
    )
    styles.add(
        ParagraphStyle(
            name="SecaoUFF",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor(AZUL_ESCURO),
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(name="CorpoUFF", fontSize=9.2, leading=14, textColor=colors.HexColor(TEXTO))
    )
    styles.add(
        ParagraphStyle(
            name="KPI",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            alignment=1,
            textColor=colors.HexColor(AZUL_ESCURO),
        )
    )
    styles.add(
        ParagraphStyle(
            name="KPILabel",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            alignment=1,
            textColor=colors.HexColor(AZUL),
        )
    )

    story = []
    logo = ""
    if logo_path and Path(logo_path).exists():
        logo = Image(str(logo_path), width=4.8 * cm, height=1.55 * cm)

    cabecalho = Table(
        [
            [
                logo,
                [
                    Paragraph(
                        "Relatório de Monitoramento Wi-Fi Institucional", styles["TituloUFF"]
                    ),
                    Paragraph(
                        "Universidade Federal Fluminense - FortiGate 1500D - FortiAnalyzer 7.4.3",
                        styles["SubUFF"],
                    ),
                ],
            ]
        ],
        colWidths=[5.2 * cm, 12.2 * cm],
    )
    cabecalho.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 2, colors.HexColor(AZUL)),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(cabecalho)
    story.append(Spacer(1, 0.2 * cm))

    periodo = (
        f"<b>Período:</b> {inicio:%d/%m/%Y %H:%M} até {(fim - pd.Timedelta(seconds=1)):%d/%m/%Y %H:%M}<br/>"
        f"<b>SSIDs:</b> {', '.join(ssids_selecionados)}<br/>"
        f"<b>Granularidade:</b> {granularidade}"
    )
    quadro_periodo = Table([[Paragraph(periodo, styles["CorpoUFF"])]], colWidths=[17.4 * cm])
    quadro_periodo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(AZUL_CLARO)),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#BBDCF8")),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(quadro_periodo)
    story.append(Spacer(1, 0.25 * cm))

    kpis = [
        ("Clientes nos SSIDs", _numero(clientes_nos_ssids)),
        ("Únicos gerais", _numero(dispositivos_unicos_gerais)),
        ("Pico observado", _numero(pico)),
        ("Horário do pico", horario_pico.strftime("%H:%M")),
        ("SSID líder", ssid_lider),
        ("AP líder", ap_lider),
    ]
    celulas = [
        [Paragraph(rotulo, styles["KPILabel"]), Paragraph(str(valor), styles["KPI"])]
        for rotulo, valor in kpis
    ]
    tabela_kpi = Table(
        [celulas[:3], celulas[3:]], colWidths=[5.8 * cm] * 3, rowHeights=[1.75 * cm] * 2
    )
    tabela_kpi.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D9E6F2")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E6F2")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(tabela_kpi)

    story.append(Paragraph("Resumo executivo", styles["SecaoUFF"]))
    resumo = (
        f"Foram contabilizados <b>{_numero(clientes_nos_ssids)}</b> clientes distintos somados entre os SSIDs e "
        f"<b>{_numero(dispositivos_unicos_gerais)}</b> dispositivos únicos gerais. O maior volume ocorreu às "
        f"<b>{horario_pico:%H:%M}</b>, com <b>{_numero(pico)}</b> clientes no intervalo de <b>{granularidade}</b>. "
        f"O SSID líder foi <b>{ssid_lider}</b>, com <b>{ssid_lider_pct:.1f}%</b> da soma. O AP de maior concentração "
        f"foi <b>{ap_lider}</b>, com <b>{_numero(ap_lider_n)}</b> clientes. O tempo médio observado foi de "
        f"<b>{_duracao(tempo_medio)}</b> (estimativa). O SSID <b>{ssid_eventos_lider}</b> apresentou a maior relação de eventos por cliente."
    )
    story.append(Paragraph(resumo, styles["CorpoUFF"]))

    ssid_df = (
        filtrado.groupby("ssid")
        .agg(clientes=("dispositivo_id", "nunique"), eventos=("action", "size"))
        .reset_index()
        .sort_values("clientes", ascending=False)
    )
    ssid_df["eventos_por_cliente"] = (
        ssid_df["eventos"] / ssid_df["clientes"].replace(0, pd.NA)
    ).round(2)
    ssid_df["participacao"] = (ssid_df["clientes"] / max(clientes_nos_ssids, 1) * 100).round(1)

    ap_df = (
        filtrado.groupby("ap")
        .agg(clientes=("dispositivo_id", "nunique"), eventos=("action", "size"))
        .reset_index()
        .sort_values(["clientes", "eventos"], ascending=False)
    )

    freq = {
        "1 minuto": "1min",
        "5 minutos": "5min",
        "15 minutos": "15min",
        "30 minutos": "30min",
        "1 hora": "1h",
    }.get(granularidade, "5min")
    temp = filtrado.copy()
    temp["intervalo"] = temp["data_hora"].dt.floor(freq)
    temp = (
        temp.groupby(["intervalo", "ssid"])["dispositivo_id"]
        .nunique()
        .reset_index(name="clientes")
        .groupby("intervalo")["clientes"]
        .sum()
        .reset_index()
    )

    story.append(Paragraph("Indicadores por SSID", styles["SecaoUFF"]))
    dados_tabela = [["SSID", "Clientes", "Eventos", "Eventos/cliente", "Participação"]]
    for r in ssid_df.itertuples(index=False):
        dados_tabela.append(
            [
                str(r.ssid),
                _numero(r.clientes),
                _numero(r.eventos),
                f"{r.eventos_por_cliente:.2f}",
                f"{r.participacao:.1f}%",
            ]
        )
    tabela = Table(
        dados_tabela, colWidths=[5.1 * cm, 2.4 * cm, 2.4 * cm, 3.2 * cm, 2.7 * cm], repeatRows=1
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(AZUL)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D9E6F2")),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFD")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(tabela)
    story.append(Spacer(1, 0.2 * cm))
    story.append(Image(_grafico_ssid(ssid_df), width=17.1 * cm, height=7.0 * cm))

    story.append(PageBreak())
    story.append(Paragraph("Evolução temporal", styles["SecaoUFF"]))
    story.append(Image(_grafico_tempo(temp, granularidade), width=17.1 * cm, height=7.0 * cm))

    story.append(Paragraph("Pontos de acesso com maior concentração", styles["SecaoUFF"]))
    dados_ap = [["Posição", "Ponto de acesso", "Clientes", "Eventos"]]
    for pos, r in enumerate(ap_df.head(10).itertuples(index=False), 1):
        dados_ap.append([str(pos), str(r.ap), _numero(r.clientes), _numero(r.eventos)])
    tabela_ap = Table(dados_ap, colWidths=[1.7 * cm, 10.1 * cm, 2.7 * cm, 2.7 * cm], repeatRows=1)
    tabela_ap.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(AZUL)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D9E6F2")),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFD")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(tabela_ap)
    story.append(Spacer(1, 0.2 * cm))
    story.append(Image(_grafico_ap(ap_df), width=17.1 * cm, height=8.0 * cm))

    story.append(PageBreak())
    story.append(Paragraph("Metodologia e proteção de dados", styles["SecaoUFF"]))
    observacoes = [
        "<b>Clientes nos SSIDs:</b> soma dos dispositivos distintos de cada SSID selecionado.",
        "<b>Únicos gerais:</b> elimina repetição do mesmo dispositivo entre SSIDs.",
        "<b>Pico observado:</b> soma por SSID dentro do intervalo escolhido.",
        "<b>Tempo médio:</b> estimativa baseada na sequência de eventos, limitada a 30 minutos por intervalo.",
        "<b>Limitação:</b> logs de eventos não equivalem ao inventário instantâneo do FortiGate.",
        "<b>LGPD:</b> não são exibidos nome, CPF, e-mail, MAC original ou IP completo.",
    ]
    for item in observacoes:
        story.append(Paragraph("• " + item, styles["CorpoUFF"]))
        story.append(Spacer(1, 0.08 * cm))

    def rodape(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#BBDCF8"))
        canvas.line(1.3 * cm, 0.85 * cm, 19.7 * cm, 0.85 * cm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(CINZA))
        canvas.drawString(
            1.3 * cm,
            0.5 * cm,
            "Universidade Federal Fluminense - Monitoramento Wi-Fi Institucional",
        )
        canvas.drawRightString(19.7 * cm, 0.5 * cm, f"Página {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=rodape, onLaterPages=rodape)
    saida.seek(0)
    return saida.getvalue()

