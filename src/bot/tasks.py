import asyncio
from datetime import datetime, time, timedelta
import logging
from typing import List, Optional, Dict

import discord
from discord.ext import tasks, commands
from discord import app_commands

from src.storage.daily import get_missing_updates
from src.utils.config import get_env, get_br_time, to_br_timezone, BRAZIL_TIMEZONE, log_command
from src.storage.users import check_user_is_po
from src.storage.feature_toggle import is_feature_enabled
from src.storage.ignored_dates import should_ignore_date, get_all_ignored_dates

logger = logging.getLogger('team_analysis_bot')


class ScheduledTasks(commands.Cog):
    """Cog para tarefas agendadas do bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_reminder.start()

    async def log_configured_channels(self):
        """Loga informações sobre os canais configurados na inicialização do bot."""
        logger.info("==== Verificando canais configurados ====")

        daily_channel_id = get_env("DAILY_CHANNEL_ID")
        if daily_channel_id:
            try:
                daily_channel = await self.bot.fetch_channel(int(daily_channel_id))
                logger.info(f"Canal para atualizações diárias configurado: #{daily_channel.name} (ID: {daily_channel.id}) no servidor {daily_channel.guild.name}")
            except (discord.NotFound, discord.Forbidden, ValueError) as e:
                logger.error(f"Erro ao obter canal para atualizações diárias: {str(e)}")
                logger.info(f"DAILY_CHANNEL_ID configurado com valor inválido ou inacessível: {daily_channel_id}")
        else:
            logger.warning("DAILY_CHANNEL_ID não está configurado. O bot usará um canal alternativo para os lembretes.")

        time_tracking_channel_id = get_env("TIME_TRACKING_CHANNEL_ID")
        if time_tracking_channel_id:
            try:
                time_channel = await self.bot.fetch_channel(int(time_tracking_channel_id))
                logger.info(f"Canal para time tracking configurado: #{time_channel.name} (ID: {time_channel.id}) no servidor {time_channel.guild.name}")
            except (discord.NotFound, discord.Forbidden, ValueError) as e:
                logger.error(f"Erro ao obter canal para time tracking: {str(e)}")
                logger.info(f"TIME_TRACKING_CHANNEL_ID configurado com valor inválido ou inacessível: {time_tracking_channel_id}")
        else:
            logger.warning("TIME_TRACKING_CHANNEL_ID não está configurado.")

        logger.info("==== Verificação de canais concluída ====")

    def cog_unload(self):
        """Chamado quando o cog é descarregado."""
        self.daily_reminder.cancel()

    async def _check_daily_collection_enabled(self, interaction: Optional[discord.Interaction] = None) -> bool:
        """
        Verifica se as funcionalidades de daily e cobrança estão ativadas.

        Args:
            interaction: Interação opcional do Discord para enviar mensagem de erro.
        """
        if not is_feature_enabled("daily"):
            if interaction:
                await interaction.response.send_message(
                    "⚠️ A funcionalidade de atualizações diárias está desativada. "
                    "Você pode ativá-la com o comando `/toggle funcionalidade=daily`.",
                    ephemeral=True
                )
                log_command("INFO", interaction.user, interaction.command.name, "Funcionalidade de daily desativada")
            return False

        if not is_feature_enabled("daily_collection"):
            if interaction:
                await interaction.response.send_message(
                    "⚠️ A funcionalidade de cobrança de daily está desativada. "
                    "Você pode ativá-la com o comando `/toggle funcionalidade=daily_collection`.",
                    ephemeral=True
                )
                log_command("INFO", interaction.user, interaction.command.name, "Funcionalidade de cobrança de daily desativada")
            return False

        return True

    @tasks.loop(time=time(13, 0))
    async def daily_reminder(self):
        """Envia lembretes para usuários que não enviaram atualizações diárias."""
        logger.info("Executando tarefa de lembretes de atualizações diárias")

        try:
            if not await self._check_daily_collection_enabled():
                logger.info("Funcionalidade de cobrança de daily está desativada, pulando lembretes")
                return

            br_time = get_br_time()

            if br_time.weekday() >= 5:
                logger.info("Hoje é fim de semana, pulando lembretes de atualizações diárias")
                return

            if should_ignore_date(br_time):
                logger.info(f"Data {br_time.strftime('%Y-%m-%d')} está na lista de datas ignoradas, pulando lembretes")
                return

            yesterday = br_time - timedelta(days=1)
            if should_ignore_date(yesterday):
                logger.info(f"Data {yesterday.strftime('%Y-%m-%d')} está na lista de datas ignoradas, pulando lembretes")
                return

            missing_users = get_missing_updates()

            if not missing_users:
                logger.info("Todos os usuários enviaram suas atualizações diárias.")
                return

            logger.info(f"Enviando lembretes para {len(missing_users)} usuários")

            daily_channel_id = get_env("DAILY_CHANNEL_ID")
            daily_channel = None

            if daily_channel_id:
                try:
                    daily_channel = await self.bot.fetch_channel(int(daily_channel_id))
                    logger.info(f"Canal para atualizações diárias encontrado: {daily_channel.name}")
                except (discord.NotFound, discord.Forbidden, ValueError) as e:
                    logger.error(f"Erro ao obter canal para atualizações diárias: {str(e)}")

            if not daily_channel:
                logger.info("Canal específico para atualizações diárias não configurado ou não encontrado")

            pending_by_date: Dict[str, List[discord.User]] = {}
            processed_users = []

            for user_id in missing_users:
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    processed_users.append(user)

                    embed = discord.Embed(
                        title="🔔 Lembrete: Atualização Diária Pendente",
                        description="Você ainda não enviou sua atualização diária de ontem. Por favor, use o comando `/daily` para informar o que você fez.",
                        color=discord.Color.yellow()
                    )

                    yesterday = get_br_time() - timedelta(days=1)
                    yesterday_str = yesterday.strftime("%d/%m/%Y")
                    yesterday_db = yesterday.strftime("%Y-%m-%d")

                    if daily_channel:
                        embed.add_field(
                            name="Onde enviar?",
                            value=f"Use o comando `/daily` no canal {daily_channel.mention} e descreva o que você fez ontem.",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="Como enviar?",
                            value="Use o comando `/daily` no servidor e descreva o que você fez ontem.",
                            inline=False
                        )

                    embed.set_footer(text=f"Atualização pendente para: {yesterday_str}")

                    await user.send(embed=embed)

                    if yesterday_db not in pending_by_date:
                        pending_by_date[yesterday_db] = []
                    pending_by_date[yesterday_db].append(user)

                    logger.info(f"Lembrete enviado para o usuário {user_id}")
                    await asyncio.sleep(1)

                except discord.HTTPException as e:
                    logger.error(f"Erro ao enviar lembrete para o usuário {user_id}: {str(e)}")
                except Exception as e:
                    logger.error(f"Erro inesperado ao processar lembrete para o usuário {user_id}: {str(e)}")

            if processed_users and (daily_channel or self.bot.guilds):
                await self._send_public_reminder(daily_channel, pending_by_date)

        except Exception as e:
            logger.error(f"Erro ao executar tarefa de lembretes: {str(e)}")

    async def _send_public_reminder(self, daily_channel: Optional[discord.TextChannel], pending_by_date: Dict[str, List[discord.User]]):
        """Envia um lembrete público no canal designado listando todos os usuários pendentes."""
        try:
            channel = daily_channel

            if daily_channel:
                logger.info(f"Canal configurado para daily updates: #{daily_channel.name} (ID: {daily_channel.id}) no servidor {daily_channel.guild.name}")
            else:
                logger.info("Nenhum canal específico configurado para daily updates, buscando canal alternativo...")

            if not channel:
                for guild in self.bot.guilds:
                    logger.info(f"Procurando canal apropriado no servidor: {guild.name} (ID: {guild.id})")

                    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                        channel = guild.system_channel
                        logger.info(f"Usando canal do sistema: #{channel.name} (ID: {channel.id})")
                        break
                    else:
                        logger.info("Canal do sistema não disponível, procurando primeiro canal de texto com permissões...")
                        for text_channel in guild.text_channels:
                            if text_channel.permissions_for(guild.me).send_messages:
                                channel = text_channel
                                logger.info(f"Usando canal de texto: #{channel.name} (ID: {channel.id})")
                                break
                        if channel:
                            break

            if not channel:
                logger.error("Não foi possível encontrar um canal para enviar o lembrete público")
                return

            logger.info(f"Canal final escolhido para envio do lembrete: #{channel.name} (ID: {channel.id}) no servidor {channel.guild.name}")

            embed = discord.Embed(
                title="📢 Lembretes de Atualizações Diárias Pendentes",
                description="Os seguintes membros da equipe estão com atualizações diárias pendentes:",
                color=discord.Color.gold()
            )

            for date_str, users in pending_by_date.items():
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                date_obj = date_obj.replace(tzinfo=BRAZIL_TIMEZONE)
                formatted_date = date_obj.strftime("%d/%m/%Y")

                user_list = "\n".join([f"• {user.mention}" for user in users])

                embed.add_field(
                    name=f"📅 Dia {formatted_date}",
                    value=user_list if user_list else "Nenhum usuário pendente.",
                    inline=False
                )

            daily_channel_mention = f"este canal ({channel.mention})" if channel == daily_channel else channel.mention
            if daily_channel:
                embed.add_field(
                    name="⚠️ Atenção",
                    value=f"Por favor, envie suas atualizações usando o comando `/daily` no canal {daily_channel.mention}.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="⚠️ Atenção",
                    value=f"Por favor, envie suas atualizações usando o comando `/daily` em {daily_channel_mention}.",
                    inline=False
                )

            current_time_br = get_br_time().strftime("%d/%m/%Y %H:%M:%S")
            embed.set_footer(text=f"Horário de Brasília: {current_time_br}")

            await channel.send(embed=embed)
            logger.info(f"Anúncio público de lembretes enviado no canal {channel.name}")

        except Exception as e:
            logger.error(f"Erro ao enviar anúncio público: {str(e)}")

    @app_commands.command(name="cobrar_daily", description="Cobra as atualizações diárias pendentes. (Somente POs e Admins)")
    async def cobrar_daily(self, interaction: discord.Interaction):
        """Comando para POs e admins cobrarem atualizações diárias pendentes."""
        if not await self._check_daily_collection_enabled(interaction):
            return

        br_time = get_br_time()
        if should_ignore_date(br_time):
            await interaction.response.send_message(
                f"⚠️ A data atual ({br_time.strftime('%d/%m/%Y')}) está configurada para ser ignorada na cobrança de daily.",
                ephemeral=True
            )
            log_command("INFO", interaction.user, "/cobrar_daily", f"Data {br_time.strftime('%Y-%m-%d')} ignorada")
            return

        yesterday = br_time - timedelta(days=1)
        if should_ignore_date(yesterday):
            await interaction.response.send_message(
                f"⚠️ A data de ontem ({yesterday.strftime('%d/%m/%Y')}) está configurada para ser ignorada na cobrança de daily.",
                ephemeral=True
            )
            log_command("INFO", interaction.user, "/cobrar_daily", f"Data {yesterday.strftime('%Y-%m-%d')} ignorada")
            return

        daily_channel_id = get_env("DAILY_CHANNEL_ID")

        if daily_channel_id and str(interaction.channel_id) != daily_channel_id:
            try:
                daily_channel = await self.bot.fetch_channel(int(daily_channel_id))
                await interaction.response.send_message(
                    f"Este comando só pode ser usado no canal {daily_channel.mention}.",
                    ephemeral=True
                )
            except (discord.NotFound, discord.Forbidden):
                await interaction.response.send_message(
                    "Este comando só pode ser usado no canal de atualizações diárias.",
                    ephemeral=True
                )
            return

        user_id = str(interaction.user.id)
        admin_role_id = get_env("ADMIN_ROLE_ID")
        has_permission = False

        if check_user_is_po(user_id):
            has_permission = True
            logger.info(f"Usuário {user_id} é PO e solicitou cobrança de atualizações diárias")

        elif admin_role_id and interaction.guild:
            member = interaction.guild.get_member(int(user_id))
            if member and any(role.id == int(admin_role_id) for role in member.roles):
                has_permission = True
                logger.info(f"Usuário {user_id} tem cargo de admin e solicitou cobrança de atualizações diárias")

        if not has_permission:
            await interaction.response.send_message(
                "Você não tem permissão para usar este comando. Somente POs e administradores podem usá-lo.",
                ephemeral=True
            )
            logger.warning(f"Usuário {user_id} tentou usar o comando de cobrança sem permissão")
            return

        await interaction.response.defer(thinking=True)

        missing_users = get_missing_updates()

        if not missing_users:
            await interaction.followup.send("Todos os usuários estão com suas atualizações diárias em dia! 🎉")
            return

        pending_by_date = await self._process_management_reminder(missing_users, interaction.user)

        embed = discord.Embed(
            title="📊 Relatório de Cobrança de Atualizações",
            description=f"A equipe de gerência de projetos ({interaction.user.mention}) solicitou uma cobrança das atualizações pendentes.",
            color=discord.Color.brand_red()
        )

        for date_str, users in pending_by_date.items():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            date_obj = date_obj.replace(tzinfo=BRAZIL_TIMEZONE)
            formatted_date = date_obj.strftime("%d/%m/%Y")

            user_list = "\n".join([f"• {user.mention}" for user in users])

            embed.add_field(
                name=f"📅 Dia {formatted_date}",
                value=user_list if user_list else "Nenhum usuário pendente.",
                inline=False
            )

        embed.set_footer(text=f"Cobrança solicitada em: {get_br_time().strftime('%d/%m/%Y %H:%M:%S')}")

        await interaction.followup.send(embed=embed)
        logger.info(f"Cobrança de atualizações diárias executada por {interaction.user.id}")

    async def _process_management_reminder(self, missing_users: List[str], requester: discord.User) -> Dict[str, List[discord.User]]:
        """Processa uma cobrança iniciada pela gerência, enviando mensagens privadas."""
        pending_by_date: Dict[str, List[discord.User]] = {}
        processed_users = []

        for user_id in missing_users:
            try:
                user = await self.bot.fetch_user(int(user_id))
                processed_users.append(user)

                embed = discord.Embed(
                    title="⚠️ Cobrança: Atualizações Diárias Pendentes",
                    description=f"A equipe de gerência de projetos ({requester.mention}) notou que você está com atualizações diárias pendentes.",
                    color=discord.Color.red()
                )

                yesterday = get_br_time() - timedelta(days=1)
                yesterday_db = yesterday.strftime("%Y-%m-%d")

                daily_channel_id = get_env("DAILY_CHANNEL_ID")
                daily_channel = None

                if daily_channel_id:
                    try:
                        daily_channel = await self.bot.fetch_channel(int(daily_channel_id))
                    except (discord.NotFound, discord.Forbidden):
                        pass

                if daily_channel:
                    embed.add_field(
                        name="⏰ Solicitação Urgente",
                        value=f"Por favor, use o comando `/daily` no canal {daily_channel.mention} para atualizar seu status o mais rápido possível.",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="⏰ Solicitação Urgente",
                        value="Por favor, use o comando `/daily` para atualizar seu status o mais rápido possível.",
                        inline=False
                    )

                embed.add_field(
                    name="📝 Lembrete",
                    value="Manter suas atualizações diárias em dia é essencial para o acompanhamento do projeto pela equipe de gerência.",
                    inline=False
                )

                embed.set_footer(text=f"Cobrança realizada em: {get_br_time().strftime('%d/%m/%Y %H:%M:%S')}")

                await user.send(embed=embed)

                if yesterday_db not in pending_by_date:
                    pending_by_date[yesterday_db] = []
                pending_by_date[yesterday_db].append(user)

                logger.info(f"Cobrança gerencial enviada para o usuário {user_id}")
                await asyncio.sleep(1)

            except discord.HTTPException as e:
                logger.error(f"Erro ao enviar cobrança para o usuário {user_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Erro inesperado ao processar cobrança para o usuário {user_id}: {str(e)}")

        return pending_by_date

    @daily_reminder.before_loop
    async def before_daily_reminder(self):
        """Aguarda o bot estar pronto antes de iniciar a tarefa e configura o horário."""
        await self.bot.wait_until_ready()

        await self.log_configured_channels()

        reminder_time_str = get_env("DAILY_REMINDER_TIME", "10:00")
        try:
            hour, minute = map(int, reminder_time_str.split(":"))

            utc_hour = (hour + 3) % 24
            reminder_time = time(utc_hour, minute)

            self.daily_reminder.change_interval(time=reminder_time)
            logger.info(f"Tarefa de lembretes configurada para executar diariamente às {reminder_time_str} (Horário de Brasília)")
            logger.info(f"Convertido para {utc_hour}:{minute:02d} UTC")
        except (ValueError, AttributeError) as e:
            default_time = time(13, 0)
            self.daily_reminder.change_interval(time=default_time)
            logger.error(f"Erro ao configurar horário do lembrete ({str(e)}). Usando o padrão: 10:00 (Horário de Brasília)")

        logger.info("Tarefa de lembretes de atualizações diárias inicializada")


async def setup(bot: commands.Bot):
    """Configura as tarefas agendadas."""
    cog = ScheduledTasks(bot)
    await bot.add_cog(cog)