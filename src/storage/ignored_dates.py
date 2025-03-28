"""Módulo para gerenciar configurações de datas ignoradas para cobrança de daily."""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Union

from src.storage.database import get_connection
from src.utils.config import get_br_time

logger = logging.getLogger('team_analysis_bot')

def _create_tables_if_not_exists():
    """Cria as tabelas necessárias no banco de dados se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ignored_dates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL
        )
        ''')

        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Erro ao criar tabelas de datas ignoradas: {e}")
    finally:
        conn.close()

def add_ignored_date(start_date: str, end_date: str, created_by: str) -> bool:
    """
    Adiciona uma data ou período para ser ignorado na cobrança de daily.

    Args:
        start_date: Data inicial no formato YYYY-MM-DD
        end_date: Data final no formato YYYY-MM-DD (pode ser igual à start_date para um dia específico)
        created_by: ID do usuário que criou a configuração

    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    _create_tables_if_not_exists()

    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        logger.error(f"Formato de data inválido: {start_date} ou {end_date}")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    try:
        now = get_br_time().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO ignored_dates (start_date, end_date, created_at, created_by) VALUES (?, ?, ?, ?)",
            (start_date, end_date, now, created_by)
        )
        conn.commit()
        logger.info(f"Data ignorada adicionada: {start_date} a {end_date} por {created_by}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Erro ao adicionar data ignorada: {e}")
        return False
    finally:
        conn.close()

def remove_ignored_date(date_id: int) -> bool:
    """
    Remove uma data ignorada pelo seu ID.

    Args:
        date_id: ID da data ignorada a ser removida

    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM ignored_dates WHERE id = ?", (date_id,))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"Data ignorada removida: ID {date_id}")
            return True
        else:
            logger.warning(f"Tentativa de remover data ignorada inexistente: ID {date_id}")
            return False
    except sqlite3.Error as e:
        logger.error(f"Erro ao remover data ignorada: {e}")
        return False
    finally:
        conn.close()

def get_all_ignored_dates() -> List[Dict[str, Union[int, str]]]:
    """
    Obtém todas as datas ignoradas configuradas.

    Returns:
        List[Dict]: Lista de dicionários com as informações das datas ignoradas
    """
    _create_tables_if_not_exists()

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM ignored_dates ORDER BY start_date")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter datas ignoradas: {e}")
        return []
    finally:
        conn.close()

def parse_date_config(date_config: str) -> List[Tuple[str, str]]:
    """
    Analisa uma string de configuração de datas ignoradas e retorna uma lista de tuplas (data_inicial, data_final).

    Formatos aceitos:
    - "2023-12-25" - data única (será tratada como intervalo do mesmo dia)
    - "2023-12-25,2023-12-26" - múltiplas datas únicas separadas por vírgula
    - "2023-12-24-2024-01-03" - intervalo de datas (do primeiro ao segundo dia)
    - Combinação dos formatos acima separados por vírgula

    Args:
        date_config: String com configuração de datas

    Returns:
        List[Tuple[str, str]]: Lista de tuplas (data_inicial, data_final)
    """
    result = []
    if not date_config or not date_config.strip():
        return result

    logger.info(f"Processando configuração de datas: '{date_config}'")

    parts = [p.strip() for p in date_config.split(',')]

    for part in parts:
        logger.info(f"Processando parte: '{part}'")

        if part.count('-') == 2:
            try:
                datetime.strptime(part, "%Y-%m-%d")
                result.append((part, part))
                logger.info(f"Data única válida: {part}")
            except ValueError as e:
                logger.warning(f"Formato de data único inválido: {part} - {str(e)}")

        elif part.count('-') > 2:
            try:
                date_parts = part.split('-')
                if len(date_parts) == 6:
                    start_date = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"
                    end_date = f"{date_parts[3]}-{date_parts[4]}-{date_parts[5]}"

                    datetime.strptime(start_date, "%Y-%m-%d")
                    datetime.strptime(end_date, "%Y-%m-%d")

                    result.append((start_date, end_date))
                    logger.info(f"Intervalo válido: {start_date} até {end_date}")
                else:
                    logger.warning(f"Formato de intervalo inválido (número incorreto de partes): {part}")
            except ValueError as e:
                logger.warning(f"Erro validando intervalo de datas: {part} - {str(e)}")
            except Exception as e:
                logger.warning(f"Erro ao processar intervalo de datas: {part} - {str(e)}")
        else:
            logger.warning(f"Formato não reconhecido: {part}")

    logger.info(f"Configuração processada com {len(result)} entradas válidas")
    return result

def should_ignore_date(date: datetime) -> bool:
    """
    Verifica se uma data específica deve ser ignorada para cobrança de daily.

    Args:
        date: Data a ser verificada

    Returns:
        bool: True se a data deve ser ignorada, False caso contrário
    """
    date_str = date.strftime("%Y-%m-%d")
    ignored_dates = get_all_ignored_dates()

    for ignored in ignored_dates:
        start_date = ignored['start_date']
        end_date = ignored['end_date']

        if start_date <= date_str <= end_date:
            return True

    return False

def clear_all_ignored_dates() -> bool:
    """
    Remove todas as datas ignoradas configuradas (função administrativa).

    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM ignored_dates")
        conn.commit()
        logger.info(f"Todas as datas ignoradas foram removidas")
        return True
    except sqlite3.Error as e:
        logger.error(f"Erro ao remover todas as datas ignoradas: {e}")
        return False
    finally:
        conn.close()