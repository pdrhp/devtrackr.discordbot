"""
Informações de versão para o Team Analysis Bot.
"""
import os
import yaml
import re
import logging

__default_version__ = "0.0.0"

CHANGELOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'changelogs')

logger = logging.getLogger('team_analysis_bot')

def get_version():
    """
    Retorna a versão atual do bot.

    A versão é determinada dinamicamente examinando o arquivo de changelog mais recente.
    Se não for possível determinar a versão a partir dos changelogs, retorna a versão padrão.
    """
    try:
        if not os.path.exists(CHANGELOGS_DIR):
            logger.warning(f"Diretório de changelogs não encontrado: {CHANGELOGS_DIR}")
            return __default_version__

        changelog_files = [f for f in os.listdir(CHANGELOGS_DIR)
                           if f.endswith('.yaml') and f != 'modelo.yaml' and re.match(r'^\d+\.\d+\.\d+$', f.split('.yaml')[0])]

        logger.debug(f"Arquivos de changelog encontrados: {changelog_files}")

        if not changelog_files:
            logger.warning("Nenhum arquivo de changelog encontrado")
            return __default_version__

        changelog_files.sort(key=lambda x: [int(p) for p in x.split('.yaml')[0].split('.')], reverse=True)

        latest_changelog = changelog_files[0]

        version = latest_changelog.split('.yaml')[0]

        if not re.match(r'^\d+\.\d+\.\d+$', version):
            logger.warning(f"Formato de versão inválido: {version}")
            return __default_version__

        changelog_path = os.path.join(CHANGELOGS_DIR, latest_changelog)
        with open(changelog_path, 'r', encoding='utf-8') as f:
            changelog_data = yaml.safe_load(f)

            if 'version' in changelog_data and changelog_data['version'] == version:
                logger.debug(f"Versão determinada a partir do arquivo de changelog: {version}")
                return version
            else:
                logger.warning(f"Inconsistência na versão do changelog: {version} vs {changelog_data.get('version', 'não definida')}")
                return __default_version__

    except Exception as e:
        logger.error(f"Erro ao determinar a versão: {str(e)}")
        return __default_version__

def get_all_versions():
    """
    Retorna todas as versões disponíveis ordenadas semanticamente (mais antiga para mais recente).

    Returns:
        list: Lista de strings com as versões disponíveis.
    """
    try:
        if not os.path.exists(CHANGELOGS_DIR):
            logger.warning(f"Diretório de changelogs não encontrado: {CHANGELOGS_DIR}")
            return []

        changelog_files = [f for f in os.listdir(CHANGELOGS_DIR)
                          if f.endswith('.yaml') and f != 'modelo.yaml' and re.match(r'^\d+\.\d+\.\d+$', f.split('.yaml')[0])]

        logger.debug(f"Arquivos de changelog encontrados: {changelog_files}")

        if not changelog_files:
            logger.warning("Nenhum arquivo de changelog encontrado")
            return []

        changelog_files.sort(key=lambda x: [int(p) for p in x.split('.yaml')[0].split('.')])

        versions = [f.split('.yaml')[0] for f in changelog_files]

        return versions

    except Exception as e:
        logger.error(f"Erro ao listar versões disponíveis: {str(e)}")
        return []