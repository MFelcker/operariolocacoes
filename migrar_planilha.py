"""
Script de migração dos dados da planilha 'Controle Financeiro Operário'
para o banco de dados SQLite do sistema.
Execução única — popula equipamentos, parcelas, locações e despesas.
"""
import pandas as pd
from datetime import datetime, date
from database import (
    init_db, get_conn,
    criar_equipamento, listar_equipamentos,
    criar_parcelas_equipamento, listar_parcelas, marcar_parcela_paga,
    criar_cliente,
    criar_despesa,
)

ARQUIVO = "Controle financeiro Operário (1).xlsx"


def parse_date(val):
    """Converte valor da planilha para string YYYY-MM-DD."""
    if pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, date):
        return val.isoformat()
    try:
        return datetime.strptime(str(val), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def extrair_registros_razao():
    """Extrai todos os registros da aba RAZÃO como lista de dicts."""
    df = pd.read_excel(ARQUIVO, sheet_name="RAZÃO", header=None)
    registros = []

    # Coluna 0-3: 2025 | Coluna 4-7: 2026
    for _, row in df.iterrows():
        # Lado 2025
        data = parse_date(row[0])
        desc = str(row[1]).strip() if pd.notna(row[1]) else None
        valor = float(row[2]) if pd.notna(row[2]) else None
        pago = str(row[3]).strip().upper() == "PAGO" if pd.notna(row[3]) else False
        if data and desc and valor is not None:
            registros.append({"data": data, "descricao": desc, "valor": valor, "pago": pago})

        # Lado 2026
        data2 = parse_date(row[4])
        desc2 = str(row[5]).strip() if pd.notna(row[5]) else None
        valor2 = float(row[6]) if pd.notna(row[6]) else None
        pago2 = str(row[7]).strip().upper() == "PAGO" if pd.notna(row[7]) else False
        if data2 and desc2 and valor2 is not None:
            registros.append({"data": data2, "descricao": desc2, "valor": valor2, "pago": pago2})

    return registros


def classificar_registro(reg):
    """Classifica cada registro da planilha em categorias do sistema."""
    desc = reg["descricao"]
    valor = reg["valor"]

    # Parcelas de equipamento (ignorar — serão criadas via criar_parcelas_equipamento)
    if "Extratora 01" in desc and "/" in desc:
        return "parcela_ext01"
    if "Extratora 02" in desc and "/" in desc:
        return "parcela_ext02"

    # Diárias = locação (receita)
    if "Diária da extratora" in desc:
        return "diaria"

    # Venda de sabão extra ao cliente (receita)
    if "sabão extra" in desc.lower() or ("compra de sabão" in desc.lower() and valor > 0):
        return "sabao_extra"

    # Compra de sabão em atacado (despesa)
    if "compra de sabão" in desc.lower() and valor < 0:
        return "despesa_sabao"
    if desc.lower() in ("sabão", "sabão e filtro", "produto"):
        return "despesa_sabao"

    # Tráfego / marketing
    if "tráfego" in desc.lower() or "trafego" in desc.lower():
        return "despesa_trafego"

    # Compra de flyers / adesivos
    if "flyer" in desc.lower() or "adesivo" in desc.lower():
        return "despesa_marketing"

    # Borrifadores
    if "borrifador" in desc.lower() or "borrifadores" in desc.lower():
        return "despesa_outros"

    # Compra de filtro
    if "filtro" in desc.lower():
        return "despesa_manutencao"

    # Outros
    if valor < 0:
        return "despesa_outros"

    return "receita_outros"


def migrar():
    """Executa a migração completa."""
    print("Inicializando banco de dados...")
    init_db()

    # Limpar banco antes de migrar
    with get_conn() as conn:
        conn.execute("DELETE FROM estoque_movimentacoes")
        conn.execute("DELETE FROM locacoes")
        conn.execute("DELETE FROM parcelas")
        conn.execute("DELETE FROM parcelas_equipamento")
        conn.execute("DELETE FROM despesas")
        conn.execute("DELETE FROM manutencoes")
        conn.execute("DELETE FROM clientes")
        conn.execute("DELETE FROM equipamentos")
    print("Banco limpo.")

    # ── 1. Criar equipamentos ──────────────────
    print("\nCriando equipamentos...")
    criar_equipamento("Extratora 01", "Máquina extratora de estofados - 1ª máquina",
                       "2025-07-01", 1782.96, "disponivel")
    criar_equipamento("Extratora 02", "Máquina extratora de estofados - 2ª máquina",
                       "2026-01-01", 1420.00, "disponivel")

    equips = listar_equipamentos()
    ext01 = next(e for e in equips if "01" in e["nome"])
    ext02 = next(e for e in equips if "02" in e["nome"])
    print(f"  Extratora 01: ID {ext01['id']}")
    print(f"  Extratora 02: ID {ext02['id']}")

    # ── 2. Criar parcelas ──────────────────────
    print("\nCriando parcelas...")

    # Extratora 01: 12 parcelas de R$148.58, início Jul 2025
    pe01_id = criar_parcelas_equipamento(ext01["id"], "Extratora 01", 1782.96, 12, "2025-07-01")
    # Marcar parcelas pagas (1-10: Jul/2025 a Abr/2026)
    parcelas_01 = listar_parcelas(parcela_equip_id=pe01_id)
    for p in parcelas_01:
        if p["numero"] <= 10:  # 1 a 10 pagas (Jul 2025 a Abr 2026)
            marcar_parcela_paga(p["id"], 1)
    print(f"  Extratora 01: {len(parcelas_01)} parcelas criadas, 10 pagas")

    # Extratora 02: 10 parcelas de R$142.00, início Jan 2026
    pe02_id = criar_parcelas_equipamento(ext02["id"], "Extratora 02", 1420.00, 10, "2026-01-01")
    # Marcar parcelas pagas (1-4: Jan a Abr 2026)
    parcelas_02 = listar_parcelas(parcela_equip_id=pe02_id)
    for p in parcelas_02:
        if p["numero"] <= 4:
            marcar_parcela_paga(p["id"], 1)
    print(f"  Extratora 02: {len(parcelas_02)} parcelas criadas, 4 pagas")

    # ── 3. Criar cliente genérico ──────────────
    print("\nCriando cliente legado...")
    criar_cliente("Cliente Legado", "", "", "Locações importadas da planilha anterior (sem dados do cliente)")

    from database import listar_clientes
    clientes = listar_clientes()
    cliente_legado = clientes[0]
    print(f"  Cliente Legado: ID {cliente_legado['id']}")

    # ── 4. Extrair e classificar registros ─────
    print("\nExtraindo registros da planilha...")
    registros = extrair_registros_razao()
    print(f"  {len(registros)} registros encontrados")

    # Classificar
    contadores = {}
    for reg in registros:
        reg["tipo"] = classificar_registro(reg)
        contadores[reg["tipo"]] = contadores.get(reg["tipo"], 0) + 1

    print("  Classificação:")
    for tipo, qtd in sorted(contadores.items()):
        print(f"    {tipo}: {qtd}")

    # ── 5. Importar diárias como locações ──────
    print("\nImportando locações (diárias)...")
    diarias = [r for r in registros if r["tipo"] == "diaria"]
    sabao_extras = [r for r in registros if r["tipo"] == "sabao_extra"]

    # Agrupar sabão extra por data para associar às diárias
    sabao_por_data = {}
    for s in sabao_extras:
        if s["data"] not in sabao_por_data:
            sabao_por_data[s["data"]] = 0
        sabao_por_data[s["data"]] += s["valor"]

    loc_count = 0
    diarias_por_data = {}
    for d in diarias:
        if d["data"] not in diarias_por_data:
            diarias_por_data[d["data"]] = []
        diarias_por_data[d["data"]].append(d)

    # Sabão extras sem diária no mesmo dia: criar locação própria com diária=0
    for data_str, valor_sabao in sabao_por_data.items():
        if data_str not in diarias_por_data and valor_sabao > 0:
            diarias_por_data[data_str] = [{"data": data_str, "valor": 0, "_only_sabao": True}]

    with get_conn() as conn:
        for data_str, diarias_dia in sorted(diarias_por_data.items()):
            sabao_dia = sabao_por_data.get(data_str, 0)

            for idx, d in enumerate(diarias_dia):
                # Antes de Jan/2026: só Extratora 01
                # A partir de Jan/2026: distribuir entre as duas
                data_d = datetime.strptime(d["data"], "%Y-%m-%d").date()
                if data_d < date(2026, 1, 1):
                    equip_id = ext01["id"]
                else:
                    equip_id = ext01["id"] if idx % 2 == 0 else ext02["id"]

                # Todo o sabão extra do dia vai na primeira locação do dia
                sabao_extra_val = sabao_dia if idx == 0 else 0
                sabao_ml = 500 + (int(sabao_extra_val / 15) * 500) if sabao_extra_val > 0 else 500

                c = conn.cursor()
                c.execute("""
                    INSERT INTO locacoes (cliente_id, equipamento_id, data_saida,
                        data_retorno_prevista, data_retorno_efetiva, valor_diaria,
                        sabao_ml, valor_sabao_extra, status, observacoes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'encerrada', ?)
                """, (
                    cliente_legado["id"], equip_id, d["data"],
                    d["data"], d["data"], d["valor"],
                    sabao_ml, sabao_extra_val,
                    "Importado da planilha" + (" (apenas sabão extra)" if d.get("_only_sabao") else ""),
                ))
                loc_id = c.lastrowid

                # Registrar saída de estoque
                c.execute("""
                    INSERT INTO estoque_movimentacoes (tipo, quantidade_ml, origem, referencia_id, data)
                    VALUES ('saida', ?, 'locacao', ?, ?)
                """, (sabao_ml, loc_id, d["data"]))

                loc_count += 1

    print(f"  {loc_count} locações importadas")
    print(f"  Sabão extra associado em {len([d for d in sabao_por_data if sabao_por_data[d] > 0])} dias")

    # ── 6. Importar despesas ───────────────────
    print("\nImportando despesas...")
    desp_count = 0

    for reg in registros:
        tipo = reg["tipo"]
        valor_abs = abs(reg["valor"])

        if tipo == "despesa_sabao":
            # Compra de sabão em atacado — estimar ml (R$15 = 500ml no varejo, atacado ~R$5/500ml)
            ml_estimado = int(valor_abs / 5) * 500  # estimativa grosseira
            ml_estimado = max(ml_estimado, 500)
            criar_despesa("sabao", reg["descricao"], valor_abs, reg["data"], ml_estimado)
            desp_count += 1

        elif tipo == "despesa_trafego" or tipo == "despesa_marketing":
            criar_despesa("outros", f"Marketing: {reg['descricao']}", valor_abs, reg["data"])
            desp_count += 1

        elif tipo == "despesa_manutencao":
            criar_despesa("manutencao", reg["descricao"], valor_abs, reg["data"])
            desp_count += 1

        elif tipo == "despesa_outros":
            criar_despesa("outros", reg["descricao"], valor_abs, reg["data"])
            desp_count += 1

    print(f"  {desp_count} despesas importadas")

    # ── 7. Resumo final ────────────────────────
    print("\n" + "=" * 50)
    print("MIGRAÇÃO CONCLUÍDA!")
    print("=" * 50)

    with get_conn() as conn:
        n_equip = conn.execute("SELECT COUNT(*) as n FROM equipamentos").fetchone()["n"]
        n_clientes = conn.execute("SELECT COUNT(*) as n FROM clientes").fetchone()["n"]
        n_locacoes = conn.execute("SELECT COUNT(*) as n FROM locacoes").fetchone()["n"]
        n_despesas = conn.execute("SELECT COUNT(*) as n FROM despesas").fetchone()["n"]
        n_parcelas = conn.execute("SELECT COUNT(*) as n FROM parcelas").fetchone()["n"]
        n_parc_pagas = conn.execute("SELECT COUNT(*) as n FROM parcelas WHERE paga = 1").fetchone()["n"]
        n_mov = conn.execute("SELECT COUNT(*) as n FROM estoque_movimentacoes").fetchone()["n"]

        fat_total = conn.execute("""
            SELECT COALESCE(SUM(valor_diaria + valor_sabao_extra), 0) as total FROM locacoes
        """).fetchone()["total"]
        desp_total = conn.execute("""
            SELECT COALESCE(SUM(valor), 0) as total FROM despesas
        """).fetchone()["total"]

    print(f"  Equipamentos: {n_equip}")
    print(f"  Clientes: {n_clientes}")
    print(f"  Locações: {n_locacoes}")
    print(f"  Despesas: {n_despesas}")
    print(f"  Parcelas: {n_parcelas} ({n_parc_pagas} pagas)")
    print(f"  Movimentações estoque: {n_mov}")
    print(f"  Faturamento total (diárias + sabão): R$ {fat_total:,.2f}")
    print(f"  Despesas totais: R$ {desp_total:,.2f}")


if __name__ == "__main__":
    migrar()
