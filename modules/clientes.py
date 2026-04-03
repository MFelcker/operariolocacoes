"""
Módulo Clientes — cadastro, edição, histórico e ranking de clientes.
"""
import streamlit as st
import pandas as pd
from datetime import date

from database import (
    listar_clientes,
    buscar_clientes,
    criar_cliente,
    atualizar_cliente,
    excluir_cliente,
    locacoes_por_cliente,
    ranking_clientes,
)

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
LINHAS_POR_PAGINA = 20
STATUS_OPCOES = ["ativo", "inadimplente", "inativo"]
STATUS_FILTRO = ["Todos", "Ativo", "Inadimplente", "Inativo"]

TEMPLATE_CONFIRMACAO = (
    "Olá {nome}! Sua locação da máquina extratora está confirmada para o dia {data}. "
    "Endereço de entrega: {endereco}. Qualquer dúvida, estou à disposição! "
    "- Operário Locações"
)

TEMPLATE_DEVOLUCAO = (
    "Olá {nome}! Lembrando que a devolução da máquina extratora está prevista para "
    "amanhã ({data}). Por favor, me avise quando estiver pronta para retirada. "
    "Obrigado! - Operário Locações"
)

TEMPLATE_COBRANCA = (
    "Olá {nome}! Verificamos que há um valor pendente referente à sua locação. "
    "Podemos conversar sobre isso? Obrigado! - Operário Locações"
)


