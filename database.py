"""
Módulo de banco de dados — SQLite.
Contém criação de tabelas e funções CRUD para todos os módulos.
"""
import sqlite3
import os
from datetime import datetime, date
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "operario.db")


@contextmanager
def get_conn():
    """Abre conexão com o banco, habilita FK e fecha ao sair."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ──────────────────────────────────────────────
# Criação de tabelas
# ──────────────────────────────────────────────
def init_db():
    """Cria todas as tabelas caso não existam."""
    with get_conn() as conn:
        c = conn.cursor()

        # Configurações gerais (chave-valor)
        c.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)

        # Equipamentos
        c.execute("""
            CREATE TABLE IF NOT EXISTS equipamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT,
                data_aquisicao DATE,
                custo_aquisicao REAL DEFAULT 0,
                status TEXT DEFAULT 'disponivel',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Clientes
        c.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                endereco TEXT,
                observacoes TEXT,
                inadimplente INTEGER DEFAULT 0,
                ocorrencia_dano INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ativo',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Locações
        c.execute("""
            CREATE TABLE IF NOT EXISTS locacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                equipamento_id INTEGER NOT NULL,
                data_saida DATE NOT NULL,
                data_retorno_prevista DATE NOT NULL,
                data_retorno_efetiva DATE,
                valor_diaria REAL NOT NULL,
                sabao_ml INTEGER DEFAULT 500,
                valor_sabao_extra REAL DEFAULT 0,
                status TEXT DEFAULT 'ativa',
                observacoes TEXT,
                dano_descricao TEXT,
                dano_valor REAL DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id)
            )
        """)

        # Despesas — parcelas de equipamentos
        c.execute("""
            CREATE TABLE IF NOT EXISTS parcelas_equipamento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipamento_id INTEGER,
                nome_equipamento TEXT NOT NULL,
                valor_total REAL NOT NULL,
                num_parcelas INTEGER NOT NULL,
                data_inicio DATE NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id)
            )
        """)

        # Parcelas individuais geradas
        c.execute("""
            CREATE TABLE IF NOT EXISTS parcelas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parcela_equip_id INTEGER NOT NULL,
                numero INTEGER NOT NULL,
                valor REAL NOT NULL,
                data_vencimento DATE NOT NULL,
                paga INTEGER DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parcela_equip_id) REFERENCES parcelas_equipamento(id) ON DELETE CASCADE
            )
        """)

        # Despesas gerais (sabão, gasolina, manutenção, outros)
        c.execute("""
            CREATE TABLE IF NOT EXISTS despesas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT NOT NULL,
                descricao TEXT,
                valor REAL NOT NULL,
                data DATE NOT NULL,
                quantidade_ml INTEGER DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Manutenções
        c.execute("""
            CREATE TABLE IF NOT EXISTS manutencoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipamento_id INTEGER NOT NULL,
                data DATE NOT NULL,
                tipo_servico TEXT NOT NULL,
                custo REAL NOT NULL,
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id)
            )
        """)

        # Movimentações de estoque de sabão
        c.execute("""
            CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                quantidade_ml INTEGER NOT NULL,
                origem TEXT,
                referencia_id INTEGER,
                data DATE NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Inserir configs padrão se não existirem
        defaults = {
            "empresa_nome": "Operário - Serviços e Locações",
            "empresa_cnpj": "",
            "empresa_responsavel": "",
            "valor_diaria_padrao": "75.00",
            "valor_produto_extra": "15.00",
            "estoque_minimo_ml": "2000",
            "dias_cliente_inativo": "30",
            "reserva_manutencao": "100.00",
            "backup_pasta": "",
            "backup_automatico": "0",
        }
        for chave, valor in defaults.items():
            c.execute(
                "INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)",
                (chave, valor),
            )


# ──────────────────────────────────────────────
# Configurações
# ──────────────────────────────────────────────
def get_config(chave, default=""):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?", (chave,)
        ).fetchone()
        return row["valor"] if row else default


def set_config(chave, valor):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
            (chave, str(valor)),
        )


