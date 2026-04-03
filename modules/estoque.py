"""
Módulo Estoque de Insumos — acompanhamento do estoque de sabão.
"""
import streamlit as st

from database import (
    saldo_estoque,
    listar_movimentacoes_estoque,
    get_config,
)

ITENS_POR_PAGINA = 20


def render():
    st.title("🧴 Estoque de Insumos")

    # ──────────────────────────────────────────
    # 1. Saldo atual
    # ──────────────────────────────────────────
    st.subheader("Saldo Atual")

    saldo = saldo_estoque()
    estoque_minimo = int(get_config("estoque_minimo_ml", "2000"))

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Estoque Atual", f"{saldo} ml")
    with col2:
        st.metric("Estoque Mínimo Configurado", f"{estoque_minimo} ml")

    if saldo < estoque_minimo:
        st.error(
            f"⚠️ Estoque abaixo do mínimo! Atual: {saldo} ml — "
            f"Mínimo: {estoque_minimo} ml. Registre uma compra de sabão em **Despesas**."
        )
    else:
        st.success(f"✅ Estoque dentro do nível seguro (mínimo: {estoque_minimo} ml).")

    st.markdown("---")

    # ──────────────────────────────────────────
    # 2. Histórico de movimentações
    # ──────────────────────────────────────────
    st.subheader("Histórico de Movimentações")

    movimentacoes = listar_movimentacoes_estoque()

    if not movimentacoes:
        st.info("Nenhuma movimentação de estoque registrada.")
    else:
        total_registros = len(movimentacoes)
        total_paginas = max(1, (total_registros + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)

        if "pag_estoque" not in st.session_state:
            st.session_state["pag_estoque"] = 1
        pagina = st.number_input(
            "Página",
            min_value=1,
            max_value=total_paginas,
            value=st.session_state["pag_estoque"],
            step=1,
            key="pag_estoque_input",
        )
        st.session_state["pag_estoque"] = pagina

        inicio = (pagina - 1) * ITENS_POR_PAGINA
        fim = inicio + ITENS_POR_PAGINA
        pagina_registros = movimentacoes[inicio:fim]

        st.caption(f"Exibindo {inicio + 1}–{min(fim, total_registros)} de {total_registros} registros")

        tipo_labels = {"entrada": "Entrada", "saida": "Saída"}
        origem_labels = {
            "compra_sabao": "Compra de Sabão (Despesas)",
            "locacao": "Locação",
        }

        dados_tabela = []
        for mov in pagina_registros:
            dados_tabela.append({
                "Data": mov["data"],
                "Tipo": tipo_labels.get(mov["tipo"], mov["tipo"]),
                "Quantidade (ml)": mov["quantidade_ml"],
                "Origem": origem_labels.get(mov["origem"], mov["origem"] or "—"),
            })

        st.table(dados_tabela)

    st.markdown("---")

    # ──────────────────────────────────────────
    # 3. Nota informativa
    # ──────────────────────────────────────────
    st.info(
        "ℹ️ **Como funciona o estoque:**\n\n"
        "- **Entradas** são geradas automaticamente ao registrar compras de sabão no módulo **Despesas**.\n"
        "- **Saídas** são geradas automaticamente ao criar ou atualizar **Locações**.\n\n"
        "Para adicionar estoque, registre uma despesa de sabão. "
        "Para consumir estoque, crie uma nova locação."
    )
