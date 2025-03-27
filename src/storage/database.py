import os
import sqlite3
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                       "data", "teamanalysis.db")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection():
    """
    Obtém uma conexão com o banco de dados.

    Returns:
        sqlite3.Connection: Conexão com o banco de dados.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """
    Inicializa o banco de dados criando as tabelas necessárias se não existirem.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Criar tabela para registros de ponto
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS time_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        clock_in TIMESTAMP NOT NULL,
        clock_out TIMESTAMP,
        observation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Criar tabela para usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL UNIQUE,
        user_name TEXT NOT NULL,
        role TEXT NOT NULL,  -- 'teammember' ou 'po'
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        registered_by TEXT NOT NULL
    )
    ''')

    # Criar tabela para atualizações diárias (daily updates)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        report_date DATE NOT NULL,  -- Data a que se refere o relatório (YYYY-MM-DD)
        content TEXT NOT NULL,      -- Conteúdo do relatório diário
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, report_date)  -- Cada usuário só pode ter um relatório por data
    )
    ''')

    conn.commit()
    conn.close()


initialize_database()