# ──────────────────────────────────────────────
# Equipamentos
# ──────────────────────────────────────────────
def listar_equipamentos(status=None):
    with get_conn() as conn:
        if status:
            return conn.execute(
                "SELECT * FROM equipamentos WHERE status = ? ORDER BY nome", (status,)
            ).fetchall()
        return conn.execute("SELECT * FROM equipamentos ORDER BY nome").fetchall()


def get_equipamento(eid):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM equipamentos WHERE id = ?", (eid,)).fetchone()


def criar_equipamento(nome, descricao, data_aquisicao, custo_aquisicao, status="disponivel"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO equipamentos (nome, descricao, data_aquisicao, custo_aquisicao, status) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, data_aquisicao, custo_aquisicao, status),
        )


def atualizar_equipamento(eid, nome, descricao, data_aquisicao, custo_aquisicao, status):
    with get_conn() as conn:
        conn.execute(
            "UPDATE equipamentos SET nome=?, descricao=?, data_aquisicao=?, custo_aquisicao=?, status=? WHERE id=?",
            (nome, descricao, data_aquisicao, custo_aquisicao, status, eid),
        )


def excluir_equipamento(eid):
    with get_conn() as conn:
        conn.execute("DELETE FROM equipamentos WHERE id = ?", (eid,))


# ──────────────────────────────────────────────
# Clientes
# ──────────────────────────────────────────────
def listar_clientes(status=None):
    with get_conn() as conn:
        if status:
            return conn.execute(
                "SELECT * FROM clientes WHERE status = ? ORDER BY nome", (status,)
            ).fetchall()
        return conn.execute("SELECT * FROM clientes ORDER BY nome").fetchall()


def get_cliente(cid):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM clientes WHERE id = ?", (cid,)).fetchone()


def criar_cliente(nome, telefone, endereco, observacoes):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO clientes (nome, telefone, endereco, observacoes) VALUES (?, ?, ?, ?)",
            (nome, telefone, endereco, observacoes),
        )


def atualizar_cliente(cid, nome, telefone, endereco, observacoes, inadimplente, ocorrencia_dano, status):
    with get_conn() as conn:
        conn.execute(
            "UPDATE clientes SET nome=?, telefone=?, endereco=?, observacoes=?, inadimplente=?, ocorrencia_dano=?, status=? WHERE id=?",
            (nome, telefone, endereco, observacoes, inadimplente, ocorrencia_dano, status, cid),
        )


def excluir_cliente(cid):
    with get_conn() as conn:
        conn.execute("DELETE FROM clientes WHERE id = ?", (cid,))


def buscar_clientes(termo):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM clientes WHERE nome LIKE ? OR telefone LIKE ? ORDER BY nome",
            (f"%{termo}%", f"%{termo}%"),
        ).fetchall()


# ──────────────────────────────────────────────
# Locações
# ──────────────────────────────────────────────
def listar_locacoes(mes=None, cliente_id=None, equipamento_id=None, status=None):
    with get_conn() as conn:
        query = """
            SELECT l.*, c.nome as cliente_nome, e.nome as equipamento_nome
            FROM locacoes l
            JOIN clientes c ON l.cliente_id = c.id
            JOIN equipamentos e ON l.equipamento_id = e.id
            WHERE 1=1
        """
        params = []
        if mes:
            query += " AND strftime('%Y-%m', l.data_saida) = ?"
            params.append(mes)
        if cliente_id:
            query += " AND l.cliente_id = ?"
            params.append(cliente_id)
        if equipamento_id:
            query += " AND l.equipamento_id = ?"
            params.append(equipamento_id)
        if status:
            query += " AND l.status = ?"
            params.append(status)
        query += " ORDER BY l.data_saida DESC"
        return conn.execute(query, params).fetchall()


def get_locacao(lid):
    with get_conn() as conn:
        return conn.execute(
            """SELECT l.*, c.nome as cliente_nome, e.nome as equipamento_nome
               FROM locacoes l
               JOIN clientes c ON l.cliente_id = c.id
               JOIN equipamentos e ON l.equipamento_id = e.id
               WHERE l.id = ?""",
            (lid,),
        ).fetchone()


