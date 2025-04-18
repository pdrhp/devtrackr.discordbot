"""
Utilitários de configuração para Team Analysis Discord Bot.
"""
import os
import json
import datetime
from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict, Optional, Union
import pytz
import re

import discord

BRAZIL_TIMEZONE = pytz.timezone('America/Sao_Paulo')

DAILY_CHANNEL_ID = "DAILY_CHANNEL_ID"
TIME_TRACKING_CHANNEL_ID = "TIME_TRACKING_CHANNEL_ID"

DEFAULT_CONFIG = {
    "ADMIN_ROLE_ID": "000000000000000000",
}

logger = logging.getLogger('team_analysis_bot')

TIME_TRACKING_CHANNEL_ID = int(os.getenv("TIME_TRACKING_CHANNEL_ID", "0"))

log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

def configure_logging():
    """Configura o logging com handlers para arquivos e console."""
    logger = logging.getLogger('team_analysis')
    logger.setLevel(logging.DEBUG)

    cmd_logger = logging.getLogger('team_analysis_commands')
    cmd_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(os.path.join(log_dir, 'team_analysis.log'), encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    debug_handler = logging.FileHandler(os.path.join(log_dir, 'debug.log'), encoding='utf-8')
    debug_handler.setLevel(logging.DEBUG)
    debug_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    debug_handler.setFormatter(debug_formatter)

    cmd_file_handler = logging.FileHandler(os.path.join(log_dir, 'commands.log'), encoding='utf-8')
    cmd_file_handler.setLevel(logging.INFO)
    cmd_file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(debug_handler)
    logger.addHandler(console_handler)

    cmd_logger.addHandler(cmd_file_handler)
    cmd_logger.addHandler(debug_handler)
    cmd_logger.addHandler(console_handler)

    return logger

logger = configure_logging()

def get_env(key, default=None):
    """
    Obtém uma variável de ambiente, com valor padrão opcional.
    Se a variável não existir, o valor padrão é retornado.

    Args:
        key: Nome da variável de ambiente.
        default: Valor padrão se a variável não existir.

    Returns:
        O valor da variável de ambiente ou o valor padrão.
    """
    return os.environ.get(key, default)


def get_br_time() -> datetime:
    """
    Retorna a data e hora atual no fuso horário de Brasília.

    Returns:
        datetime: Data e hora atual em GMT-3 (Brasília).
    """
    return datetime.now(tz=BRAZIL_TIMEZONE)


def now_br() -> datetime:
    """
    Alias para get_br_time(). Retorna a data e hora atual no fuso horário de Brasília.

    Returns:
        datetime: Data e hora atual em GMT-3 (Brasília).
    """
    return get_br_time()


def to_br_timezone(dt: datetime) -> datetime:
    """
    Converte um objeto datetime para o fuso horário de Brasília.
    Se o datetime não tiver informação de fuso, assume UTC.

    Args:
        dt (datetime): Objeto datetime para converter.

    Returns:
        datetime: Datetime convertido para GMT-3 (Brasília).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(BRAZIL_TIMEZONE)


def log_command(action: str, user: Union[discord.User, discord.Member], command: str, details: Optional[str] = None):
    """
    Registra a execução de um comando por um usuário.

    Args:
        action (str): Tipo de ação (ex: "EXECUTADO", "ERRO", "REGISTRO")
        user (Union[discord.User, discord.Member]): Usuário que executou o comando
        command (str): Nome do comando executado
        details (Optional[str]): Detalhes adicionais sobre a execução
    """
    timestamp = get_br_time().strftime("%Y-%m-%d %H:%M:%S")

    user_info = f"@{user.name}#{user.discriminator} (ID: {user.id})"

    if details:
        log_message = f"[{timestamp}] {action}: {user_info} executou {command} - {details}"
    else:
        log_message = f"[{timestamp}] {action}: {user_info} executou {command}"

    cmd_logger = logging.getLogger('team_analysis_commands')
    cmd_logger.info(log_message)

    logger.info(f"COMANDO: {log_message}")

def parse_date_string(date_string: Optional[str]) -> Optional[str]:
    """
    Converte uma string de data em vários formatos para o formato interno padrão YYYY-MM-DD.
    Aceita os formatos:
    - YYYY-MM-DD
    - YYYY/MM/DD
    - DD/MM/YYYY

    Args:
        date_string: String de data a ser convertida ou None.

    Returns:
        String de data no formato YYYY-MM-DD ou None se a entrada for None ou inválida.
    """
    if not date_string:
        return None

    date_string = date_string.strip()

    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_string):
        try:
            datetime.strptime(date_string, "%Y-%m-%d")
            return date_string
        except ValueError:
            return None

    if re.match(r'^\d{4}/\d{2}/\d{2}$', date_string):
        try:
            dt = datetime.strptime(date_string, "%Y/%m/%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    if re.match(r'^\d{2}/\d{2}/\d{4}$', date_string):
        try:
            dt = datetime.strptime(date_string, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    return None

def format_date_for_display(date_string: str) -> str:
    """
    Formata uma data no formato interno YYYY-MM-DD para exibição no formato DD/MM/YYYY.

    Args:
        date_string: Data no formato YYYY-MM-DD.

    Returns:
        Data formatada como DD/MM/YYYY.
    """
    try:
        dt = datetime.strptime(date_string, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return date_string