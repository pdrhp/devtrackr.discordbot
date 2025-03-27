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

import discord

# Zona de tempo do Brasil (GMT-3)
BRAZIL_TIMEZONE = pytz.timezone('America/Sao_Paulo')

# Canais especiais
DAILY_CHANNEL_ID = "DAILY_CHANNEL_ID"
TIME_TRACKING_CHANNEL_ID = "TIME_TRACKING_CHANNEL_ID"

DEFAULT_CONFIG = {
    "ADMIN_ROLE_ID": "000000000000000000",
}

# Configurar logger principal
logger = logging.getLogger('team_analysis_bot')


def get_env(key, default=None):
    """
    Obtém uma variável de ambiente, com valor padrão opcional.
    Se o valor padrão for fornecido e a variável não existir, o valor padrão é retornado.
    Caso contrário, uma exceção é levantada.

    Args:
        key: Nome da variável de ambiente.
        default: Valor padrão se a variável não existir.

    Returns:
        O valor da variável de ambiente ou o valor padrão.

    Raises:
        KeyError: Se a variável não existe e nenhum valor padrão foi fornecido.
    """
    value = os.environ.get(key, default)
    if value is None:
        raise KeyError(f"Variável de ambiente '{key}' não encontrada e nenhum valor padrão foi fornecido.")
    return value


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
    # Se o datetime não tiver fuso horário, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Converte para o fuso horário de Brasília
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
    # Usar horário de Brasília
    timestamp = get_br_time().strftime("%Y-%m-%d %H:%M:%S")

    # Formatar a mensagem de log
    user_info = f"@{user.name}#{user.discriminator} (ID: {user.id})"

    if details:
        log_message = f"[{timestamp}] {action}: {user_info} executou {command} - {details}"
    else:
        log_message = f"[{timestamp}] {action}: {user_info} executou {command}"

    # Registrar no logger de comandos específico
    cmd_logger = logging.getLogger('team_analysis_commands')
    cmd_logger.info(log_message)

    # Também registrar no logger principal para debug
    logger.info(f"COMANDO: {log_message}")