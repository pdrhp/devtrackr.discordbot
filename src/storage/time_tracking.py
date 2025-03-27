import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.storage.database import get_connection
from src.utils.config import get_br_time, to_br_timezone


def clock_in(user_id: str, observation: Optional[str] = None) -> Tuple[bool, str]:
    """
    Registra entrada de um usuário.

    Args:
        user_id (str): ID do usuário.
        observation (Optional[str]): Observação opcional sobre o registro.

    Returns:
        Tuple[bool, str]: (Sucesso, Mensagem)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT * FROM time_tracking WHERE user_id = ? AND clock_out IS NULL",
            (user_id,)
        )
        existing_open_record = cursor.fetchone()

        if existing_open_record:
            return False, "Você já tem um registro de ponto aberto. Use `/off` para registrar sua saída."

        timestamp = get_br_time().isoformat()
        cursor.execute(
            "INSERT INTO time_tracking (user_id, clock_in, observation) VALUES (?, ?, ?)",
            (user_id, timestamp, observation)
        )
        conn.commit()

        return True, timestamp

    except sqlite3.Error as e:
        return False, f"Erro ao registrar ponto: {str(e)}"

    finally:
        conn.close()


def clock_out(user_id: str, observation: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
    """
    Registra saída de um usuário.

    Args:
        user_id (str): ID do usuário.
        observation (Optional[str]): Observação opcional sobre o registro.

    Returns:
        Tuple[bool, str, Optional[str]]: (Sucesso, Mensagem, Duração formatada)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT * FROM time_tracking WHERE user_id = ? AND clock_out IS NULL ORDER BY clock_in DESC",
            (user_id,)
        )
        open_record = cursor.fetchone()

        if not open_record:
            return False, "Você não possui um registro de ponto aberto. Use `/on` para registrar sua entrada.", None

        timestamp = get_br_time().isoformat()
        cursor.execute(
            "UPDATE time_tracking SET clock_out = ?, observation = COALESCE(?, observation) WHERE id = ?",
            (timestamp, observation, open_record['id'])
        )
        conn.commit()

        start_time = datetime.fromisoformat(open_record['clock_in'])
        end_time = datetime.fromisoformat(timestamp)

        start_time_br = to_br_timezone(start_time) if start_time.tzinfo else start_time
        end_time_br = to_br_timezone(end_time) if end_time.tzinfo else end_time

        duration = end_time_br - start_time_br

        hours, remainder = divmod(duration.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        duration_str = f"{hours}h {minutes}min"

        return True, timestamp, duration_str

    except sqlite3.Error as e:
        return False, f"Erro ao registrar ponto: {str(e)}", None

    finally:
        conn.close()


def get_user_records(user_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Obtém registros de ponto de um usuário.

    Args:
        user_id (str): ID do usuário.
        start_date (Optional[str]): Data inicial no formato YYYY-MM-DD.
        end_date (Optional[str]): Data final no formato YYYY-MM-DD.

    Returns:
        List[Dict[str, str]]: Lista de registros de ponto.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT * FROM time_tracking WHERE user_id = ?"
        params = [user_id]

        if start_date:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
            start_datetime_br = start_datetime.replace(tzinfo=None).isoformat()
            query += " AND clock_in >= ?"
            params.append(start_datetime_br)

        if end_date:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            end_datetime_br = end_datetime.replace(tzinfo=None).isoformat()
            query += " AND clock_in <= ?"
            params.append(end_datetime_br)

        query += " ORDER BY clock_in ASC"

        cursor.execute(query, params)
        records = cursor.fetchall()

        result = []
        for record in records:
            record_dict = {
                "clock_in": record['clock_in'],
                "clock_out": record['clock_out'],
                "observation": record['observation']
            }
            result.append(record_dict)

        return result

    except sqlite3.Error:
        return []

    finally:
        conn.close()


def get_all_users_records(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, List[Dict[str, str]]]:
    """
    Obtém registros de ponto de todos os usuários.

    Args:
        start_date (Optional[str]): Data inicial no formato YYYY-MM-DD.
        end_date (Optional[str]): Data final no formato YYYY-MM-DD.

    Returns:
        Dict[str, List[Dict[str, str]]]: Dicionário com IDs dos usuários como chaves e listas de registros como valores.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = "SELECT DISTINCT user_id FROM time_tracking"
        cursor.execute(query)
        users = [row['user_id'] for row in cursor.fetchall()]

        result = {}
        for user_id in users:
            records = get_user_records(user_id, start_date, end_date)
            if records:
                result[user_id] = records

        return result

    except sqlite3.Error:
        return {}

    finally:
        conn.close()