# devtrackr.discordbot

Um bot do Discord para análise e gerenciamento de times de desenvolvimento com foco em atualizações de status assíncronos e controle de ponto.

## Funcionalidades

- Sistema de ponto (toggle-ável)
- Registro de membros do time
- Stand-ups diários assíncronos
- Relatórios de atividade
- Lembretes automáticos para atualizações diárias pendentes
- Todas as datas e horários no fuso horário de Brasília (GMT-3)
- Sistema de suporte para reporte de erros e sugestões

## Estrutura do Projeto

```
/src/
  /bot/       - Código relacionado ao bot do Discord
  /storage/   - Código para armazenamento e persistência
  /utils/     - Código de utilitarios.
```

## Configuração

1. Clone este repositório
2. Instale as dependências com `pip install -r requirements.txt`
3. Renomeie o arquivo `.env.example` para `.env` e configure:
   - `DISCORD_TOKEN` - Seu token do bot Discord
   - `ADMIN_ROLE_ID` - ID do cargo de administrador (opcional, padrão usa permissões de administrador do servidor)
   - `DAILY_CHANNEL_ID` - ID do canal para atualizações diárias (opcional)
   - `DAILY_REMINDER_TIME` - Horário para lembretes diários no formato HH:MM (opcional, padrão: 10:00)
   - `SUPPORT_USER_ID` - ID do usuário que receberá mensagens de suporte (opcional)
4. Execute o bot com `python main.py`

## Usando Docker

Você pode executar este bot usando Docker com a imagem publicada no Docker Hub:

```bash
docker run -d \
  -e DISCORD_TOKEN=seu_token \
  -e ADMIN_ROLE_ID=id_do_cargo \
  -e DAILY_CHANNEL_ID=id_do_canal \
  -e DAILY_REMINDER_TIME=10:00 \
  -e SUPPORT_USER_ID=id_do_usuario \
  -v /caminho/para/seu/banco:/app/data \
  pdrh/devtracker:latest
```

### Versões Disponíveis

A imagem está disponível no Docker Hub em [pdrh/devtracker](https://hub.docker.com/r/pdrh/devtracker) com as seguintes tags:

- `latest` - Versão mais recente do bot
- Tags de versão específicas (ex: `0.0.2`, `0.0.3`) - Versões estáveis específicas

### Construindo sua própria imagem Docker

Para construir sua própria imagem Docker:

```bash
docker build -t seu-usuário/devtracker:tag .
```

## Comandos Principais

- `/toggle funcionalidade=ponto` - Ativa/desativa o sistema de ponto (apenas admin)
- `/on` - Registra entrada (quando o sistema de ponto está ativo)
- `/off` - Registra saída (quando o sistema de ponto está ativo)
- `/horas` - Visualiza suas horas registradas
- `/folha-de-ponto` - Visualiza as horas de todos os usuários (apenas admin)
- `/registrar tipo=[teammember|po] usuario=@username` - Registra um usuário no sistema (apenas admin)
- `/remover usuario=@username` - Remove um usuário do sistema (apenas admin)
- `/listar-usuarios tipo=[teammember|po|all]` - Lista os usuários registrados (apenas admin)
- `/daily [data=YYYY-MM-DD]` - Envia atualização diária (data opcional, padrão: dia anterior)
- `/ver-daily periodo=[semana|mes]` - Visualiza suas atualizações diárias
- `/relatorio-daily data_inicial=YYYY-MM-DD data_final=YYYY-MM-DD` - Gera relatório de atualizações diárias (admin/PO)
- `/relatorio` - Gerar relatório de atividades
- `/limpar-resumos` - Limpa todos os resumos diários do banco de dados (apenas admin, somente para testes)
- `/suporte` - Abre um modal para enviar mensagens de erro, sugestões ou problemas ao administrador do bot

## Sistema de Lembretes

O bot enviará automaticamente lembretes para usuários que não enviaram suas atualizações diárias:

1. Lembretes individuais via mensagem direta para cada usuário com atualizações pendentes
2. Um anúncio público no canal designado (ou canal padrão do servidor) listando todos os usuários com atualizações pendentes
3. Se configurado, o bot verificará que as atualizações sejam enviadas no canal correto

## Fuso Horário

Este bot opera no fuso horário de Brasília (GMT-3) para todas as suas funcionalidades:

- Registros de ponto
- Datas de atualizações diárias
- Horários dos lembretes
- Relatórios e visualizações de dados

Isso garante que todas as operações de data e hora estejam alinhadas com o horário brasileiro, independente de onde o bot esteja hospedado.
