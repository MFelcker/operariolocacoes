"""
Modulo Agenda — Calendario de ocupacao e disponibilidade das maquinas.
"""
import calendar
from datetime import date, datetime, timedelta
from typing import Optional

import streamlit as st

from database import listar_equipamentos, listar_locacoes, taxa_ocupacao_mes

# Paleta de cores para maquinas
CORES_MAQUINAS = [
    "#1B3A8C",
    "#2B8BE8",
    "#4CAF50",
    "#FF9800",
    "#E91E63",
    "#9C27B0",
    "#00BCD4",
    "#795548",
    "#607D8B",
    "#F44336",
    "#3F51B5",
    "#8BC34A",
]


def _cor_maquina(idx: int) -> str:
    """Retorna a cor associada ao indice da maquina."""
    return CORES_MAQUINAS[idx % len(CORES_MAQUINAS)]


def _parse_data(valor) -> Optional[date]:
    """Converte string ou date para date."""
    if valor is None:
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if isinstance(valor, datetime):
        return valor.date()
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _locacoes_do_mes(ano: int, mes: int):
    """Retorna todas as locacoes que interceptam o mes/ano indicado."""
    inicio = date(ano, mes, 1)
    dias_no_mes = calendar.monthrange(ano, mes)[1]
    fim = date(ano, mes, dias_no_mes)

    todas = listar_locacoes()
    resultado = []
    for loc in todas:
        d_saida = _parse_data(loc["data_saida"])
        d_fim = _parse_data(loc["data_retorno_efetiva"]) or _parse_data(
            loc["data_retorno_prevista"]
        )
        if d_saida is None or d_fim is None:
            continue
        # Verifica se o intervalo da locacao intercepta o mes
        if d_saida <= fim and d_fim >= inicio:
            resultado.append(loc)
    return resultado


def _montar_ocupacao(ano: int, mes: int, locacoes):
    """Retorna dict {dia: [(equip_nome, cor), ...]} para o mes."""
    dias_no_mes = calendar.monthrange(ano, mes)[1]
    inicio_mes = date(ano, mes, 1)
    fim_mes = date(ano, mes, dias_no_mes)

    # Mapear equipamentos a cores
    equipamentos = listar_equipamentos()
    equip_cor = {}
    for idx, eq in enumerate(equipamentos):
        equip_cor[eq["id"]] = (eq["nome"], _cor_maquina(idx))

    ocupacao = {d: [] for d in range(1, dias_no_mes + 1)}

    for loc in locacoes:
        d_saida = _parse_data(loc["data_saida"])
        d_fim = _parse_data(loc["data_retorno_efetiva"]) or _parse_data(
            loc["data_retorno_prevista"]
        )
        if d_saida is None or d_fim is None:
            continue

        # Limitar ao mes corrente
        d_ini = max(d_saida, inicio_mes)
        d_end = min(d_fim, fim_mes)

        equip_id = loc["equipamento_id"]
        nome, cor = equip_cor.get(equip_id, (loc["equipamento_nome"], "#888888"))

        dia_atual = d_ini
        while dia_atual <= d_end:
            ocupacao[dia_atual.day].append((nome, cor))
            dia_atual += timedelta(days=1)

    return ocupacao, equip_cor


