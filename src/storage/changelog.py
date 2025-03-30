"""
Módulo para gerenciar changelogs e controle de anúncios de versões.
"""
import os
import yaml
import logging
import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime

import discord

from src.storage.database import get_connection
from src.version import get_version
from src.utils.config import now_br

logger = logging.getLogger('team_analysis_bot')

CHANGELOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'changelogs')
os.makedirs(CHANGELOGS_DIR, exist_ok=True)


def has_version_been_announced(version: str) -> bool:
    """
    Verifica se uma versão já foi anunciada.

    Args:
        version: Versão a verificar.

    Returns:
        bool: True se a versão já foi anunciada, False caso contrário.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT version FROM changelog_announcements WHERE version = ?",
        (version,)
    )

    result = cursor.fetchone()
    conn.close()

    return result is not None


def mark_version_as_announced(version: str):
    """
    Marca uma versão como já tendo sido anunciada.

    Args:
        version: Versão a marcar como anunciada.
    """
    conn = get_connection()
    cursor = conn.cursor()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO changelog_announcements (version, announced_at) VALUES (?, ?)",
        (version, current_time)
    )

    conn.commit()
    conn.close()
    logger.info(f"Versão {version} marcada como anunciada em {current_time}")


def get_changelog_for_version(version: str) -> Optional[Dict[str, Any]]:
    """
    Obtém o changelog para uma versão específica.

    Args:
        version: Versão para obter o changelog.

    Returns:
        Dict ou None: Dados do changelog ou None se não encontrado.
    """
    try:
        changelog_file = os.path.join(CHANGELOGS_DIR, f"{version}.yaml")

        if not os.path.exists(changelog_file):
            logger.warning(f"Arquivo de changelog para versão {version} não encontrado: {changelog_file}")
            return None

        with open(changelog_file, "r", encoding="utf-8") as f:
            changelog_data = yaml.safe_load(f)
            return changelog_data
    except Exception as e:
        logger.error(f"Erro ao carregar changelog para versão {version}: {str(e)}")
        return None


def create_changelog_embed(changelog: Dict[str, Any]) -> discord.Embed:
    """
    Cria um embed do Discord com as informações do changelog.

    Args:
        changelog: Dados do changelog.

    Returns:
        discord.Embed: Embed formatado para o Discord.
    """
    embed = discord.Embed(
        title=f"🚀 {changelog['title']}",
        description=changelog.get('description', "O bot foi atualizado com as seguintes alterações:"),
        color=discord.Color.blue()
    )

    type_icons = {
        "adicionado": "✨",
        "melhorado": "⚡",
        "corrigido": "🐛",
        "alterado": "🔄",
        "removido": "🗑️",
        "seguranca": "🔒",
        "desenvolvimento": "⚙️"
    }

    type_titles = {
        "adicionado": "Adicionado",
        "melhorado": "Melhorado",
        "corrigido": "Corrigido",
        "alterado": "Alterado",
        "removido": "Removido",
        "seguranca": "Segurança",
        "desenvolvimento": "Desenvolvimento"
    }

    if "changes" in changelog:
        changes = changelog["changes"]
        for change_type, descriptions in changes.items():
            if descriptions:
                icon = type_icons.get(change_type, "•")
                title = type_titles.get(change_type, change_type.title())

                value = "\n".join([f"• {desc}" for desc in descriptions])

                embed.add_field(
                    name=f"{icon} {title}",
                    value=value,
                    inline=False
                )

    if "notes" in changelog and changelog["notes"]:
        embed.add_field(
            name="📝 Notas",
            value=changelog["notes"],
            inline=False
        )

    if "contributors" in changelog and changelog["contributors"]:
        contributors = ", ".join(changelog["contributors"])
        embed.add_field(
            name="👥 Contribuidores",
            value=contributors,
            inline=False
        )

    embed.set_footer(text=f"Versão {changelog['version']} | Lançada em: {changelog['release_date']}")

    return embed