def criar_locacao(cliente_id, equipamento_id, data_saida, data_retorno_prevista,
                  valor_diaria, sabao_ml, valor_sabao_extra, observacoes):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO locacoes (cliente_id, equipamento_id, data_saida,
               data_retorno_prevista, valor_diaria, sabao_ml, valor_sabao_extra, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (cliente_id, equipamento_id, data_saida, data_retorno_prevista,
             valor_diaria, sabao_ml, valor_sabao_extra, observacoes),
        )
        loc_id = c.lastrowid
        # Debitar estoque de sabão
        c.execute(
            """INSERT INTO estoque_movimentacoes (tipo, quantidade_ml, origem, referencia_id, data)
               VALUES ('saida', ?, 'locacao', ?, ?)""",
            (sabao_ml, loc_id, data_saida),
        )
        return loc_id


def atualizar_locacao(lid, cliente_id, equipamento_id, data_saida, data_retorno_prevista,
                      data_retorno_efetiva, valor_diaria, sabao_ml, valor_sabao_extra,
                      status, observacoes, dano_descricao, dano_valor):
    with get_conn() as conn:
        # Buscar sabão anterior para recalcular estoque
        old = conn.execute("SELECT sabao_ml, data_saida FROM locacoes WHERE id = ?", (lid,)).fetchone()
        old_sabao = old["sabao_ml"] if old else 0

        conn.execute(
            """UPDATE locacoes SET cliente_id=?, equipamento_id=?, data_saida=?,
               data_retorno_prevista=?, data_retorno_efetiva=?, valor_diaria=?,
               sabao_ml=?, valor_sabao_extra=?, status=?, observacoes=?,
               dano_descricao=?, dano_valor=? WHERE id=?""",
            (cliente_id, equipamento_id, data_saida, data_retorno_prevista,
             data_retorno_efetiva, valor_diaria, sabao_ml, valor_sabao_extra,
             status, observacoes, dano_descricao, dano_valor, lid),
        )

        # Recalcular movimentação de estoque se sabão mudou
        if sabao_ml != old_sabao:
            conn.execute(
                "DELETE FROM estoque_movimentacoes WHERE origem = 'locacao' AND referencia_id = ?",
                (lid,),
            )
            conn.execute(
                """INSERT INTO estoque_movimentacoes (tipo, quantidade_ml, origem, referencia_id, data)
                   VALUES ('saida', ?, 'locacao', ?, ?)""",
                (sabao_ml, lid, data_saida),
            )


def excluir_locacao(lid):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM estoque_movimentacoes WHERE origem = 'locacao' AND referencia_id = ?",
            (lid,),
        )
        conn.execute("DELETE FROM locacoes WHERE id = ?", (lid,))


def verificar_conflito(equipamento_id, data_saida, data_retorno, excluir_locacao_id=None):
    """Verifica se há conflito de datas para o equipamento."""
    with get_conn() as conn:
        query = """
            SELECT id FROM locacoes
            WHERE equipamento_id = ? AND status = 'ativa'
            AND data_saida <= ? AND data_retorno_prevista >= ?
        """
        params = [equipamento_id, data_retorno, data_saida]
        if excluir_locacao_id:
            query += " AND id != ?"
            params.append(excluir_locacao_id)
        return conn.execute(query, params).fetchone() is not None


def locacoes_por_cliente(cliente_id):
    with get_conn() as conn:
        return conn.execute(
            """SELECT l.*, e.nome as equipamento_nome
               FROM locacoes l JOIN equipamentos e ON l.equipamento_id = e.id
               WHERE l.cliente_id = ? ORDER BY l.data_saida DESC""",
            (cliente_id,),
        ).fetchall()


# ──────────────────────────────────────────────
# Despesas
# ──────────────────────────────────────────────
def listar_despesas(mes=None, categoria=None):
    with get_conn() as conn:
        query = "SELECT * FROM despesas WHERE 1=1"
        params = []
        if mes:
            query += " AND strftime('%Y-%m', data) = ?"
            params.append(mes)
        if categoria:
            query += " AND categoria = ?"
            params.append(categoria)
        query += " ORDER BY data DESC"
        return conn.execute(query, params).fetchall()


