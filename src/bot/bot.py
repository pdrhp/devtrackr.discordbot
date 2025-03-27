import os
import logging
import datetime
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def setup_logging():
    """Configura o sistema de logging com saída para console e arquivo."""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    today = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'team_analysis_bot_{today}.log')

    logger = logging.getLogger('team_analysis_bot')
    logger.setLevel(logging.INFO)

    if logger.handlers:
        logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)

    cmd_log_file = os.path.join(log_dir, f'commands_{today}.log')
    cmd_handler = RotatingFileHandler(
        cmd_log_file,
        maxBytes=10*1024*1024,
        backupCount=5
    )
    cmd_handler.setFormatter(logging.Formatter('%(message)s'))

    cmd_logger = logging.getLogger('team_analysis_commands')
    cmd_logger.setLevel(logging.INFO)
    if cmd_logger.handlers:
        cmd_logger.handlers.clear()
    cmd_logger.addHandler(cmd_handler)

    return logger

logger = setup_logging()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class TeamAnalysisBot(commands.Bot):
    """Classe principal do Bot para Team Analysis Discord Bot."""

    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        """Configura o bot antes de iniciar."""
        logger.info("Configurando extensões do bot...")

        from src.bot import commands
        await commands.setup(self)

        from src.bot import tasks
        await tasks.setup(self)

        logger.info("Configuração do bot concluída!")

    async def on_ready(self):
        """Manipulador de evento quando o bot está conectado e pronto."""
        logger.info(f'Conectado como {self.user} (ID: {self.user.id})')
        logger.info('------')

        try:
            synced = await self.tree.sync()
            logger.info(f"Comandos sincronizados: {len(synced)} comandos")
            for command in synced:
                logger.info(f"- Comando sincronizado: /{command.name}")
        except Exception as e:
            logger.error(f"Erro ao sincronizar comandos: {e}")


def run_bot():
    """Executa o bot do Discord."""
    token = os.getenv('DISCORD_TOKEN')

    if not token:
        logger.error("Token do Discord não encontrado. Configure a variável de ambiente DISCORD_TOKEN.")
        return

    bot = TeamAnalysisBot()
    bot.run(token, log_handler=None)
