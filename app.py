"""
Operário - Serviços e Locações
Aplicativo de gestão de locação de equipamentos.
"""
import streamlit as st
import os
from database import init_db

# Inicializar banco de dados
init_db()

# ──────────────────────────────────────────────
# CSS customizado para identidade visual
# ──────────────────────────────────────────────
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1B3A8C;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stRadio label span {
        color: #FFFFFF !important;
        font-size: 1.05rem;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.2);
    }

    /* Botões primários */
    .stButton > button[kind="primary"], .stButton > button {
        background-color: #1B3A8C;
        color: white;
        border: none;
    }
    .stButton > button:hover {
        background-color: #2B8BE8;
        color: white;
    }

    /* Cabeçalhos */
    h1 { color: #1B3A8C !important; }
    h2 { color: #1B3A8C !important; }
    h3 { color: #2B8BE8 !important; }

    /* Métricas */
    [data-testid="stMetricValue"] {
        color: #1B3A8C !important;
    }

    /* Tabelas */
    thead tr th {
        background-color: #1B3A8C !important;
        color: white !important;
    }
    tbody tr:nth-child(even) {
        background-color: #F4F6FA;
    }

    /* KPI Cards */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #2B8BE8;
        border-radius: 8px;
        padding: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Sidebar — logo + navegação
# ──────────────────────────────────────────────
with st.sidebar:
    # Logo
    logo_path = os.path.join(os.path.dirname(__file__), "logo_png.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=180)
    else:
        st.markdown("### 🔧 Operário")
        st.caption("Serviços e Locações")

    st.markdown("---")

    # Botão de atalho — Nova Locação
    if st.button("➕ Nova Locação", use_container_width=True, type="primary"):
        st.session_state["pagina"] = "📦 Locações"
        st.session_state["abrir_nova_locacao"] = True
        st.rerun()

    st.markdown("---")

    # Menu de navegação
    paginas = [
        "📊 Dashboard",
        "📅 Agenda",
        "📦 Locações",
        "👥 Clientes",
        "💰 Despesas",
        "📈 Inteligência Financeira",
        "🔧 Manutenção",
        "🧴 Estoque de Insumos",
        "📋 Relatórios",
        "📣 Marketing",
        "⚙️ Configurações",
    ]

    pagina_atual = st.session_state.get("pagina", paginas[0])
    if pagina_atual not in paginas:
        pagina_atual = paginas[0]

    pagina = st.radio(
        "Navegação",
        paginas,
        index=paginas.index(pagina_atual),
        label_visibility="collapsed",
    )
    st.session_state["pagina"] = pagina

# ──────────────────────────────────────────────
# Roteamento de páginas
# ──────────────────────────────────────────────
if pagina == "📊 Dashboard":
    from modules.dashboard import render
    render()
elif pagina == "📅 Agenda":
    from modules.agenda import render
    render()
elif pagina == "📦 Locações":
    from modules.locacoes import render
    render()
elif pagina == "👥 Clientes":
    from modules.clientes import render
    render()
elif pagina == "💰 Despesas":
    from modules.despesas import render
    render()
elif pagina == "📈 Inteligência Financeira":
    from modules.financeiro import render
    render()
elif pagina == "🔧 Manutenção":
    from modules.manutencao import render
    render()
elif pagina == "🧴 Estoque de Insumos":
    from modules.estoque import render
    render()
elif pagina == "📋 Relatórios":
    from modules.relatorios import render
    render()
elif pagina == "📣 Marketing":
    from modules.marketing import render
    render()
elif pagina == "⚙️ Configurações":
    from modules.configuracoes import render
    render()