def criar_despesa(categoria, descricao, valor, data_desp, quantidade_ml=0):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO despesas (categoria, descricao, valor, data, quantidade_ml) VALUES (?, ?, ?, ?, ?)",
            (categoria, descricao, valor, data_desp, quantidade_ml),
        )
        desp_id = c.lastrowid
        # Se compra de sabão, incrementar estoque
        if categoria == "sabao" and quantidade_ml > 0:
            c.execute(
                """INSERT INTO estoque_movimentacoes (tipo, quantidade_ml, origem, referencia_id, data)
                   VALUES ('entrada', ?, 'compra_sabao', ?, ?)""",
                (quantidade_ml, desp_id, data_desp),
            )
        return desp_id


def atualizar_despesa(did, categoria, descricao, valor, data_desp, quantidade_ml=0):
    with get_conn() as conn:
        old = conn.execute("SELECT categoria, quantidade_ml FROM despesas WHERE id = ?", (did,)).fetchone()

        conn.execute(
            "UPDATE despesas SET categoria=?, descricao=?, valor=?, data=?, quantidade_ml=? WHERE id=?",
            (categoria, descricao, valor, data_desp, quantidade_ml, did),
        )

        # Recalcular estoque de sabão
        if old and old["categoria"] == "sabao":
            conn.execute(
                "DELETE FROM estoque_movimentacoes WHERE origem = 'compra_sabao' AND referencia_id = ?",
                (did,),
            )
        if categoria == "sabao" and quantidade_ml > 0:
            conn.execute(
                """INSERT INTO estoque_movimentacoes (tipo, quantidade_ml, origem, referencia_id, data)
                   VALUES ('entrada', ?, 'compra_sabao', ?, ?)""",
                (quantidade_ml, did, data_desp),
            )


def excluir_despesa(did):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM estoque_movimentacoes WHERE origem = 'compra_sabao' AND referencia_id = ?",
            (did,),
        )
        conn.execute("DELETE FROM despesas WHERE id = ?", (did,))


# ──────────────────────────────────────────────
# Parcelas de equipamento
# ──────────────────────────────────────────────
def listar_parcelas_equipamento():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM parcelas_equipamento ORDER BY data_inicio DESC").fetchall()