def _gerar_html_calendario(ano: int, mes: int, ocupacao: dict) -> str:
    """Gera tabela HTML estilizada do calendario mensal."""
    cal = calendar.Calendar(firstweekday=6)  # Domingo primeiro
    semanas = cal.monthdayscalendar(ano, mes)

    dias_semana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"]

    html = """
    <style>
        .cal-table {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
            font-size: 14px;
        }
        .cal-table th {
            background-color: #1B3A8C;
            color: white;
            padding: 8px 4px;
            text-align: center;
            font-weight: 600;
        }
        .cal-table td {
            border: 1px solid #e0e0e0;
            vertical-align: top;
            padding: 4px;
            min-height: 60px;
            height: 70px;
            width: 14.28%;
        }
        .cal-table td.vazio {
            background-color: #f5f5f5;
        }
        .cal-dia-num {
            font-weight: bold;
            font-size: 13px;
            color: #333;
            margin-bottom: 3px;
        }
        .cal-tag {
            display: inline-block;
            padding: 1px 5px;
            margin: 1px 0;
            border-radius: 3px;
            color: white;
            font-size: 11px;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
        }
        .cal-hoje {
            background-color: #fffde7;
            border: 2px solid #FF9800 !important;
        }
    </style>
    <table class="cal-table">
    <thead><tr>
    """
    for d in dias_semana:
        html += f"<th>{d}</th>"
    html += "</tr></thead><tbody>"

    hoje = date.today()

    for semana in semanas:
        html += "<tr>"
        for dia in semana:
            if dia == 0:
                html += '<td class="vazio"></td>'
            else:
                classes = ""
                if date(ano, mes, dia) == hoje:
                    classes = ' class="cal-hoje"'

                tags_html = ""
                maquinas_dia = ocupacao.get(dia, [])
                for nome, cor in maquinas_dia:
                    tags_html += (
                        f'<div class="cal-tag" style="background-color:{cor};" '
                        f'title="{nome}">{nome}</div>'
                    )

                html += (
                    f"<td{classes}>"
                    f'<div class="cal-dia-num">{dia}</div>'
                    f"{tags_html}</td>"
                )
        html += "</tr>"

    html += "</tbody></table>"
    return html


def _dias_ociosos_por_maquina(ano: int, mes: int, ocupacao: dict, equip_cor: dict):
    """Calcula dias ociosos de cada maquina no mes."""
    dias_no_mes = calendar.monthrange(ano, mes)[1]

    # Contar dias ocupados por maquina
    dias_ocupados = {}
    for dia in range(1, dias_no_mes + 1):
        for nome, cor in ocupacao.get(dia, []):
            if nome not in dias_ocupados:
                dias_ocupados[nome] = set()
            dias_ocupados[nome].add(dia)

    resultado = []
    for equip_id, (nome, cor) in equip_cor.items():
        qtd_ocupado = len(dias_ocupados.get(nome, set()))
        qtd_ocioso = dias_no_mes - qtd_ocupado
        resultado.append(
            {
                "maquina": nome,
                "cor": cor,
                "dias_ocupados": qtd_ocupado,
                "dias_ociosos": qtd_ocioso,
                "total_dias": dias_no_mes,
            }
        )

    return resultado


