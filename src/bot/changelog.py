"""
Módulo para envio de changelogs no Discord.
"""
import logging
import os
from typing import Optional

import discord
from discord.ext import commands

from src.storage.changelog import (
    has_version_been_announced,
    mark_version_as_announced,
    get_changelog_for_version,
    create_changelog_embed
)
from src.version import get_version
from src.utils.config import get_env

logger = logging.getLogger('team_analysis_bot')


async def check_and_send_changelog(bot: commands.Bot):
    """
    Verifica se há um changelog para a versão atual que ainda não foi anunciado,
    e o envia para o canal de changelogs, se configurado.

    Args:
        bot: Instância do bot do Discord.
    """
    logger.debug("Iniciando verificação de changelog")

    current_version = get_version()
    logger.debug(f"Versão atual do bot: {current_version}")

    if has_version_been_announced(current_version):
        logger.info(f"Changelog para versão {current_version} já foi anunciado anteriormente")
        return

    logger.debug(f"Versão {current_version} ainda não foi anunciada")

    try:
        changelog_channel_id = get_env("CHANGELOG_CHANNEL_ID")
        logger.debug(f"CHANGELOG_CHANNEL_ID obtido: '{changelog_channel_id}'")
        if not changelog_channel_id:
            logger.debug(f"Nenhum canal de changelog configurado (CHANGELOG_CHANNEL_ID). Valor: '{changelog_channel_id}'")
            return
    except Exception as e:
        logger.error(f"Erro ao obter CHANGELOG_CHANNEL_ID: {str(e)}")
        return

    try:
        changelog_channel = await bot.fetch_channel(int(changelog_channel_id))

        changelog = get_changelog_for_version(current_version)
        if not changelog:
            logger.warning(f"Nenhum changelog encontrado para a versão {current_version}")
            return

        embed = create_changelog_embed(changelog)
        await changelog_channel.send(embed=embed)

        mark_version_as_announced(current_version)
        logger.info(f"Changelog para versão {current_version} anunciado com sucesso no canal #{changelog_channel.name}")

    except discord.NotFound:
        logger.error(f"Canal de changelog não encontrado (ID: {changelog_channel_id})")
    except discord.Forbidden:
        logger.error(f"Sem permissão para enviar mensagens no canal de changelog (ID: {changelog_channel_id})")
    except Exception as e:
        logger.error(f"Erro ao anunciar changelog: {str(e)}")