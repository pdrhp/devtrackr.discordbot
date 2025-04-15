import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

from src.storage.database import get_connection
from src.storage.users import get_user, get_users_by_role
from src.utils.config import get_br_time, BRAZIL_TIMEZONE

logger = logging.getLogger('team_analysis_bot')


def submit_daily_update(user_id: str, content: str, report_date: Optional[str] = None) -> Tuple[bool, str]:
    """
    Envia ou atualiza uma atualização diária.

    Args:
        user_id (str): ID do usuário no Discord.
        content (str): Conteúdo da atualização diária.
        report_date (Optional[str]): Data do relatório no formato YYYY-MM-DD. Se None, usa o dia anterior.

    Returns:
        Tuple[bool, str]: (Sucesso, Mensagem)
    """
    user = get_user(user_id)
    if not user:
        return False, "Você não está registrado no sistema. Peça a um administrador para registrá-lo primeiro."

    if not report_date:
        yesterday = get_br_time() - timedelta(days=1)
        report_date = yesterday.strftime("%Y-%m-%d")

    try:
        datetime.strptime(report_date, "%Y-%m-%d")
    except ValueError:
        return False, f"Formato de data inválido: {report_date}. Use o formato YYYY-MM-DD."

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT * FROM daily_updates WHERE user_id = ? AND report_date = ?",
            (user_id, report_date)
        )
        existing_report = cursor.fetchone()

        now = get_br_time().isoformat()

        if existing_report:
            cursor.execute(
                "UPDATE daily_updates SET content = ?, last_updated_at = ? WHERE id = ?",
                (content, now, existing_report['id'])
            )
            conn.commit()
            return True, f"Atualização diária para {report_date} foi atualizada com sucesso."
        else:
            cursor.execute(
                "INSERT INTO daily_updates (user_id, report_date, content, submitted_at, last_updated_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, report_date, content, now, now)
            )
            conn.commit()
            return True, f"Atualização diária para {report_date} foi enviada com sucesso."

    except sqlite3.Error as e:
        return False, f"Erro ao salvar atualização diária: {str(e)}"

    finally:
        conn.close()


