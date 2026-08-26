from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config_ssids import SSIDS_INSTITUCIONAIS
from services.parser_fortianalyzer import (
    carregar_historico,
    importar_novos_arquivos,
)
from services.relatorio_pdf import gerar_relatorio_pdf

st.set_page_config(
    page_title="Observatório Wi-Fi UFF | SBPC",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded",
)

AZUL = "#075DB8"
AZUL_ESCURO = "#06447E"
AZUL_CLARO = "#EAF4FF"
CINZA = "#64748B"

CORES_SSID = {
    "eduroam": "#075DB8",
    "VISITANTE-UFF": "#35BFE2",
    "SBPC2026": "#72D2E6",
    "SBPC": "#EF6C35",
    "PREFEITO": "#F2A23A",
    "PR_Niteroi": "#E0C72C",
}

st.markdown(
    """
    <style>
    :root {
        --uff-blue: #075DB8;
        --uff-blue-dark: #06447E;
        --uff-soft: #EAF4FF;
        --uff-border: #D9E6F2;
        --uff-text: #173B5E;
        --uff-muted: #64748B;
    }

    .stApp {
        background: #F7FAFD;
    }

    .block-container {
        max-width: 1800px;
        padding: 0 1rem 1.4rem 1rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F6FAFE 0%, #FFFFFF 100%);
        border-right: 1px solid #DCE8F3;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: .7rem;
    }

    .top-shell {
        background: #FFFFFF;
        border-bottom: 3px solid var(--uff-blue);
        margin: 0 -1rem 16px -1rem;
        padding: 12px 22px 10px 22px;
    }

    .top-title {
        color: var(--uff-blue-dark);
        font-size: 1.58rem;
        line-height: 1.15;
        font-weight: 800;
        margin: 0;
    }

    .top-subtitle {
        color: var(--uff-muted);
        font-size: .9rem;
        margin-top: 5px;
    }

    .panel {
        background: #FFFFFF;
        border: 1px solid var(--uff-border);
        border-radius: 12px;
        box-shadow: 0 4px 14px rgba(22, 82, 135, .05);
        padding: 13px 14px;
    }

    .filter-title {
        color: var(--uff-blue-dark);
        font-size: .8rem;
        font-weight: 800;
        margin-bottom: 6px;
    }

    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid var(--uff-border);
        border-radius: 12px;
        box-shadow: 0 4px 14px rgba(22, 82, 135, .06);
        padding: 14px 15px;
        min-height: 125px;
    }

    [data-testid="stMetricLabel"] {
        color: var(--uff-blue-dark);
        font-weight: 800;
    }

    [data-testid="stMetricValue"] {
        color: #193D61;
        font-weight: 800;
    }

    .summary-box {
        background: linear-gradient(100deg, #F1F8FF 0%, #FFFFFF 100%);
        border: 1px solid #BBDCF8;
        border-radius: 11px;
        padding: 13px 16px;
        color: #254A6E;
        line-height: 1.65;
        margin: 13px 0;
    }

    .summary-title {
        color: var(--uff-blue-dark);
        font-weight: 800;
        margin-bottom: 4px;
    }

    div[data-testid="stPlotlyChart"] {
        background: #FFFFFF;
        border: 1px solid var(--uff-border);
        border-radius: 12px;
        box-shadow: 0 4px 14px rgba(22, 82, 135, .05);
        padding: 5px;
    }

    .privacy {
        background: #EFF7FF;
        border: 1px solid #BBDCF8;
        border-radius: 9px;
        color: #22598B;
        padding: 9px 13px;
        font-size: .83rem;
        margin-top: 12px;
    }

    .sidebar-heading {
        color: var(--uff-blue-dark);
        font-size: .78rem;
        font-weight: 900;
        margin: 8px 0;
        text-transform: uppercase;
    }

    .sidebar-box {
        background: #F8FBFE;
        border: 1px solid #DCE8F3;
        border-radius: 10px;
        padding: 10px 12px;
        margin: 8px 0;
        color: #5A7085;
        font-size: .82rem;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 700;
    }

    h1, h2, h3 {
        color: var(--uff-blue-dark);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

LOGO = Path("assets/logo_uff_transparente.png")
PASTA_IMPORTAR = Path("data/importar")
PASTA_HISTORICO = Path("data/historico")
ARQUIVO_DEMO = Path("data/demo/wifi_demo.csv.gz")


@st.cache_data(show_spinner="Carregando o histórico...")
def carregar_dados() -> pd.DataFrame:
    dados = carregar_historico(PASTA_HISTORICO)
    modo_demo = dados.empty
    if dados.empty and ARQUIVO_DEMO.exists():
        dados = pd.read_csv(ARQUIVO_DEMO, compression="gzip")
    elif dados.empty:
        from scripts.generate_demo_data import gerar

        dados = gerar()
    if dados.empty:
        dados.attrs["modo_demo"] = modo_demo
        return dados
    dados = dados[dados["ssid"].isin(SSIDS_INSTITUCIONAIS)].copy()
    dados["data_hora"] = pd.to_datetime(dados["data_hora"], errors="coerce")
    dados = dados.dropna(subset=["data_hora"])
    dados.attrs["modo_demo"] = modo_demo
    return dados


def formatar_numero(valor: int | float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def formatar_duracao(segundos: float) -> str:
    segundos = max(0, int(segundos))
    horas, resto = divmod(segundos, 3600)
    minutos, seg = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{seg:02d}"


def calcular_tempo_observado(dados: pd.DataFrame) -> float:
    """
    Estimativa: soma intervalos consecutivos do mesmo dispositivo,
    limitando cada intervalo a 30 minutos.
    """
    base_tempo = (
        dados.dropna(subset=["dispositivo_id", "data_hora"])
        .sort_values(["dispositivo_id", "data_hora"])
        .copy()
    )
    if base_tempo.empty:
        return 0.0

    base_tempo["delta"] = (
        base_tempo.groupby("dispositivo_id")["data_hora"]
        .diff()
        .dt.total_seconds()
    )
    validos = base_tempo["delta"].where(
        (base_tempo["delta"] > 0) & (base_tempo["delta"] <= 1800)
    )

    por_dispositivo = validos.groupby(base_tempo["dispositivo_id"]).sum(min_count=1)
    if por_dispositivo.dropna().empty:
        return 0.0
    return float(por_dispositivo.mean())



def criar_grafico_temporal(serie: pd.DataFrame, granularidade: str) -> go.Figure:
    """
    Gera um gráfico temporal legível mesmo quando existe apenas um ponto
    ou quando todos os valores são iguais.
    """
    serie = serie.sort_values("intervalo").copy()

    if serie.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Sem dados para o período selecionado",
            x=.5,
            y=.5,
            showarrow=False,
            font=dict(size=16, color="#64748B"),
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig

    if len(serie) == 1:
        ponto = serie.iloc[0]
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[ponto["intervalo"]],
                y=[ponto["clientes"]],
                marker_color=AZUL,
                width=0.035,
                text=[int(ponto["clientes"])],
                textposition="outside",
                hovertemplate=(
                    "%{x|%d/%m/%Y %H:%M}<br>"
                    "<b>%{y} clientes</b><extra></extra>"
                ),
            )
        )
        ymax = max(5, int(ponto["clientes"] * 1.25))
        fig.update_yaxes(range=[0, ymax], rangemode="tozero")
    else:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=serie["intervalo"],
                y=serie["clientes"],
                mode="lines+markers",
                line=dict(width=2.7, color=AZUL),
                marker=dict(size=5, color=AZUL),
                fill="tozeroy",
                fillcolor="rgba(7,93,184,.10)",
                hovertemplate=(
                    "%{x|%d/%m/%Y %H:%M}<br>"
                    "<b>%{y} clientes</b><extra></extra>"
                ),
            )
        )

        ymin = int(serie["clientes"].min())
        ymax = int(serie["clientes"].max())

        if ymin == ymax:
            margem = max(2, int(ymax * .12))
            fig.update_yaxes(range=[max(0, ymin - margem), ymax + margem])
        else:
            fig.update_yaxes(rangemode="tozero")

    fig.update_layout(
        title=f"Clientes Observados no Tempo ({granularidade})",
        height=390,
        margin=dict(l=20, r=20, t=50, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        hovermode="x unified",
        showlegend=False,
    )
    fig.update_xaxes(
        title="",
        showgrid=False,
        tickformat="%H:%M\n%d/%m",
    )
    fig.update_yaxes(
        title=f"Clientes ({granularidade})",
        gridcolor="#E5EDF5",
        zeroline=False,
    )
    return fig


df = carregar_dados()
MODO_DEMO = bool(df.attrs.get("modo_demo", False))


# ---------------- Topo ----------------
st.markdown('<div class="top-shell">', unsafe_allow_html=True)
top_logo, top_title = st.columns([1.2, 5.8], vertical_alignment="center")

with top_logo:
    if LOGO.exists():
        st.image(str(LOGO), width="stretch")

with top_title:
    st.markdown(
        """
        <div class="top-title">Observatório Wi-Fi UFF · SBPC</div>
        <div class="top-subtitle">Inteligência operacional, capacidade e experiência de conectividade</div>
        """,
        unsafe_allow_html=True,
    )


st.markdown("</div>", unsafe_allow_html=True)


# ---------------- Sidebar ----------------
with st.sidebar:
    if MODO_DEMO:
        st.info("Modo demonstração: dados sintéticos, sem informações do ambiente real.")

    st.markdown('<div class="sidebar-heading">Atualização dos dados</div>', unsafe_allow_html=True)

    pendentes = sorted(
        list(PASTA_IMPORTAR.glob("*.csv"))
        + list(PASTA_IMPORTAR.glob("*.csv.gz"))
    )
    st.caption(f"Arquivos novos aguardando processamento: {len(pendentes)}")

    if st.button("☁  Processar arquivos novos", width="stretch", type="primary"):
        try:
            with st.spinner("Processando arquivos novos e atualizando o histórico..."):
                resumo_importacao = importar_novos_arquivos()
            st.success(
                f"{resumo_importacao['registros_novos']} novos registros; "
                f"{resumo_importacao['duplicados_descartados']} duplicados descartados."
            )
            st.cache_data.clear()
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))

    st.divider()

    menu = st.radio(
        "Navegação",
        [
            "⌂  Visão Geral",
            "◉  Por SSID",
            "♜  Por Pontos de Acesso",
            "◷  Por Horários",
            "▥  Qualidade de Rádio",
            "▣  Resumo & Insights",
            "⇩  Exportar Relatórios",
            "ⓘ  Sobre o Sistema",
        ],
        label_visibility="collapsed",
    )

    st.markdown('<div class="sidebar-heading">Filtros ativos</div>', unsafe_allow_html=True)
    filtro_status = st.empty()

    st.markdown(
        '<div class="sidebar-box"><b>Histórico:</b> os arquivos importados são '
        "acumulados e preservados para consultas futuras.</div>",
        unsafe_allow_html=True,
    )


if df.empty:
    st.warning(
        "Nenhum registro institucional disponível. Copie um CSV ou CSV.GZ "
        "para data/importar e clique em Importar novos arquivos."
    )
    st.stop()

if MODO_DEMO:
    st.caption("Demonstração pública com dados 100% sintéticos. Métricas não representam resultados oficiais da UFF ou da SBPC.")


# ---------------- Filtros superiores ----------------
data_min = df["data_hora"].min()
data_max = df["data_hora"].max()

st.info(
    f"Base carregada disponível de {data_min.strftime('%d/%m/%Y %H:%M:%S')} "
    f"até {data_max.strftime('%d/%m/%Y %H:%M:%S')}. "
    "Os indicadores só podem somar registros existentes nesse intervalo."
)


f1, f2, f3, f4, f5 = st.columns([1.25, 1.35, 1.35, .8, .95], gap="small")

with f1:
    st.markdown('<div class="filter-title">▣ Período</div>', unsafe_allow_html=True)
    modo_periodo = st.selectbox(
        "Período",
        [
            "Personalizado",
            "Última 1 hora",
            "Últimas 12 horas",
            "Últimas 24 horas",
            "Hoje",
            "Ontem",
            "Dia completo",
            "Todo o histórico",
        ],
        label_visibility="collapsed",
    )

    inicio_custom = data_min
    fim_custom = data_max + pd.Timedelta(seconds=1)

    if modo_periodo == "Personalizado":
        cini, cfim = st.columns(2)
        with cini:
            data_inicio = st.date_input(
                "De",
                value=data_min.date(),
                min_value=data_min.date(),
                max_value=data_max.date(),
            )
            hora_inicio = st.time_input("Hora inicial", value=time(8, 0))
        with cfim:
            data_fim = st.date_input(
                "Até",
                value=data_max.date(),
                min_value=data_min.date(),
                max_value=data_max.date(),
            )
            hora_fim = st.time_input("Hora final", value=time(20, 0))

        inicio_custom = pd.Timestamp.combine(data_inicio, hora_inicio)
        fim_custom = pd.Timestamp.combine(data_fim, hora_fim)
        if fim_custom <= inicio_custom:
            fim_custom += pd.Timedelta(days=1)

with f2:
    st.markdown('<div class="filter-title">◉ SSID Institucional</div>', unsafe_allow_html=True)
    ssids_presentes = [
        ssid for ssid in SSIDS_INSTITUCIONAIS
        if ssid in set(df["ssid"].dropna().unique())
    ]
    selecionar_todos_ssids = st.checkbox(
        "Selecionar todos os SSIDs",
        value=True,
        key="selecionar_todos_ssids",
    )

    if selecionar_todos_ssids:
        ssids = list(ssids_presentes)
        st.multiselect(
            "SSID Institucional",
            ssids_presentes,
            default=ssids_presentes,
            disabled=True,
            key="ssids_todos_visual",
            label_visibility="collapsed",
        )
    else:
        ssids = st.multiselect(
            "SSID Institucional",
            ssids_presentes,
            default=ssids_presentes,
            key="ssids_selecionados",
            label_visibility="collapsed",
        )

    st.caption(f"{len(ssids)} de {len(ssids_presentes)} SSIDs selecionados")

with f3:
    st.markdown('<div class="filter-title">♜ Pontos de Acesso</div>', unsafe_allow_html=True)
    aps_disponiveis = sorted(
        str(ap) for ap in df["ap"].dropna().unique() if str(ap).strip()
    )
    aps = st.multiselect(
        "Pontos de Acesso",
        aps_disponiveis,
        placeholder="Todos selecionados",
        label_visibility="collapsed",
    )

with f4:
    st.markdown('<div class="filter-title">◷ Granularidade</div>', unsafe_allow_html=True)
    granularidade = st.selectbox(
        "Granularidade",
        ["1 minuto", "5 minutos", "15 minutos", "30 minutos", "1 hora"],
        index=1,
        label_visibility="collapsed",
    )

with f5:
    st.markdown('<div class="filter-title">↻ Atualização</div>', unsafe_allow_html=True)
    atualizar = st.button("↻  Atualizar", width="stretch", type="primary")
    auto_atualizar = st.toggle("Auto atualizar", value=False)
    st.caption("A cada 5 minutos")

if atualizar:
    st.cache_data.clear()
    st.rerun()


# ---------------- Aplicação dos filtros ----------------
referencia = data_max

if modo_periodo == "Última 1 hora":
    inicio, fim = referencia - pd.Timedelta(hours=1), referencia + pd.Timedelta(seconds=1)
elif modo_periodo == "Últimas 12 horas":
    inicio, fim = referencia - pd.Timedelta(hours=12), referencia + pd.Timedelta(seconds=1)
elif modo_periodo == "Últimas 24 horas":
    inicio, fim = referencia - pd.Timedelta(hours=24), referencia + pd.Timedelta(seconds=1)
elif modo_periodo == "Hoje":
    inicio = referencia.normalize()
    fim = inicio + pd.Timedelta(days=1)
elif modo_periodo == "Ontem":
    fim = referencia.normalize()
    inicio = fim - pd.Timedelta(days=1)
elif modo_periodo == "Dia completo":
    dia = st.date_input(
        "Selecione o dia do relatório",
        value=referencia.date(),
        min_value=data_min.date(),
        max_value=data_max.date(),
    )
    inicio = pd.Timestamp(dia)
    fim = inicio + pd.Timedelta(days=1)
elif modo_periodo == "Todo o histórico":
    inicio, fim = data_min, data_max + pd.Timedelta(seconds=1)
else:
    inicio, fim = inicio_custom, fim_custom

filtrado = df[
    (df["data_hora"] >= inicio)
    & (df["data_hora"] < fim)
].copy()

if ssids:
    filtrado = filtrado[filtrado["ssid"].isin(ssids)]
else:
    filtrado = filtrado.iloc[0:0]

if aps:
    filtrado = filtrado[filtrado["ap"].isin(aps)]

filtros_ativos = [
    f"SSIDs: {len(ssids)}/{len(ssids_presentes)}",
    f"{len(aps) if aps else 'Todos'} AP(s)",
    modo_periodo,
]
filtro_status.markdown(
    '<div class="sidebar-box">' + "<br>".join(map(str, filtros_ativos)) + "</div>",
    unsafe_allow_html=True,
)

if filtrado.empty:
    st.info("Não existem registros para a combinação de filtros selecionada.")
    st.stop()


# ---------------- Cálculos ----------------
freq_map = {
    "1 minuto": "1min",
    "5 minutos": "5min",
    "15 minutos": "15min",
    "30 minutos": "30min",
    "1 hora": "1h",
}
freq = freq_map[granularidade]

# Duas leituras complementares:
# 1) dispositivos únicos gerais: elimina repetição do mesmo aparelho entre SSIDs;
# 2) clientes somados por SSID: soma a quantidade distinta dentro de cada SSID.
dispositivos_unicos_gerais = (
    filtrado["dispositivo_id"].replace("", pd.NA).nunique()
)

clientes_por_ssid_base = (
    filtrado.groupby("ssid")["dispositivo_id"]
    .nunique()
)

clientes_unicos = int(clientes_por_ssid_base.sum())
eventos = len(filtrado)

linha_tempo = filtrado.copy()
linha_tempo["intervalo"] = linha_tempo["data_hora"].dt.floor(freq)

# Calcula distintos por SSID dentro de cada intervalo e depois soma os SSIDs.
# Assim, todos os SSIDs selecionados participam do pico e do gráfico temporal.
serie_por_ssid = (
    linha_tempo.groupby(["intervalo", "ssid"])
    .agg(
        clientes=("dispositivo_id", "nunique"),
        eventos=("action", "size"),
    )
    .reset_index()
)

serie = (
    serie_por_ssid.groupby("intervalo")
    .agg(
        clientes=("clientes", "sum"),
        eventos=("eventos", "sum"),
    )
    .reset_index()
)

pico_linha = serie.loc[serie["clientes"].idxmax()]
pico = int(pico_linha["clientes"])
horario_pico = pico_linha["intervalo"]

ssid_rank = (
    filtrado.groupby("ssid")["dispositivo_id"]
    .nunique()
    .sort_values(ascending=False)
)

ssids_sem_dados = [
    ssid for ssid in SSIDS_INSTITUCIONAIS
    if ssid not in set(filtrado["ssid"].dropna().unique())
]

detalhamento_ssid = (
    filtrado.groupby("ssid")
    .agg(
        clientes_distintos=("dispositivo_id", "nunique"),
        eventos=("action", "size"),
    )
    .reindex(SSIDS_INSTITUCIONAIS, fill_value=0)
    .reset_index()
)

detalhamento_ssid["participacao_pct"] = (
    detalhamento_ssid["clientes_distintos"]
    / max(clientes_unicos, 1)
    * 100
).round(1)
ssid_lider = ssid_rank.index[0]
ssid_lider_n = int(ssid_rank.iloc[0])
ssid_lider_pct = (ssid_lider_n / clientes_unicos * 100) if clientes_unicos else 0

ap_rank = (
    filtrado.groupby("ap")["dispositivo_id"]
    .nunique()
    .sort_values(ascending=False)
)
ap_lider = ap_rank.index[0] if not ap_rank.empty else "—"
ap_lider_n = int(ap_rank.iloc[0]) if not ap_rank.empty else 0

tempo_medio = calcular_tempo_observado(filtrado)

eventos_por_ssid = (
    filtrado.groupby("ssid")
    .agg(
        clientes=("dispositivo_id", "nunique"),
        eventos=("action", "size"),
    )
)
eventos_por_ssid["eventos_por_cliente"] = (
    eventos_por_ssid["eventos"]
    / eventos_por_ssid["clientes"].replace(0, pd.NA)
)
ssid_eventos_lider = (
    eventos_por_ssid["eventos_por_cliente"].idxmax()
    if not eventos_por_ssid.empty
    else "—"
)


st.caption(
    "SSIDs selecionados: "
    + ", ".join(ssids)
    + f" | Soma dos clientes distintos por SSID: {formatar_numero(clientes_unicos)}"
    + f" | Dispositivos únicos gerais: {formatar_numero(dispositivos_unicos_gerais)}"
)

if ssids_sem_dados:
    st.warning(
        "SSID(s) selecionado(s) sem registros no período/importação atual: "
        + ", ".join(ssids_sem_dados)
    )

# ---------------- Cards ----------------
m1, m2, m3, m4, m5, m6 = st.columns(6, gap="small")
m1.metric(
    "Clientes nos SSIDs",
    formatar_numero(clientes_unicos),
    help=(
        "Soma dos clientes distintos dentro de cada SSID selecionado. "
        f"Dispositivos únicos gerais, sem repetir entre SSIDs: "
        f"{formatar_numero(dispositivos_unicos_gerais)}."
    ),
)
m2.metric("Pico Observado", formatar_numero(pico), help=f"Clientes distintos em {granularidade}.")
m3.metric("Horário do Pico", horario_pico.strftime("%H:%M"), help=horario_pico.strftime("%d/%m/%Y"))
m4.metric("SSID Líder", ssid_lider, help=f"{ssid_lider_pct:.1f}% dos clientes observados.")
m5.metric("AP Líder", ap_lider, help=f"{ap_lider_n} clientes únicos.")
m6.metric("Tempo Médio Observado", formatar_duracao(tempo_medio), help="Estimativa com limite de 30 minutos por intervalo.")


if len(serie) == 1:
    st.info(
        "O período selecionado gerou apenas um intervalo temporal. "
        "O gráfico será exibido como uma barra para manter a leitura correta."
    )

# ---------------- Resumo automático ----------------
st.markdown(
    f"""
    <div class="summary-box">
        <div class="summary-title">Resumo do Período Selecionado</div>
        Entre <b>{inicio.strftime('%d/%m/%Y %H:%M')}</b> e
        <b>{(fim - pd.Timedelta(seconds=1)).strftime('%d/%m/%Y %H:%M')}</b>,
        foram contabilizados, na base carregada, <b>{formatar_numero(clientes_unicos)}</b> clientes
        somados entre os SSIDs selecionados. Sem repetir um mesmo dispositivo
        entre SSIDs, o total geral foi de
        <b>{formatar_numero(dispositivos_unicos_gerais)}</b> dispositivos. O maior volume ocorreu às
        <b>{horario_pico.strftime('%H:%M')}</b>, com
        <b>{formatar_numero(pico)}</b> clientes em um intervalo de
        <b>{granularidade}</b>.<br>
        O SSID com maior utilização foi <b>{ssid_lider}</b>, representando
        <b>{ssid_lider_pct:.1f}%</b> dos clientes. O ponto de acesso com maior
        concentração foi <b>{ap_lider}</b>, com
        <b>{formatar_numero(ap_lider_n)}</b> clientes distintos.<br>
        O tempo médio de permanência observado foi de
        <b>{formatar_duracao(tempo_medio)}</b> (estimativa).
        O SSID <b>{ssid_eventos_lider}</b> apresentou a maior relação de eventos
        por cliente, o que pode indicar reconexões ou roaming mais intenso.
    </div>
    """,
    unsafe_allow_html=True,
)



with st.expander("Ver detalhamento do cálculo por SSID", expanded=True):
    tabela_detalhe = detalhamento_ssid.rename(
        columns={
            "ssid": "SSID",
            "clientes_distintos": "Clientes distintos",
            "eventos": "Eventos",
            "participacao_pct": "Participação (%)",
        }
    )
    st.dataframe(
        tabela_detalhe,
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "O total 'Clientes nos SSIDs' é a soma da coluna 'Clientes distintos'. "
        "SSID com zero não possui registros no arquivo/período atualmente carregado."
    )

# ---------------- Conteúdo conforme menu ----------------
ssid_df = (
    filtrado.groupby("ssid")
    .agg(
        clientes=("dispositivo_id", "nunique"),
        eventos=("action", "size"),
    )
    .reset_index()
    .sort_values("clientes", ascending=False)
)

ap_df = (
    filtrado.groupby("ap")
    .agg(
        clientes=("dispositivo_id", "nunique"),
        eventos=("action", "size"),
    )
    .reset_index()
    .sort_values(["clientes", "eventos"], ascending=False)
)

if "Visão Geral" in menu:
    g1, g2, g3 = st.columns([1.05, 1.35, 1.25], gap="small")

    with g1:
        fig = go.Figure()
        fig.add_trace(
            go.Pie(
                labels=ssid_df["ssid"],
                values=ssid_df["clientes"],
                hole=.58,
                marker=dict(
                    colors=[
                        CORES_SSID.get(ssid, "#7CAED6")
                        for ssid in ssid_df["ssid"]
                    ]
                ),
                textinfo="none",
                hovertemplate="<b>%{label}</b><br>Clientes: %{value}<br>%{percent}<extra></extra>",
            )
        )
        fig.add_annotation(
            text=f"<b>{formatar_numero(clientes_unicos)}</b><br>Total",
            x=.5, y=.5, showarrow=False, font=dict(size=20, color="#173B5E"),
        )
        fig.update_layout(
            title="Clientes distintos somados por SSID",
            legend=dict(orientation="v"),
            margin=dict(l=15, r=15, t=50, b=15),
            height=390,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(
            fig,
            width="stretch",
            config={"displaylogo": False},
        )

    with g2:
        fig = criar_grafico_temporal(serie, granularidade)
        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displaylogo": False,
                "modeBarButtonsToRemove": [
                    "lasso2d",
                    "select2d",
                    "autoScale2d",
                ],
            },
        )

    with g3:
        top_ap = ap_df.head(10).sort_values("clientes")
        fig = px.bar(
            top_ap,
            x="clientes",
            y="ap",
            orientation="h",
            text="clientes",
            labels={"clientes": "Clientes Únicos", "ap": ""},
            title="Top 10 Pontos de Acesso por Clientes Únicos",
        )
        fig.update_traces(marker_color=AZUL, textposition="outside", cliponaxis=False)
        fig.update_layout(
            height=390,
            margin=dict(l=15, r=35, t=50, b=35),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#FFFFFF",
            xaxis=dict(rangemode="tozero", gridcolor="#E5EDF5"),
        )
        st.plotly_chart(fig, width="stretch")

elif "Por SSID" in menu:
    st.subheader("Análise por SSID")
    tabela = ssid_df.copy()
    tabela["participacao"] = (
        tabela["clientes"] / clientes_unicos * 100
    ).round(1)
    tabela["eventos_por_cliente"] = (
        tabela["eventos"] / tabela["clientes"].replace(0, pd.NA)
    ).round(2)

    st.dataframe(
        tabela.rename(
            columns={
                "ssid": "SSID",
                "clientes": "Clientes únicos",
                "eventos": "Eventos",
                "participacao": "Participação (%)",
                "eventos_por_cliente": "Eventos por cliente",
            }
        ),
        width="stretch",
        hide_index=True,
    )

elif "Pontos de Acesso" in menu:
    st.subheader("Análise por Pontos de Acesso")
    limite = st.slider("Quantidade de APs exibidos", 5, 50, 20, 5)
    top_ap = ap_df.head(limite).sort_values("clientes")
    fig = px.bar(
        top_ap,
        x="clientes",
        y="ap",
        orientation="h",
        hover_data=["eventos"],
        labels={"clientes": "Clientes únicos", "ap": ""},
    )
    fig.update_traces(marker_color=AZUL)
    st.plotly_chart(fig, width="stretch")

elif "Por Horários" in menu:
    st.subheader("Análise por Horários")
    fig = px.area(
        serie,
        x="intervalo",
        y="clientes",
        hover_data=["eventos"],
        labels={"intervalo": "Data e hora", "clientes": "Clientes observados"},
    )
    fig.update_traces(line_color=AZUL, fillcolor="rgba(7,93,184,.16)")
    st.plotly_chart(fig, width="stretch")

elif "Qualidade de Rádio" in menu:
    st.subheader("Qualidade de Rádio")
    q1, q2 = st.columns(2)

    with q1:
        if "signal" in filtrado and filtrado["signal"].notna().any():
            fig = px.histogram(
                filtrado.dropna(subset=["signal"]),
                x="signal",
                nbins=25,
                title="Distribuição de sinal",
            )
            fig.update_traces(marker_color=AZUL)
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("A exportação atual não possui sinal suficiente.")

    with q2:
        if "channel" in filtrado and filtrado["channel"].notna().any():
            canais = (
                filtrado.dropna(subset=["channel"])
                .groupby("channel")
                .size()
                .reset_index(name="eventos")
            )
            fig = px.bar(
                canais,
                x="channel",
                y="eventos",
                title="Eventos por canal",
            )
            fig.update_traces(marker_color=AZUL)
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("A exportação atual não possui canal suficiente.")

elif "Resumo & Insights" in menu:
    st.subheader("Resumo e Insights")
    st.write(
        f"O período apresentou {formatar_numero(clientes_unicos)} clientes únicos, "
        f"com pico de {formatar_numero(pico)} às {horario_pico.strftime('%H:%M')}."
    )
    st.write(
        f"O SSID líder foi {ssid_lider}, enquanto o AP de maior concentração "
        f"foi {ap_lider}."
    )
    st.warning(
        f"{ssid_eventos_lider} apresentou a maior relação de eventos por cliente. "
        "Esse resultado não confirma falha, mas indica prioridade de investigação."
    )

elif "Exportar Relatórios" in menu:
    st.subheader("Exportar Relatórios")
    st.write(
        "Gere um relatório institucional da Universidade Federal Fluminense "
        "com os filtros aplicados na dashboard."
    )

    pdf_bytes = gerar_relatorio_pdf(
        filtrado=filtrado,
        inicio=inicio,
        fim=fim,
        granularidade=granularidade,
        clientes_nos_ssids=clientes_unicos,
        dispositivos_unicos_gerais=dispositivos_unicos_gerais,
        pico=pico,
        horario_pico=horario_pico,
        ssid_lider=ssid_lider,
        ssid_lider_pct=ssid_lider_pct,
        ap_lider=ap_lider,
        ap_lider_n=ap_lider_n,
        tempo_medio=tempo_medio,
        ssid_eventos_lider=ssid_eventos_lider,
        ssids_selecionados=ssids,
        logo_path=LOGO,
    )

    col_pdf, col_csv = st.columns(2)
    with col_pdf:
        st.download_button(
            "Baixar relatório institucional em PDF",
            data=pdf_bytes,
            file_name=f"relatorio_wifi_uff_{inicio:%Y%m%d_%H%M}_{fim:%Y%m%d_%H%M}.pdf",
            mime="application/pdf",
            width="stretch",
            type="primary",
        )

    with col_csv:
        exportar = filtrado[
            ["data_hora", "ssid", "ap", "action", "banda", "channel", "signal", "snr"]
        ].copy()
        csv_bytes = exportar.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Baixar dados agregados filtrados em CSV",
            data=csv_bytes,
            file_name=f"wifi_uff_{inicio:%Y%m%d_%H%M}_{fim:%Y%m%d_%H%M}.csv",
            mime="text/csv",
            width="stretch",
        )

    st.info(
        "O PDF contém identidade visual da UFF, indicadores, resumo executivo, "
        "tabelas, gráficos, metodologia e observações de LGPD."
    )

else:
    st.subheader("Sobre o Sistema")
    st.markdown(
        """
        Esta dashboard consolida exportações manuais do FortiAnalyzer e mantém
        um histórico acumulativo. Os seis SSIDs monitorados são:

        - eduroam
        - VISITANTE-UFF
        - SBPC2026
        - SBPC
        - PREFEITO
        - PR_Niteroi

        A contagem utiliza identificadores anônimos. O pico representa clientes observados no intervalo selecionado. Quando há apenas um intervalo, o gráfico temporal exibe uma barra em vez de uma linha.
        """
    )


ultima_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
rodape, atualizado = st.columns([4.5, 1])
with rodape:
    st.markdown(
        """
        <div class="privacy">
        🛡 <b>Proteção de Dados (LGPD):</b> nenhuma informação pessoal é exibida.
        MACs são anonimizados, IPs completos não são armazenados e todos os
        indicadores apresentados são agregados.
        </div>
        """,
        unsafe_allow_html=True,
    )
with atualizado:
    st.caption(f"Última atualização: {ultima_atualizacao}")

