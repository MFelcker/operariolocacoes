"""
Módulo de Configurações — parâmetros da empresa, equipamentos e backup.
"""
import streamlit as st
import shutil
import os
from datetime import date, datetime
from database import (
    get_config, set_config,
    listar_equipamentos, criar_equipamento, atualizar_equipamento, excluir_equipamento,
    DB_PATH,
)


def render():
    st.header("⚙️ Configurações")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏢 Dados da Empresa",
        "🔢 Parâmetros",
        "🖥️ Equipamentos",
        "💾 Backup",
    ])

    # ── Dados da Empresa ──────────────────────
    with tab1:
        st.subheader("Dados da Empresa")
        nome = st.text_input("Nome da empresa", value=get_config("empresa_nome"))
        cnpj = st.text_input("CNPJ", value=get_config("empresa_cnpj"))
        responsavel = st.text_input("Responsável", value=get_config("empresa_responsavel"))

        if st.button("Salvar dados da empresa", key="salvar_empresa"):
            set_config("empresa_nome", nome)
            set_config("empresa_cnpj", cnpj)
            set_config("empresa_responsavel", responsavel)
            st.success("Dados da empresa salvos com sucesso!")

    # ── Parâmetros ────────────────────────────
    with tab2:
        st.subheader("Parâmetros Operacionais")

        col1, col2 = st.columns(2)
        with col1:
            diaria = st.number_input(
                "Valor padrão da diária (R$)",
                min_value=0.0, step=5.0, format="%.2f",
                value=float(get_config("valor_diaria_padrao", "75.00")),
            )
            produto = st.number_input(
                "Valor do produto extra (R$/500ml)",
                min_value=0.0, step=1.0, format="%.2f",
                value=float(get_config("valor_produto_extra", "15.00")),
            )
            estoque_min = st.number_input(
                "Estoque mínimo de sabão para alerta (ml)",
                min_value=0, step=500,
                value=int(get_config("estoque_minimo_ml", "2000")),
            )
        with col2:
            dias_inativo = st.number_input(
                "Dias sem locação para alerta de cliente inativo",
                min_value=1, step=5,
                value=int(get_config("dias_cliente_inativo", "30")),
            )
            reserva = st.number_input(
                "Reserva mensal de manutenção (R$)",
                min_value=0.0, step=10.0, format="%.2f",
                value=float(get_config("reserva_manutencao", "100.00")),
            )

        if st.button("Salvar parâmetros", key="salvar_params"):
            set_config("valor_diaria_padrao", f"{diaria:.2f}")
            set_config("valor_produto_extra", f"{produto:.2f}")
            set_config("estoque_minimo_ml", str(estoque_min))
            set_config("dias_cliente_inativo", str(dias_inativo))
            set_config("reserva_manutencao", f"{reserva:.2f}")
            st.success("Parâmetros salvos com sucesso!")

    # ── Equipamentos ──────────────────────────
    with tab3:
        st.subheader("Cadastro de Equipamentos")

        with st.expander("➕ Novo Equipamento"):
            eq_nome = st.text_input("Nome do equipamento", key="eq_nome")
            eq_desc = st.text_area("Descrição", key="eq_desc")
            eq_data = st.date_input("Data de aquisição", value=date.today(), key="eq_data")
            eq_custo = st.number_input("Custo de aquisição (R$)", min_value=0.0, step=100.0, format="%.2f", key="eq_custo")
            eq_status = st.selectbox("Status", ["disponivel", "em_manutencao", "inativo"],
                                     format_func=lambda x: {"disponivel": "Disponível", "em_manutencao": "Em Manutenção", "inativo": "Inativo"}[x],
                                     key="eq_status")

            if st.button("Salvar equipamento", key="salvar_eq"):
                if not eq_nome.strip():
                    st.error("Nome do equipamento é obrigatório.")
                else:
                    criar_equipamento(eq_nome.strip(), eq_desc, eq_data.isoformat(), eq_custo, eq_status)
                    st.success(f"Equipamento '{eq_nome}' cadastrado com sucesso!")
                    st.rerun()

        # Listar equipamentos
        equips = listar_equipamentos()
        if not equips:
            st.info("Nenhum equipamento cadastrado.")
        else:
            STATUS_LABELS = {
                "disponivel": "🟢 Disponível",
                "em_manutencao": "🟡 Em Manutenção",
                "inativo": "🔴 Inativo",
            }
            for eq in equips:
                status_label = STATUS_LABELS.get(eq["status"], eq["status"])
                with st.expander(f"{eq['nome']} — {status_label}"):
                    ed_nome = st.text_input("Nome", value=eq["nome"], key=f"ed_nome_{eq['id']}")
                    ed_desc = st.text_area("Descrição", value=eq["descricao"] or "", key=f"ed_desc_{eq['id']}")
                    ed_data = st.date_input(
                        "Data de aquisição",
                        value=datetime.strptime(eq["data_aquisicao"], "%Y-%m-%d").date() if eq["data_aquisicao"] else date.today(),
                        key=f"ed_data_{eq['id']}",
                    )
                    ed_custo = st.number_input("Custo de aquisição (R$)", min_value=0.0, step=100.0, format="%.2f",
                                               value=float(eq["custo_aquisicao"] or 0), key=f"ed_custo_{eq['id']}")
                    status_opts = ["disponivel", "em_manutencao", "inativo"]
                    ed_status = st.selectbox(
                        "Status", status_opts,
                        index=status_opts.index(eq["status"]) if eq["status"] in status_opts else 0,
                        format_func=lambda x: {"disponivel": "Disponível", "em_manutencao": "Em Manutenção", "inativo": "Inativo"}[x],
                        key=f"ed_status_{eq['id']}",
                    )

                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Salvar alterações", key=f"salvar_eq_{eq['id']}"):
                            atualizar_equipamento(eq["id"], ed_nome, ed_desc, ed_data.isoformat(), ed_custo, ed_status)
                            st.success("Equipamento atualizado!")
                            st.rerun()
                    with col_b:
                        confirmar = st.checkbox("Confirmar exclusão", key=f"conf_del_eq_{eq['id']}")
                        if confirmar:
                            if st.button("🗑️ Excluir", key=f"del_eq_{eq['id']}"):
                                excluir_equipamento(eq["id"])
                                st.success("Equipamento excluído!")
                                st.rerun()

    # ── Backup ────────────────────────────────
    with tab4:
        st.subheader("Backup do Banco de Dados")

        st.info(f"Caminho do banco de dados: `{DB_PATH}`")

        pasta_backup = st.text_input(
            "Pasta para backup",
            value=get_config("backup_pasta", ""),
            placeholder="Ex.: /home/usuario/backups",
        )

        auto_backup = st.checkbox(
            "Backup automático diário",
            value=get_config("backup_automatico", "0") == "1",
        )

        if st.button("Salvar configurações de backup", key="salvar_backup_cfg"):
            set_config("backup_pasta", pasta_backup)
            set_config("backup_automatico", "1" if auto_backup else "0")
            st.success("Configurações de backup salvas!")

        st.markdown("---")

        if st.button("📦 Fazer backup agora", key="fazer_backup", type="primary"):
            pasta = pasta_backup.strip() or os.path.dirname(DB_PATH)
            if not os.path.isdir(pasta):
                try:
                    os.makedirs(pasta, exist_ok=True)
                except Exception as e:
                    st.error(f"Erro ao criar pasta de backup: {e}")
                    pasta = None

            if pasta:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                destino = os.path.join(pasta, f"operario_backup_{timestamp}.db")
                try:
                    shutil.copy2(DB_PATH, destino)
                    st.success(f"Backup realizado com sucesso!\n\n📁 `{destino}`")
                except Exception as e:
                    st.error(f"Erro ao fazer backup: {e}")