def render():
    """Renderiza a pagina de Agenda e Disponibilidade."""
    st.markdown("# 📅 Agenda e Disponibilidade")
    st.markdown("### Calendário de ocupação das máquinas")
    st.divider()

    # ── Seletor de mes/ano ──
    col_mes, col_ano = st.columns(2)

    meses_nomes = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ]

    hoje = date.today()
    with col_mes:
        mes_sel = st.selectbox(
            "Mês",
            options=list(range(1, 13)),
            format_func=lambda m: meses_nomes[m - 1],
            index=hoje.month - 1,
        )
    with col_ano:
        ano_sel = st.selectbox(
            "Ano",
            options=list(range(hoje.year - 2, hoje.year + 3)),
            index=2,
        )

    # ── Buscar locacoes e montar ocupacao ──
    locacoes = _locacoes_do_mes(ano_sel, mes_sel)
    ocupacao, equip_cor = _montar_ocupacao(ano_sel, mes_sel, locacoes)

    # ── Legenda de cores ──
    if equip_cor:
        st.markdown("#### Legenda de máquinas")
        cols_legenda = st.columns(min(len(equip_cor), 6))
        for idx, (equip_id, (nome, cor)) in enumerate(equip_cor.items()):
            with cols_legenda[idx % len(cols_legenda)]:
                st.markdown(
                    f'<span style="display:inline-block;width:14px;height:14px;'
                    f"background-color:{cor};border-radius:3px;margin-right:6px;"
                    f'vertical-align:middle;"></span>'
                    f'<span style="vertical-align:middle;font-size:14px;">'
                    f"{nome}</span>",
                    unsafe_allow_html=True,
                )

    st.markdown("")

    # ── Calendario visual ──
    nome_mes = meses_nomes[mes_sel - 1]
    st.markdown(
        f'<h4 style="text-align:center;color:#1B3A8C;">'
        f"{nome_mes} de {ano_sel}</h4>",
        unsafe_allow_html=True,
    )

    html_cal = _gerar_html_calendario(ano_sel, mes_sel, ocupacao)
    st.markdown(html_cal, unsafe_allow_html=True)

    st.markdown("")
    st.divider()

    # ── Indicador de dias ociosos ──
    st.markdown("#### ⏳ Dias ociosos por máquina no mês")

    dados_ociosos = _dias_ociosos_por_maquina(ano_sel, mes_sel, ocupacao, equip_cor)
    dias_no_mes = calendar.monthrange(ano_sel, mes_sel)[1]

    if dados_ociosos:
        cols_ociosos = st.columns(min(len(dados_ociosos), 4))
        for idx, item in enumerate(dados_ociosos):
            with cols_ociosos[idx % len(cols_ociosos)]:
                pct_ocioso = (
                    (item["dias_ociosos"] / item["total_dias"]) * 100
                    if item["total_dias"] > 0
                    else 0
                )
                st.markdown(
                    f'<div style="border-left:4px solid {item["cor"]};'
                    f'padding:8px 12px;margin-bottom:8px;background:#f8f9fa;'
                    f'border-radius:0 6px 6px 0;">'
                    f'<strong>{item["maquina"]}</strong><br>'
                    f'<span style="font-size:22px;color:#1B3A8C;">'
                    f'{item["dias_ociosos"]}</span>'
                    f' <span style="font-size:13px;color:#666;">dias ociosos</span>'
                    f'<br><span style="font-size:12px;color:#999;">'
                    f'{item["dias_ocupados"]} dias ocupados '
                    f"({100 - pct_ocioso:.0f}% ocupação)</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("Nenhuma máquina cadastrada.")

    st.divider()

    # ── Detalhe por dia ──
    st.markdown("#### 🔍 Detalhes de um dia específico")

    dia_selecionado = st.date_input(
        "Selecione uma data para ver as locações ativas",
        value=date(ano_sel, mes_sel, 1),
        min_value=date(ano_sel, mes_sel, 1),
        max_value=date(
            ano_sel, mes_sel, calendar.monthrange(ano_sel, mes_sel)[1]
        ),
    )

    if dia_selecionado:
        locacoes_dia = []
        for loc in locacoes:
            d_saida = _parse_data(loc["data_saida"])
            d_fim = _parse_data(loc["data_retorno_efetiva"]) or _parse_data(
                loc["data_retorno_prevista"]
            )
            if d_saida is None or d_fim is None:
                continue
            if d_saida <= dia_selecionado <= d_fim:
                locacoes_dia.append(loc)

        if locacoes_dia:
            st.markdown(
                f"**{len(locacoes_dia)} locação(ões) ativa(s) em "
                f"{dia_selecionado.strftime('%d/%m/%Y')}:**"
            )
            for loc in locacoes_dia:
                d_saida = _parse_data(loc["data_saida"])
                d_retorno = _parse_data(
                    loc["data_retorno_efetiva"]
                ) or _parse_data(loc["data_retorno_prevista"])

                equip_id = loc["equipamento_id"]
                _, cor = equip_cor.get(
                    equip_id, (loc["equipamento_nome"], "#888888")
                )

                st.markdown(
                    f'<div style="border-left:4px solid {cor};'
                    f"padding:10px 14px;margin:6px 0;background:#fff;"
                    f'border-radius:0 8px 8px 0;box-shadow:0 1px 3px rgba(0,0,0,0.1);">'
                    f'<strong style="color:#1B3A8C;">🔧 {loc["equipamento_nome"]}</strong>'
                    f"<br>"
                    f'👤 Cliente: <strong>{loc["cliente_nome"]}</strong><br>'
                    f"📆 Saída: {d_saida.strftime('%d/%m/%Y') if d_saida else '-'} &nbsp;|&nbsp; "
                    f"Retorno: {d_retorno.strftime('%d/%m/%Y') if d_retorno else '-'}<br>"
                    f'<span style="font-size:12px;color:#666;">'
                    f'Status: {loc["status"]}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info(
                f"Nenhuma locação ativa em "
                f"{dia_selecionado.strftime('%d/%m/%Y')}."
            )