def criar_parcelas_equipamento(equipamento_id, nome_equipamento, valor_total, num_parcelas, data_inicio):
    """Cria o registro de parcelamento e gera as parcelas individuais."""
    from dateutil.relativedelta import relativedelta

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO parcelas_equipamento (equipamento_id, nome_equipamento, valor_total, num_parcelas, data_inicio)
               VALUES (?, ?, ?, ?, ?)""",
            (equipamento_id, nome_equipamento, valor_total, num_parcelas, data_inicio),
        )
        pe_id = c.lastrowid
        valor_parcela = round(valor_total / num_parcelas, 2)

        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date() if isinstance(data_inicio, str) else data_inicio
        for i in range(num_parcelas):
            dt_venc = dt_inicio + relativedelta(months=i)
            c.execute(
                "INSERT INTO parcelas (parcela_equip_id, numero, valor, data_vencimento) VALUES (?, ?, ?, ?)",
                (pe_id, i + 1, valor_parcela, dt_venc.isoformat()),
            )
        return pe_id


def listar_parcelas(parcela_equip_id=None, mes=None):
    with get_conn() as conn:
        query = """
            SELECT p.*, pe.nome_equipamento
            FROM parcelas p
            JOIN parcelas_equipamento pe ON p.parcela_equip_id = pe.id
            WHERE 1=1
        """
        params = []
        if parcela_equip_id:
            query += " AND p.parcela_equip_id = ?"
            params.append(parcela_equip_id)
        if mes:
            query += " AND strftime('%Y-%m', p.data_vencimento) = ?"
            params.append(mes)
        query += " ORDER BY p.data_vencimento"
        return conn.execute(query, params).fetchall()


def marcar_parcela_paga(pid, paga=1):
    with get_conn() as conn:
        conn.execute("UPDATE parcelas SET paga = ? WHERE id = ?", (paga, pid))


def excluir_parcelas_equipamento(pe_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM parcelas WHERE parcela_equip_id = ?", (pe_id,))
        conn.execute("DELETE FROM parcelas_equipamento WHERE id = ?", (pe_id,))


# ──────────────────────────────────────────────
# Manutenções
# ──────────────────────────────────────────────
def listar_manutencoes(equipamento_id=None):
    with get_conn() as conn:
        if equipamento_id:
            return conn.execute(
                """SELECT m.*, e.nome as equipamento_nome FROM manutencoes m
                   JOIN equipamentos e ON m.equipamento_id = e.id
                   WHERE m.equipamento_id = ? ORDER BY m.data DESC""",
                (equipamento_id,),
            ).fetchall()
        return conn.execute(
            """SELECT m.*, e.nome as equipamento_nome FROM manutencoes m
               JOIN equipamentos e ON m.equipamento_id = e.id ORDER BY m.data DESC"""
        ).fetchall()


def criar_manutencao(equipamento_id, data_m, tipo_servico, custo, observacoes):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO manutencoes (equipamento_id, data, tipo_servico, custo, observacoes) VALUES (?, ?, ?, ?, ?)",
            (equipamento_id, data_m, tipo_servico, custo, observacoes),
        )


def atualizar_manutencao(mid, equipamento_id, data_m, tipo_servico, custo, observacoes):
    with get_conn() as conn:
        conn.execute(
            "UPDATE manutencoes SET equipamento_id=?, data=?, tipo_servico=?, custo=?, observacoes=? WHERE id=?",
            (equipamento_id, data_m, tipo_servico, custo, observacoes, mid),
        )


def excluir_manutencao(mid):
    with get_conn() as conn:
        conn.execute("DELETE FROM manutencoes WHERE id = ?", (mid,))


# ──────────────────────────────────────────────
# Estoque de sabão
# ──────────────────────────────────────────────
def saldo_estoque():
    """Retorna o saldo atual de sabão em ml."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN tipo = 'entrada' THEN quantidade_ml ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN tipo = 'saida' THEN quantidade_ml ELSE 0 END), 0) as saldo
            FROM estoque_movimentacoes
        """).fetchone()
        return row["saldo"] if row else 0


def listar_movimentacoes_estoque():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM estoque_movimentacoes ORDER BY data DESC, id DESC"
        ).fetchall()


# ──────────────────────────────────────────────
# Funções auxiliares para relatórios / dashboard
# ──────────────────────────────────────────────
def faturamento_mes(mes):
    """Retorna faturamento bruto do mês (YYYY-MM)."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT COALESCE(SUM(
                valor_diaria * (
                    CAST(julianday(COALESCE(data_retorno_efetiva, data_retorno_prevista)) - julianday(data_saida) AS INTEGER) + 1
                ) + valor_sabao_extra + dano_valor
            ), 0) as total
            FROM locacoes
            WHERE strftime('%Y-%m', data_saida) = ?
        """, (mes,)).fetchone()
        return row["total"] if row else 0


def despesas_mes(mes):
    """Retorna total de despesas do mês incluindo parcelas."""
    with get_conn() as conn:
        desp = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) as total FROM despesas WHERE strftime('%Y-%m', data) = ?",
            (mes,),
        ).fetchone()["total"]

        parc = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) as total FROM parcelas WHERE strftime('%Y-%m', data_vencimento) = ?",
            (mes,),
        ).fetchone()["total"]

        return desp + parc


def despesas_por_categoria_mes(mes):
    """Retorna despesas agrupadas por categoria no mês."""
    with get_conn() as conn:
        result = {}
        rows = conn.execute(
            "SELECT categoria, SUM(valor) as total FROM despesas WHERE strftime('%Y-%m', data) = ? GROUP BY categoria",
            (mes,),
        ).fetchall()
        for r in rows:
            result[r["categoria"]] = r["total"]

        parc = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) as total FROM parcelas WHERE strftime('%Y-%m', data_vencimento) = ?",
            (mes,),
        ).fetchone()["total"]
        if parc > 0:
            result["parcelas"] = parc

        return result


def num_locacoes_mes(mes):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as total FROM locacoes WHERE strftime('%Y-%m', data_saida) = ?",
            (mes,),
        ).fetchone()
        return row["total"] if row else 0


def taxa_ocupacao_mes(mes, equipamento_id=None):
    """Calcula % de dias do mês em que cada máquina estava alugada."""
    import calendar
    year, month = int(mes[:4]), int(mes[5:7])
    dias_no_mes = calendar.monthrange(year, month)[1]

    with get_conn() as conn:
        query = """
            SELECT equipamento_id, data_saida,
                   COALESCE(data_retorno_efetiva, data_retorno_prevista) as data_fim
            FROM locacoes
            WHERE (
                (data_saida <= ? AND COALESCE(data_retorno_efetiva, data_retorno_prevista) >= ?)
            )
        """
        inicio_mes = f"{mes}-01"
        fim_mes = f"{mes}-{dias_no_mes:02d}"
        params = [fim_mes, inicio_mes]
        if equipamento_id:
            query += " AND equipamento_id = ?"
            params.append(equipamento_id)

        rows = conn.execute(query, params).fetchall()
        equips = {}
        for r in rows:
            eid = r["equipamento_id"]
            ds = max(datetime.strptime(r["data_saida"], "%Y-%m-%d").date(), date(year, month, 1))
            df = min(datetime.strptime(r["data_fim"], "%Y-%m-%d").date(), date(year, month, dias_no_mes))
            dias = (df - ds).days + 1
            equips[eid] = equips.get(eid, 0) + dias
        return {eid: round(dias / dias_no_mes * 100, 1) for eid, dias in equips.items()}


def ranking_clientes():
    """Retorna ranking de clientes por frequência e valor total."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT c.id, c.nome, COUNT(l.id) as total_locacoes,
                   COALESCE(SUM(
                       l.valor_diaria * (
                           CAST(julianday(COALESCE(l.data_retorno_efetiva, l.data_retorno_prevista)) - julianday(l.data_saida) AS INTEGER) + 1
                       ) + l.valor_sabao_extra + l.dano_valor
                   ), 0) as valor_total
            FROM clientes c
            LEFT JOIN locacoes l ON c.id = l.cliente_id
            GROUP BY c.id
            ORDER BY total_locacoes DESC
        """).fetchall()


def clientes_inativos(dias):
    """Retorna clientes que não alugam há mais de X dias."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT c.*, MAX(l.data_saida) as ultima_locacao,
                   CAST(julianday('now') - julianday(MAX(l.data_saida)) AS INTEGER) as dias_sem_locacao
            FROM clientes c
            LEFT JOIN locacoes l ON c.id = l.cliente_id
            WHERE c.status = 'ativo'
            GROUP BY c.id
            HAVING ultima_locacao IS NOT NULL
               AND CAST(julianday('now') - julianday(MAX(l.data_saida)) AS INTEGER) > ?
            ORDER BY dias_sem_locacao DESC
        """, (dias,)).fetchall()


def ticket_medio():
    """Retorna o ticket médio das locações."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT AVG(
                valor_diaria * (
                    CAST(julianday(COALESCE(data_retorno_efetiva, data_retorno_prevista)) - julianday(data_saida) AS INTEGER) + 1
                ) + valor_sabao_extra
            ) as media
            FROM locacoes
        """).fetchone()
        return row["media"] if row and row["media"] else 0


def faturamento_por_equipamento(equipamento_id):
    """Retorna faturamento total de um equipamento."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT COALESCE(SUM(
                valor_diaria * (
                    CAST(julianday(COALESCE(data_retorno_efetiva, data_retorno_prevista)) - julianday(data_saida) AS INTEGER) + 1
                ) + valor_sabao_extra + dano_valor
            ), 0) as total
            FROM locacoes WHERE equipamento_id = ?
        """, (equipamento_id,)).fetchone()
        return row["total"] if row else 0


def parcelas_pagas_equipamento(equipamento_id):
    """Retorna total de parcelas pagas para um equipamento."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT COALESCE(SUM(p.valor), 0) as total
            FROM parcelas p
            JOIN parcelas_equipamento pe ON p.parcela_equip_id = pe.id
            WHERE pe.equipamento_id = ? AND p.paga = 1
        """, (equipamento_id,)).fetchone()
        return row["total"] if row else 0