def get_user_daily_updates(user_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtém as atualizações diárias de um usuário em um período.

    Args:
        user_id (str): ID do usuário no Discord.
        start_date (Optional[str]): Data inicial no formato YYYY-MM-DD.
        end_date (Optional[str]): Data final no formato YYYY-MM-DD.

    Returns:
        List[Dict[str, Any]]: Lista de atualizações diárias.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT * FROM daily_updates WHERE user_id = ?"
        params = [user_id]

        if start_date:
            query += " AND report_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND report_date <= ?"
            params.append(end_date)

        query += " ORDER BY report_date DESC"

        cursor.execute(query, params)
        updates = cursor.fetchall()

        return [dict(update) for update in updates]

    except sqlite3.Error:
        return []

    finally:
        conn.close()


def get_all_daily_updates(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Obtém todas as atualizações diárias no período especificado, agrupadas por usuário.

    Args:
        start_date (Optional[str]): Data inicial no formato YYYY-MM-DD.
        end_date (Optional[str]): Data final no formato YYYY-MM-DD.

    Returns:
        Dict[str, List[Dict[str, Any]]]: Dicionário com IDs dos usuários como chaves e listas de atualizações como valores.
    """
    logger.debug(f"[DEBUG] get_all_daily_updates: Iniciando busca para período {start_date} a {end_date}")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT * FROM daily_updates"
        params = []

        if start_date or end_date:
            query += " WHERE"

        if start_date:
            query += " report_date >= ?"
            params.append(start_date)

            if end_date:
                query += " AND"

        if end_date:
            query += " report_date <= ?"
            params.append(end_date)

        query += " ORDER BY user_id, report_date DESC"

        logger.debug(f"[DEBUG] get_all_daily_updates: Executando query: {query} com params: {params}")

        cursor.execute(query, params)
        all_updates = cursor.fetchall()

        logger.debug(f"[DEBUG] get_all_daily_updates: Recuperadas {len(all_updates)} atualizações do banco")

        results = {}
        for update in all_updates:
            user_id = update['user_id']
            if user_id not in results:
                results[user_id] = []

            results[user_id].append(dict(update))

        logger.debug(f"[DEBUG] get_all_daily_updates: Organizadas atualizações para {len(results)} usuários")

        for user_id, updates in results.items():
            logger.debug(f"[DEBUG] get_all_daily_updates: Usuário {user_id} tem {len(updates)} atualizações")

        return results

    except sqlite3.Error as e:
        logger.error(f"[DEBUG] get_all_daily_updates: Erro SQL: {str(e)}")
        return {}

    finally:
        conn.close()


def get_missing_updates(for_date: Optional[str] = None) -> List[str]:
    """
    Obtém lista de IDs de usuários do tipo 'teammember' que não enviaram atualização para a data especificada.
    Finais de semana (sábado e domingo) são automaticamente ignorados.
    Quando a verificação é feita em uma segunda-feira, a função verifica a sexta-feira anterior.

    Args:
        for_date (Optional[str]): Data para verificar no formato YYYY-MM-DD. Se None, usa o dia anterior.

    Returns:
        List[str]: Lista de IDs de usuários que não enviaram atualização.
    """
    if not for_date:
        yesterday = get_br_time() - timedelta(days=1)
        today_weekday = get_br_time().weekday()
        yesterday_weekday = yesterday.weekday()

        logger.info(f"Verificando atualizações pendentes: hoje é dia {get_br_time().strftime('%Y-%m-%d')} (weekday={today_weekday}), verificando dia {yesterday.strftime('%Y-%m-%d')} (weekday={yesterday_weekday})")

        if yesterday.weekday() == 6:
            yesterday = get_br_time() - timedelta(days=3)
            logger.info(f"Dia anterior é domingo, verificando sexta-feira: {yesterday.strftime('%Y-%m-%d')}")
        elif yesterday.weekday() == 5:
            yesterday = get_br_time() - timedelta(days=2)
            logger.info(f"Dia anterior é sábado, verificando sexta-feira: {yesterday.strftime('%Y-%m-%d')}")

        for_date = yesterday.strftime("%Y-%m-%d")

    check_date = datetime.strptime(for_date, "%Y-%m-%d")
    if check_date.weekday() >= 5:
        logger.info(f"Data {for_date} é um final de semana (weekday={check_date.weekday()}), retornando lista vazia")
        return []

    team_members = get_users_by_role("teammember")
    team_member_ids = [tm['user_id'] for tm in team_members]

    if not team_member_ids:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    try:
        placeholders = ','.join(['?'] * len(team_member_ids))
        query = f"SELECT DISTINCT user_id FROM daily_updates WHERE report_date = ? AND user_id IN ({placeholders})"
        params = [for_date] + team_member_ids

        cursor.execute(query, params)
        submitted_users = [row['user_id'] for row in cursor.fetchall()]

        missing_users = [user_id for user_id in team_member_ids if user_id not in submitted_users]

        return missing_users

    except sqlite3.Error:
        return []

    finally:
        conn.close()


def clear_all_daily_updates() -> Tuple[bool, str]:
    """
    Limpa todos os registros de atualizações diárias.
    Esta função deve ser usada apenas para fins de teste.

    Returns:
        Tuple[bool, str]: (Sucesso, Mensagem)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) as count FROM daily_updates")
        count = cursor.fetchone()['count']

        cursor.execute("DELETE FROM daily_updates")
        conn.commit()

        br_time = get_br_time().strftime("%d/%m/%Y %H:%M:%S")
        return True, f"Todos os {count} registros de atualizações diárias foram removidos com sucesso. Horário de Brasília: {br_time}"
    except sqlite3.Error as e:
        return False, f"Erro ao limpar atualizações diárias: {str(e)}"
    finally:
        conn.close()


def has_submitted_daily_update(user_id: str, report_date: Optional[str] = None) -> bool:
    """
    Verifica se um usuário já enviou atualização diária para a data especificada.

    Args:
        user_id (str): ID do usuário no Discord.
        report_date (Optional[str]): Data para verificar no formato YYYY-MM-DD. Se None, usa o dia anterior.

    Returns:
        bool: True se o usuário já enviou atualização para a data, False caso contrário.
    """
    if not report_date:
        yesterday = get_br_time() - timedelta(days=1)
        report_date = yesterday.strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT COUNT(*) as count FROM daily_updates WHERE user_id = ? AND report_date = ?",
            (user_id, report_date)
        )
        result = cursor.fetchone()
        return result and result['count'] > 0

    except sqlite3.Error:
        return False

    finally:
        conn.close()