def _formatar_brl(valor):
    """Formata valor como R$ X.XXX,XX."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _badge_status(status):
    """Retorna emoji para o status."""
    return {"ativo": "🟢", "inadimplente": "🟡", "inativo": "🔴"}.get(status, "⚪")


# ──────────────────────────────────────────────
# Render principal
# ──────────────────────────────────────────────
def render():
    st.title("👥 Clientes")

    # ── Novo cliente ──────────────────────────
    with st.expander("Novo Cliente", expanded=False):
        _form_novo_cliente()

    st.markdown("---")

    # ── Busca e filtros ───────────────────────
    col_busca, col_filtro = st.columns([3, 1])
    with col_busca:
        termo = st.text_input(
            "🔍 Buscar por nome ou telefone",
            key="cli_busca",
        )
    with col_filtro:
        filtro_status = st.selectbox(
            "Status",
            STATUS_FILTRO,
            key="cli_filtro_status",
        )

    # Obter dados
    if termo:
        clientes = buscar_clientes(termo)
    elif filtro_status != "Todos":
        clientes = listar_clientes(status=filtro_status.lower())
    else:
        clientes = listar_clientes()

    clientes = [dict(c) for c in clientes]

    st.caption(f"{len(clientes)} cliente(s) encontrado(s)")

    # ── Tabela de clientes com paginação ──────
    if clientes:
        _tabela_clientes(clientes)

        st.markdown("---")

        # ── Edição / exclusão / histórico ─────
        _secao_edicao(clientes)
    else:
        st.info("Nenhum cliente encontrado.")

    st.markdown("---")

    # ── Ranking de clientes ───────────────────
    _secao_ranking()

    st.markdown("---")

    # ── Templates WhatsApp ────────────────────
    _secao_whatsapp(clientes)


# ──────────────────────────────────────────────
# Formulário — novo cliente
# ──────────────────────────────────────────────
def _form_novo_cliente():
    with st.form("form_novo_cliente", clear_on_submit=True):
        nome = st.text_input("Nome *")
        telefone = st.text_input("Telefone")
        endereco = st.text_input("Endereço de entrega")
        observacoes = st.text_area("Observações")
        enviado = st.form_submit_button("💾 Salvar cliente")

    if enviado:
        if not nome.strip():
            st.error("O nome é obrigatório.")
        else:
            criar_cliente(nome.strip(), telefone.strip(), endereco.strip(), observacoes.strip())
            st.success(f"Cliente **{nome.strip()}** cadastrado com sucesso!")
            st.rerun()


# ──────────────────────────────────────────────
# Tabela paginada
# ──────────────────────────────────────────────
def _tabela_clientes(clientes):
    total = len(clientes)
    total_paginas = max(1, (total + LINHAS_POR_PAGINA - 1) // LINHAS_POR_PAGINA)

    pagina = st.number_input(
        "Página",
        min_value=1,
        max_value=total_paginas,
        value=1,
        step=1,
        key="cli_pagina",
    )

    inicio = (pagina - 1) * LINHAS_POR_PAGINA
    fim = inicio + LINHAS_POR_PAGINA
    fatia = clientes[inicio:fim]

    dados = []
    for c in fatia:
        dados.append({
            "Nome": c["nome"],
            "Telefone": c.get("telefone", ""),
            "Endereço": c.get("endereco", ""),
            "Status": f'{_badge_status(c["status"])} {c["status"].capitalize()}',
            "Inadimplente": "⚠️ Sim" if c.get("inadimplente") else "Não",
            "Dano": "⚠️ Sim" if c.get("ocorrencia_dano") else "Não",
        })

    df = pd.DataFrame(dados)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Página {pagina} de {total_paginas}")


# ──────────────────────────────────────────────
# Edição, exclusão e histórico
# ──────────────────────────────────────────────
def _secao_edicao(clientes):
    st.subheader("Editar / Excluir / Histórico")

    nomes = {c["id"]: c["nome"] for c in clientes}
    opcoes = ["Selecione um cliente..."] + [
        f'{c["id"]} — {c["nome"]}' for c in clientes
    ]
    escolha = st.selectbox("Selecione o cliente", opcoes, key="cli_select_editar")

    if escolha == "Selecione um cliente...":
        return

    cid = int(escolha.split(" — ")[0])
    cliente = next(c for c in clientes if c["id"] == cid)

    # ── Editar ────────────────────────────────
    with st.expander(f"Editar: {cliente['nome']}", expanded=True):
        with st.form(f"form_editar_{cid}"):
            nome = st.text_input("Nome", value=cliente["nome"])
            telefone = st.text_input("Telefone", value=cliente.get("telefone", ""))
            endereco = st.text_input("Endereço de entrega", value=cliente.get("endereco", ""))
            observacoes = st.text_area("Observações", value=cliente.get("observacoes", ""))

            col1, col2, col3 = st.columns(3)
            with col1:
                inadimplente = st.checkbox(
                    "Inadimplente",
                    value=bool(cliente.get("inadimplente")),
                )
            with col2:
                ocorrencia_dano = st.checkbox(
                    "Ocorrência de dano",
                    value=bool(cliente.get("ocorrencia_dano")),
                )
            with col3:
                status_idx = STATUS_OPCOES.index(cliente["status"]) if cliente["status"] in STATUS_OPCOES else 0
                status = st.selectbox(
                    "Status",
                    STATUS_OPCOES,
                    index=status_idx,
                    format_func=lambda s: s.capitalize(),
                )

            salvar = st.form_submit_button("💾 Salvar alterações")

        if salvar:
            if not nome.strip():
                st.error("O nome é obrigatório.")
            else:
                atualizar_cliente(
                    cid,
                    nome.strip(),
                    telefone.strip(),
                    endereco.strip(),
                    observacoes.strip(),
                    int(inadimplente),
                    int(ocorrencia_dano),
                    status,
                )
                st.success(f"Cliente **{nome.strip()}** atualizado com sucesso!")
                st.rerun()

    # ── Excluir ───────────────────────────────
    st.markdown("#### Excluir cliente")
    confirmacao = st.checkbox(
        f"Confirmo que desejo excluir o cliente **{cliente['nome']}**",
        key=f"cli_confirm_del_{cid}",
    )
    if confirmacao:
        if st.button("🗑️ Excluir cliente", key=f"cli_btn_del_{cid}", type="primary"):
            try:
                excluir_cliente(cid)
                st.success(f"Cliente **{cliente['nome']}** excluído.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    # ── Histórico de locações ─────────────────
    st.markdown("#### Histórico de locações")
    locacoes = locacoes_por_cliente(cid)
    locacoes = [dict(l) for l in locacoes]

    if locacoes:
        dados_loc = []
        for loc in locacoes:
            dados_loc.append({
                "Equipamento": loc.get("equipamento_nome", ""),
                "Data Saída": loc["data_saida"],
                "Retorno Previsto": loc["data_retorno_prevista"],
                "Retorno Efetivo": loc.get("data_retorno_efetiva", "—"),
                "Valor Diária": _formatar_brl(loc["valor_diaria"]),
                "Status": loc["status"].capitalize(),
            })
        df_loc = pd.DataFrame(dados_loc)
        st.dataframe(df_loc, use_container_width=True, hide_index=True)
    else:
        st.info("Este cliente ainda não possui locações registradas.")


# ──────────────────────────────────────────────
# Ranking de clientes
# ──────────────────────────────────────────────
def _secao_ranking():
    st.subheader("🏆 Ranking de Clientes")

    ranking = ranking_clientes()
    ranking = [dict(r) for r in ranking]

    if not ranking:
        st.info("Nenhum dado de ranking disponível.")
        return

    dados_rank = []
    for i, r in enumerate(ranking, start=1):
        dados_rank.append({
            "Posição": f"{i}º",
            "Cliente": r["nome"],
            "Total de Locações": r["total_locacoes"],
            "Valor Total": _formatar_brl(r["valor_total"]),
        })

    df_rank = pd.DataFrame(dados_rank)
    st.dataframe(df_rank, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────
# Templates WhatsApp
# ──────────────────────────────────────────────
def _secao_whatsapp(clientes):
    st.subheader("📱 Modelos de Mensagem WhatsApp")
    st.caption("Selecione um cliente para personalizar as mensagens. Copie o texto usando o ícone no canto do bloco.")

    # Seleção de cliente para preencher template
    opcoes_wp = ["Sem personalização"] + [
        f'{c["id"]} — {c["nome"]}' for c in clientes
    ]
    escolha_wp = st.selectbox("Cliente para personalizar", opcoes_wp, key="cli_wp_select")

    nome_cli = "{nome}"
    endereco_cli = "{endereco}"
    data_cli = date.today().strftime("%d/%m/%Y")

    if escolha_wp != "Sem personalização":
        cid_wp = int(escolha_wp.split(" — ")[0])
        cli_wp = next(c for c in clientes if c["id"] == cid_wp)
        nome_cli = cli_wp["nome"]
        endereco_cli = cli_wp.get("endereco", "{endereco}") or "{endereco}"

    # Confirmação
    st.markdown("**Confirmação de locação**")
    msg_conf = TEMPLATE_CONFIRMACAO.format(nome=nome_cli, data=data_cli, endereco=endereco_cli)
    st.code(msg_conf, language=None)

    # Lembrete de devolução
    st.markdown("**Lembrete de devolução**")
    msg_dev = TEMPLATE_DEVOLUCAO.format(nome=nome_cli, data=data_cli)
    st.code(msg_dev, language=None)

    # Cobrança
    st.markdown("**Lembrete de pagamento**")
    msg_cob = TEMPLATE_COBRANCA.format(nome=nome_cli)
    st.code(msg_cob, language=None)

    st.info("💡 **Copiar:** clique no ícone de cópia (📋) no canto superior direito de cada bloco de texto acima.")
