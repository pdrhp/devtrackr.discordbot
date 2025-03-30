"""
Módulo para envio de changelogs no Discord.
"""
import logging
import os
from typing import Optional, List

import discord
from discord.ext import commands

from src.storage.changelog import (
    has_version_been_announced,
    mark_version_as_announced,
    get_changelog_for_version,
    create_changelog_embed
)
from src.version import get_version, get_all_versions
from src.utils.config import get_env

logger = logging.getLogger('team_analysis_bot')


async def send_changelog_for_version(bot: commands.Bot, version: str, channel):
    """
    Envia o changelog de uma versão específica para o canal.

    Args:
        bot: Instância do bot do Discord.
        version: Versão para enviar o changelog.
        channel: Canal do Discord para enviar o changelog.

    Returns:
        bool: True se o changelog foi enviado com sucesso, False caso contrário.
    """
    try:
        changelog = get_changelog_for_version(version)
        if not changelog:
            logger.warning(f"Nenhum changelog encontrado para a versão {version}")
            return False

        embed = create_changelog_embed(changelog)
        await channel.send(embed=embed)

        mark_version_as_announced(version)
        logger.info(f"Changelog para versão {version} anunciado com sucesso no canal #{channel.name}")
        return True

    except Exception as e:
        logger.error(f"Erro ao anunciar changelog para versão {version}: {str(e)}")
        return False


async def check_and_send_changelog(bot: commands.Bot):
    """
    Verifica se há changelogs que ainda não foram anunciados para a versão atual
    e versões anteriores, e os envia para o canal de changelogs, se configurado.

    Args:
        bot: Instância do bot do Discord.
    """
    logger.debug("Iniciando verificação de changelog")

    current_version = get_version()
    logger.debug(f"Versão atual do bot: {current_version}")

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

        all_versions = get_all_versions()
        logger.debug(f"Todas as versões disponíveis: {all_versions}")

        if not all_versions:
            logger.warning("Nenhuma versão encontrada para anunciar")
            return

        versions_announced = 0
        for version in all_versions:
            if has_version_been_announced(version):
                logger.debug(f"Changelog para versão {version} já foi anunciado anteriormente")
                continue

            logger.debug(f"Enviando changelog para versão não anunciada: {version}")

            success = await send_changelog_for_version(bot, version, changelog_channel)

            if success:
                versions_announced += 1

        if versions_announced > 0:
            logger.info(f"Total de {versions_announced} changelog(s) anunciado(s)")
        else:
            logger.info("Nenhum novo changelog para anunciar")

    except discord.NotFound:
        logger.error(f"Canal de changelog não encontrado (ID: {changelog_channel_id})")
    except discord.Forbidden:
        logger.error(f"Sem permissão para enviar mensagens no canal de changelog (ID: {changelog_channel_id})")
    except Exception as e:
        logger.error(f"Erro ao anunciar changelog: {str(e)}")