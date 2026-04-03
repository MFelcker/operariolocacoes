"""
Módulo Relatórios — geração de relatórios mensais com exportação Excel e PDF.
"""
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date

from database import (
    faturamento_mes,
    despesas_mes,
    despesas_por_categoria_mes,
    num_locacoes_mes,
    taxa_ocupacao_mes,
    listar_equipamentos,
    get_config,
)


def _formatar_brl(valor):
    """Formata valor como R$ X.XXX,XX."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


CATEGORIAS_LABELS = {
    "parcelas": "Parcelas",
    "sabao": "Sabão",
    "gasolina": "Gasolina",
    "manutencao": "Manutenção",
    "outros": "Outros",
}


def _dados_relatorio(mes):
    """Coleta todos os dados do relatório mensal."""
    fat_bruto = faturamento_mes(mes)
    desp_total = despesas_mes(mes)
    lucro_real = fat_bruto - desp_total
    n_locacoes = num_locacoes_mes(mes)
    desp_cat = despesas_por_categoria_mes(mes)
    ocupacao = taxa_ocupacao_mes(mes)
    equipamentos = listar_equipamentos()

    ocupacao_detalhada = []
    for e in equipamentos:
        taxa = ocupacao.get(e["id"], 0.0)
        ocupacao_detalhada.append({
            "Equipamento": e["nome"],
            "Taxa de Ocupação (%)": taxa,
        })

    return {
        "mes": mes,
        "faturamento_bruto": fat_bruto,
        "despesas_total": desp_total,
        "lucro_real": lucro_real,
        "num_locacoes": n_locacoes,
        "despesas_por_categoria": desp_cat,
        "ocupacao_detalhada": ocupacao_detalhada,
    }


def _gerar_excel(dados):
    """Gera arquivo Excel (.xlsx) com os dados do relatório."""
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Aba: Resumo
        resumo = pd.DataFrame([{
            "Mês": dados["mes"],
            "Faturamento Bruto (R$)": round(dados["faturamento_bruto"], 2),
            "Despesas Totais (R$)": round(dados["despesas_total"], 2),
            "Lucro Real (R$)": round(dados["lucro_real"], 2),
            "Nº de Locações": dados["num_locacoes"],
        }])
        resumo.to_excel(writer, sheet_name="Resumo", index=False)

        # Aba: Despesas por Categoria
        if dados["despesas_por_categoria"]:
            desp_rows = []
            for cat, val in dados["despesas_por_categoria"].items():
                desp_rows.append({
                    "Categoria": CATEGORIAS_LABELS.get(cat, cat),
                    "Valor (R$)": round(val, 2),
                })
            df_desp = pd.DataFrame(desp_rows)
            df_desp.to_excel(writer, sheet_name="Despesas por Categoria", index=False)

        # Aba: Ocupação por Equipamento
        if dados["ocupacao_detalhada"]:
            df_ocup = pd.DataFrame(dados["ocupacao_detalhada"])
            df_ocup.to_excel(writer, sheet_name="Ocupação por Equipamento", index=False)

    output.seek(0)
    return output


def _safe_text(text):
    """Remove/substitui caracteres fora do latin-1 para compatibilidade com fontes PDF padrão."""
    replacements = {
        "\u2014": "-",   # em dash —
        "\u2013": "-",   # en dash –
        "\u201c": '"',   # "
        "\u201d": '"',   # "
        "\u2018": "'",   # '
        "\u2019": "'",   # '
        "\u2026": "...", # …
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    # Fallback: substituir qualquer caractere fora do latin-1 por '?'
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _gerar_pdf(dados):
    """Gera arquivo PDF com os dados do relatório."""
    from fpdf import FPDF

    empresa = _safe_text(get_config("empresa_nome", "Operario - Servicos e Locacoes"))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cabeçalho
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, empresa, ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, _safe_text(f"Relatorio Mensal - {dados['mes']}"), ln=True, align="C")
    pdf.ln(10)

    # Resumo Financeiro
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Resumo Financeiro", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Faturamento Bruto: {_formatar_brl(dados['faturamento_bruto'])}", ln=True)
    pdf.cell(0, 7, f"Despesas Totais: {_formatar_brl(dados['despesas_total'])}", ln=True)
    pdf.cell(0, 7, f"Lucro Real: {_formatar_brl(dados['lucro_real'])}", ln=True)
    pdf.cell(0, 7, _safe_text(f"Numero de Locacoes: {dados['num_locacoes']}"), ln=True)
    pdf.ln(8)

    # Despesas por Categoria
    if dados["despesas_por_categoria"]:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Despesas por Categoria", ln=True)
        pdf.set_font("Helvetica", "", 11)
        for cat, val in dados["despesas_por_categoria"].items():
            label = CATEGORIAS_LABELS.get(cat, cat)
            pdf.cell(0, 7, _safe_text(f"  {label}: {_formatar_brl(val)}"), ln=True)
        pdf.ln(8)

    # Ocupação por Equipamento
    if dados["ocupacao_detalhada"]:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, _safe_text("Taxa de Ocupacao por Equipamento"), ln=True)
        pdf.set_font("Helvetica", "", 11)
        for item in dados["ocupacao_detalhada"]:
            pdf.cell(0, 7, _safe_text(f"  {item['Equipamento']}: {item['Taxa de Ocupação (%)']}%"), ln=True)
        pdf.ln(8)

    # Rodapé
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 7, f"Gerado em {date.today().strftime('%d/%m/%Y')}", ln=True, align="C")

    output = BytesIO()
    pdf.output(output)
    output.seek(0)
    return output


def render():
    st.title("📋 Relatórios")

    # ──────────────────────────────────────────
    # 1. Seletor de mês
    # ──────────────────────────────────────────
    st.subheader("Selecione o Mês")

    col_ano, col_mes = st.columns(2)
    with col_ano:
        ano = st.selectbox(
            "Ano",
            list(range(date.today().year, date.today().year - 5, -1)),
            key="rel_ano",
        )
    with col_mes:
        meses_nomes = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ]
        mes_idx = st.selectbox(
            "Mês",
            list(range(1, 13)),
            index=date.today().month - 1,
            format_func=lambda x: meses_nomes[x - 1],
            key="rel_mes",
        )

    mes_selecionado = f"{ano}-{mes_idx:02d}"
    st.markdown(f"**Período selecionado:** {meses_nomes[mes_idx - 1]} de {ano}")

    st.markdown("---")

    # ──────────────────────────────────────────
    # 2. Dados do relatório
    # ──────────────────────────────────────────
    dados = _dados_relatorio(mes_selecionado)

    st.subheader("Resumo Financeiro")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Faturamento Bruto", _formatar_brl(dados["faturamento_bruto"]))
    with c2:
        st.metric("Lucro Real", _formatar_brl(dados["lucro_real"]))
    with c3:
        st.metric("Despesas Totais", _formatar_brl(dados["despesas_total"]))
    with c4:
        st.metric("Nº de Locações", dados["num_locacoes"])

    st.markdown("---")

    # Despesas por categoria
    st.subheader("Despesas por Categoria")
    desp_cat = dados["despesas_por_categoria"]
    if desp_cat:
        for cat, val in desp_cat.items():
            label = CATEGORIAS_LABELS.get(cat, cat)
            st.write(f"- **{label}:** {_formatar_brl(val)}")
    else:
        st.info("Nenhuma despesa registrada neste mês.")

    st.markdown("---")

    # Ocupação por equipamento
    st.subheader("Taxa de Ocupação por Equipamento")
    if dados["ocupacao_detalhada"]:
        for item in dados["ocupacao_detalhada"]:
            col_nome, col_barra = st.columns([1, 3])
            with col_nome:
                st.write(f"**{item['Equipamento']}**")
            with col_barra:
                taxa = item["Taxa de Ocupação (%)"]
                st.progress(min(taxa / 100, 1.0), text=f"{taxa}%")
    else:
        st.info("Nenhum equipamento cadastrado.")

    st.markdown("---")

    # ──────────────────────────────────────────
    # 3. Exportações
    # ──────────────────────────────────────────
    st.subheader("Exportar Relatório")

    col_excel, col_pdf = st.columns(2)

    with col_excel:
        excel_data = _gerar_excel(dados)
        nome_excel = f"relatorio_{mes_selecionado}.xlsx"
        st.download_button(
            label="📥 Exportar para Excel (.xlsx)",
            data=excel_data,
            file_name=nome_excel,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_pdf:
        pdf_data = _gerar_pdf(dados)
        nome_pdf = f"relatorio_{mes_selecionado}.pdf"
        st.download_button(
            label="📥 Exportar para PDF",
            data=pdf_data,
            file_name=nome_pdf,
            mime="application/pdf",
            use_container_width=True,
        )
