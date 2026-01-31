# Database connection and operations using asyncpg for Neon PostgreSQL
# COMPLETE REWRITE WITH ALL NEW FEATURES INTEGRATED

import asyncpg
import os
from typing import Optional, List, Dict
from datetime import datetime, timedelta

# Database connection pool
pool: Optional[asyncpg.Pool] = None

async def init_database():
    """Initialize database connection pool and create tables"""
    global pool
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Create pool with statement caching disabled and connection recycling
    pool = await asyncpg.create_pool(
        database_url, 
        min_size=5, 
        max_size=20,
        statement_cache_size=0,
        max_inactive_connection_lifetime=300
    )
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # ==================== CORE TABLES ====================
            
            # Players table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    user_id VARCHAR(255) PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    balance BIGINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Companies table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id SERIAL PRIMARY KEY,
                    owner_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    rank VARCHAR(10) NOT NULL,
                    type VARCHAR(255) NOT NULL,
                    base_income BIGINT NOT NULL,
                    current_income BIGINT NOT NULL,
                    reputation INTEGER DEFAULT 50,
                    thread_id VARCHAR(255) UNIQUE,
                    embed_message_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_event_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_companies_owner ON companies(owner_id)')
            
            # Company assets/upgrades table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS company_assets (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    asset_name VARCHAR(255) NOT NULL,
                    asset_type VARCHAR(100) NOT NULL,
                    income_boost BIGINT NOT NULL,
                    cost BIGINT NOT NULL,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Loans table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS loans (
                    id SERIAL PRIMARY KEY,
                    borrower_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
                    principal_amount BIGINT NOT NULL,
                    interest_rate DECIMAL(5,2) NOT NULL,
                    total_owed BIGINT NOT NULL,
                    loan_tier VARCHAR(10) NOT NULL,
                    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    due_date TIMESTAMP NOT NULL,
                    is_paid BOOLEAN DEFAULT FALSE,
                    thread_id VARCHAR(255),
                    embed_message_id VARCHAR(255)
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_loans_borrower ON loans(borrower_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_loans_paid ON loans(is_paid)')
            
            # Events log table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS company_events (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    event_type VARCHAR(50) NOT NULL,
                    event_description TEXT NOT NULL,
                    income_change BIGINT NOT NULL,
                    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Guild settings table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id VARCHAR(255) PRIMARY KEY,
                    company_forum_id VARCHAR(255),
                    bank_forum_id VARCHAR(255),
                    leaderboard_channel_id VARCHAR(255),
                    leaderboard_message_id VARCHAR(255),
                    event_frequency_hours INTEGER DEFAULT 6,
                    admin_role_ids TEXT[],
                    create_company_post_id VARCHAR(255),
                    request_loan_post_id VARCHAR(255),
                    tax_rate DECIMAL(5,2) DEFAULT 0.0,
                    tax_notification_channel_id VARCHAR(255),
                    stock_market_channel_id VARCHAR(255),
                    stock_market_message_id VARCHAR(255),
                    stock_update_interval_minutes INTEGER DEFAULT 3,
                    corporation_member_limit INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ==================== TAX SYSTEM ====================
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tax_collections (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    amount BIGINT NOT NULL,
                    guild_id VARCHAR(255) NOT NULL,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_tax_collections_guild ON tax_collections(guild_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_tax_collections_time ON tax_collections(collected_at)')
            
            # ==================== COLLECTIBLES ====================
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS player_collectibles (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    collectible_id VARCHAR(255) NOT NULL,
                    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, collectible_id)
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_player_collectibles_user ON player_collectibles(user_id)')
            
            # ==================== STOCK MARKET ====================
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS stock_prices (
                    symbol VARCHAR(10) PRIMARY KEY,
                    price BIGINT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS stock_price_history (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    old_price BIGINT NOT NULL,
                    new_price BIGINT NOT NULL,
                    change_percent DECIMAL(10,2) NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_stock_history_symbol ON stock_price_history(symbol)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_stock_history_time ON stock_price_history(changed_at)')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS player_stocks (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    symbol VARCHAR(10) NOT NULL,
                    shares INTEGER NOT NULL,
                    average_price BIGINT NOT NULL,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, symbol)
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_player_stocks_user ON player_stocks(user_id)')
            
            # ==================== COMPANY WARS/RAIDS ====================
            
            # Check and fix company_raids table schema
            table_exists = await conn.fetchval('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'company_raids'
                )
            ''')
            
            if table_exists:
                column_exists = await conn.fetchval('''
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'company_raids' 
                        AND column_name = 'attacker_id'
                    )
                ''')
                
                if not column_exists:
                    print("Recreating company_raids table due to schema mismatch...")
                    await conn.execute('DROP TABLE IF EXISTS company_raids CASCADE')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS company_raids (
                    id SERIAL PRIMARY KEY,
                    attacker_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    defender_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    success BOOLEAN NOT NULL,
                    loot BIGINT DEFAULT 0,
                    reputation_loss INTEGER DEFAULT 0,
                    raided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_raids_attacker ON company_raids(attacker_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_raids_defender ON company_raids(defender_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_raids_time ON company_raids(raided_at)')
            
            # Check and fix company_wars table schema
            table_exists = await conn.fetchval('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'company_wars'
                )
            ''')
            
            if table_exists:
                column_exists = await conn.fetchval('''
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'company_wars' 
                        AND column_name = 'attacker_id'
                    )
                ''')
                
                if not column_exists:
                    print("Recreating company_wars table due to schema mismatch...")
                    await conn.execute('DROP TABLE IF EXISTS company_wars CASCADE')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS company_wars (
                    id SERIAL PRIMARY KEY,
                    attacker_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    defender_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    attacker_damage BIGINT DEFAULT 0,
                    defender_damage BIGINT DEFAULT 0,
                    starts_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ends_at TIMESTAMP NOT NULL,
                    active BOOLEAN DEFAULT TRUE,
                    winner_id INTEGER
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_wars_attacker ON company_wars(attacker_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_wars_defender ON company_wars(defender_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_wars_active ON company_wars(active)')
            
            # ==================== CORPORATIONS ====================
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS corporations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    tag VARCHAR(5) NOT NULL,
                    leader_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    guild_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name),
                    UNIQUE(tag)
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_corporations_leader ON corporations(leader_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_corporations_guild ON corporations(guild_id)')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS corporation_members (
                    id SERIAL PRIMARY KEY,
                    corporation_id INTEGER NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id)
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_corp_members_corp ON corporation_members(corporation_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_corp_members_user ON corporation_members(user_id)')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS corporation_invites (
                    id SERIAL PRIMARY KEY,
                    corporation_id INTEGER NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    accepted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(corporation_id, user_id)
                )
            ''')
            
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_corp_invites_user ON corporation_invites(user_id)')
    
    print('✅ Database initialized successfully with all features')

async def close_database():
    """Close database connection pool"""
    global pool
    if pool:
        await pool.close()


# ==================== PLAYER OPERATIONS ====================

async def get_player(user_id: str) -> Optional[Dict]:
    """Get a player by user ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM players WHERE user_id = $1', user_id)
        return dict(row) if row else None

async def upsert_player(user_id: str, username: str) -> Dict:
    """Create or update a player"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO players (user_id, username, balance)
            VALUES ($1, $2, 0)
            ON CONFLICT (user_id)
            DO UPDATE SET username = $2, updated_at = CURRENT_TIMESTAMP
            RETURNING *
        ''', user_id, username)
        return dict(row)

async def update_player_balance(user_id: str, amount: int) -> Dict:
    """Update player balance (positive or negative amount)"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE players
            SET balance = GREATEST(0, balance + $2), updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1
            RETURNING *
        ''', user_id, amount)
        return dict(row) if row else None

async def get_all_players_with_balance() -> List[Dict]:
    """Get all players with positive balance"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM players WHERE balance > 0')
        return [dict(row) for row in rows]

async def get_top_players(limit: int = 25, offset: int = 0) -> List[Dict]:
    """Get top players by balance"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT user_id, username, balance,
                   ROW_NUMBER() OVER (ORDER BY balance DESC) as rank
            FROM players
            WHERE balance > 0
            ORDER BY balance DESC
            LIMIT $1 OFFSET $2
        ''', limit, offset)
        return [dict(row) for row in rows]

async def get_total_player_count() -> int:
    """Get total number of players with balance"""
    async with pool.acquire() as conn:
        count = await conn.fetchval('SELECT COUNT(*) FROM players WHERE balance > 0')
        return count or 0


# ==================== COMPANY OPERATIONS ====================

async def create_company(owner_id: str, name: str, rank: str, company_type: str, base_income: int, thread_id: str) -> Dict:
    """Create a new company"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO companies (owner_id, name, rank, type, base_income, current_income, thread_id)
            VALUES ($1, $2, $3, $4, $5, $5, $6)
            RETURNING *
        ''', owner_id, name, rank, company_type, base_income, thread_id)
        return dict(row)

async def get_company_by_id(company_id: int) -> Optional[Dict]:
    """Get company by ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM companies WHERE id = $1', company_id)
        return dict(row) if row else None

async def get_company_by_owner(owner_id: str) -> Optional[Dict]:
    """Get company owned by user"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM companies WHERE owner_id = $1', owner_id)
        return dict(row) if row else None

async def get_company_by_thread(thread_id: str) -> Optional[Dict]:
    """Get company by thread ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM companies WHERE thread_id = $1', thread_id)
        return dict(row) if row else None

async def get_all_companies() -> List[Dict]:
    """Get all companies"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM companies ORDER BY current_income DESC')
        return [dict(row) for row in rows]

async def update_company_income(company_id: int, change: int) -> Dict:
    """Update company income (can be positive or negative)"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE companies
            SET current_income = GREATEST(1, current_income + $2),
                last_event_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING *
        ''', company_id, change)
        return dict(row) if row else None

async def update_company_reputation(company_id: int, change: int):
    """Update company reputation"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE companies
            SET reputation = GREATEST(0, LEAST(100, reputation + $2))
            WHERE id = $1
        ''', company_id, change)

async def set_company_embed_message(company_id: int, message_id: str):
    """Set the embed message ID for a company"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE companies SET embed_message_id = $2 WHERE id = $1
        ''', company_id, message_id)

async def delete_company(company_id: int):
    """Delete a company"""
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM companies WHERE id = $1', company_id)


# ==================== COMPANY ASSETS ====================

async def add_company_asset(company_id: int, asset_name: str, asset_type: str, income_boost: int, cost: int):
    """Add an asset to a company"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO company_assets (company_id, asset_name, asset_type, income_boost, cost)
            VALUES ($1, $2, $3, $4, $5)
        ''', company_id, asset_name, asset_type, income_boost, cost)

async def get_company_assets(company_id: int) -> List[Dict]:
    """Get all assets for a company"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM company_assets WHERE company_id = $1 ORDER BY purchased_at DESC
        ''', company_id)
        return [dict(row) for row in rows]


# ==================== COMPANY EVENTS ====================

async def log_company_event(company_id: int, event_type: str, description: str, income_change: int):
    """Log a company event"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO company_events (company_id, event_type, event_description, income_change)
            VALUES ($1, $2, $3, $4)
        ''', company_id, event_type, description, income_change)

async def get_company_events(company_id: int, limit: int = 10) -> List[Dict]:
    """Get recent events for a company"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM company_events
            WHERE company_id = $1
            ORDER BY occurred_at DESC
            LIMIT $2
        ''', company_id, limit)
        return [dict(row) for row in rows]


# ==================== LOAN OPERATIONS ====================

async def create_loan(borrower_id: str, company_id: Optional[int], principal: int, 
                     interest_rate: float, total_owed: int, loan_tier: str, 
                     due_date: datetime, thread_id: str) -> Dict:
    """Create a new loan"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO loans (borrower_id, company_id, principal_amount, interest_rate, 
                             total_owed, loan_tier, due_date, thread_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        ''', borrower_id, company_id, principal, interest_rate, total_owed, loan_tier, due_date, thread_id)
        return dict(row)

async def set_loan_embed_message(loan_id: int, message_id: str):
    """Set the embed message ID for a loan"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE loans SET embed_message_id = $2 WHERE id = $1
        ''', loan_id, message_id)

async def get_player_loans(user_id: str, unpaid_only: bool = False) -> List[Dict]:
    """Get loans for a player"""
    async with pool.acquire() as conn:
        if unpaid_only:
            rows = await conn.fetch('''
                SELECT * FROM loans
                WHERE borrower_id = $1 AND is_paid = FALSE
                ORDER BY due_date
            ''', user_id)
        else:
            rows = await conn.fetch('''
                SELECT * FROM loans
                WHERE borrower_id = $1
                ORDER BY due_date DESC
            ''', user_id)
        return [dict(row) for row in rows]

async def get_loan_by_id(loan_id: int) -> Optional[Dict]:
    """Get a loan by ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM loans WHERE id = $1', loan_id)
        return dict(row) if row else None

async def pay_loan(loan_id: int) -> Dict:
    """Mark a loan as paid"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE loans
            SET is_paid = TRUE
            WHERE id = $1
            RETURNING *
        ''', loan_id)
        return dict(row) if row else None

async def get_overdue_loans() -> List[Dict]:
    """Get all overdue unpaid loans"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM loans
            WHERE is_paid = FALSE AND due_date < CURRENT_TIMESTAMP
            ORDER BY due_date
        ''')
        return [dict(row) for row in rows]


# ==================== GUILD SETTINGS ====================

async def get_guild_settings(guild_id: str) -> Optional[Dict]:
    """Get guild settings"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM guild_settings WHERE guild_id = $1', guild_id)
        return dict(row) if row else None

async def set_company_forum(guild_id: str, forum_id: str):
    """Set or update company forum"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, company_forum_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET company_forum_id = $2
        ''', guild_id, forum_id)

async def set_bank_forum(guild_id: str, forum_id: str):
    """Set or update bank forum"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, bank_forum_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET bank_forum_id = $2
        ''', guild_id, forum_id)

async def set_leaderboard_channel(guild_id: str, channel_id: str, message_id: str):
    """Set or update guild leaderboard message"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, leaderboard_channel_id, leaderboard_message_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id)
            DO UPDATE SET leaderboard_channel_id = $2, leaderboard_message_id = $3
        ''', guild_id, channel_id, message_id)

async def upsert_guild_leaderboard(guild_id: str, channel_id: str, message_id: str):
    """Alias for set_leaderboard_channel"""
    await set_leaderboard_channel(guild_id, channel_id, message_id)

async def set_event_frequency(guild_id: str, hours: int):
    """Set or update event frequency in hours"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, event_frequency_hours)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET event_frequency_hours = $2
        ''', guild_id, hours)

async def get_event_frequency(guild_id: str) -> int:
    """Get event frequency for a guild (default 6 hours)"""
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            'SELECT event_frequency_hours FROM guild_settings WHERE guild_id = $1',
            guild_id
        )
        return result if result is not None else 6

async def set_admin_roles(guild_id: str, role_ids: List[str]):
    """Set or update admin roles for a guild"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, admin_role_ids)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET admin_role_ids = $2
        ''', guild_id, role_ids)

async def get_admin_roles(guild_id: str) -> List[str]:
    """Get admin roles for a guild"""
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            'SELECT admin_role_ids FROM guild_settings WHERE guild_id = $1',
            guild_id
        )
        return result if result is not None else []

async def add_admin_role(guild_id: str, role_id: str):
    """Add a single admin role to a guild"""
    current_roles = await get_admin_roles(guild_id)
    if role_id not in current_roles:
        current_roles.append(role_id)
        await set_admin_roles(guild_id, current_roles)

async def remove_admin_role(guild_id: str, role_id: str):
    """Remove a single admin role from a guild"""
    current_roles = await get_admin_roles(guild_id)
    if role_id in current_roles:
        current_roles.remove(role_id)
        await set_admin_roles(guild_id, current_roles)

async def clear_admin_roles(guild_id: str):
    """Clear all admin roles for a guild"""
    await set_admin_roles(guild_id, [])

async def set_command_post_restriction(guild_id: str, command_name: str, post_id: str = None):
    """Set which post a command is restricted to"""
    column_name = f'{command_name}_post_id'
    
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id)
            VALUES ($1)
            ON CONFLICT (guild_id) DO NOTHING
        ''', guild_id)
        
        query = f'''
            UPDATE guild_settings
            SET {column_name} = $2
            WHERE guild_id = $1
        '''
        await conn.execute(query, guild_id, post_id)

async def get_command_post_restriction(guild_id: str, command_name: str) -> Optional[str]:
    """Get the restricted post ID for a command"""
    column_name = f'{command_name}_post_id'
    
    async with pool.acquire() as conn:
        query = f'SELECT {column_name} FROM guild_settings WHERE guild_id = $1'
        result = await conn.fetchval(query, guild_id)
        return result


# ==================== TAX SYSTEM ====================

async def set_tax_rate(guild_id: str, rate: float):
    """Set tax rate for a guild"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, tax_rate)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET tax_rate = $2
        ''', guild_id, rate)

async def get_tax_rate(guild_id: str) -> float:
    """Get tax rate for a guild"""
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            'SELECT tax_rate FROM guild_settings WHERE guild_id = $1',
            guild_id
        )
        return result if result is not None else 0.0

async def set_tax_notification_channel(guild_id: str, channel_id: str):
    """Set tax notification channel"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, tax_notification_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET tax_notification_channel_id = $2
        ''', guild_id, channel_id)

async def get_tax_notification_channel(guild_id: str) -> Optional[str]:
    """Get tax notification channel"""
    async with pool.acquire() as conn:
        return await conn.fetchval(
            'SELECT tax_notification_channel_id FROM guild_settings WHERE guild_id = $1',
            guild_id
        )

async def log_tax_collection(user_id: str, amount: int, guild_id: str):
    """Log a tax collection"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO tax_collections (user_id, amount, guild_id, collected_at)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
        ''', user_id, amount, guild_id)

async def get_last_tax_collection(guild_id: str) -> Optional[Dict]:
    """Get last tax collection for guild"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT SUM(amount) as total_amount, COUNT(*) as players_taxed, 
                   MAX(collected_at) as collected_at
            FROM tax_collections
            WHERE guild_id = $1
            AND collected_at > CURRENT_TIMESTAMP - INTERVAL '6 hours'
            GROUP BY guild_id
        ''', guild_id)
        return dict(row) if row else None

async def get_tax_history(guild_id: str, limit: int = 10) -> List[Dict]:
    """Get tax collection history"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT SUM(amount) as total_amount, COUNT(*) as players_taxed, 
                   DATE_TRUNC('hour', collected_at) as collected_at
            FROM tax_collections
            WHERE guild_id = $1
            GROUP BY DATE_TRUNC('hour', collected_at)
            ORDER BY collected_at DESC
            LIMIT $2
        ''', guild_id, limit)
        return [dict(row) for row in rows]


# ==================== COLLECTIBLES ====================

async def player_owns_collectible(user_id: str, collectible_id: str) -> bool:
    """Check if player owns a collectible"""
    async with pool.acquire() as conn:
        result = await conn.fetchval('''
            SELECT COUNT(*) FROM player_collectibles
            WHERE user_id = $1 AND collectible_id = $2
        ''', user_id, collectible_id)
        return result > 0

async def add_collectible_to_player(user_id: str, collectible_id: str):
    """Add a collectible to player's collection"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO player_collectibles (user_id, collectible_id, acquired_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
        ''', user_id, collectible_id)

async def remove_collectible_from_player(user_id: str, collectible_id: str):
    """Remove a collectible from player's collection"""
    async with pool.acquire() as conn:
        await conn.execute('''
            DELETE FROM player_collectibles
            WHERE user_id = $1 AND collectible_id = $2
        ''', user_id, collectible_id)

async def get_player_collectibles(user_id: str) -> List[Dict]:
    """Get all collectibles owned by player"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM player_collectibles
            WHERE user_id = $1
            ORDER BY acquired_at DESC
        ''', user_id)
        return [dict(row) for row in rows]

async def get_collectibles_stats() -> Dict:
    """Get server-wide collectibles statistics"""
    async with pool.acquire() as conn:
        stats = await conn.fetchrow('''
            SELECT 
                COUNT(DISTINCT user_id) as total_collectors,
                COUNT(*) as total_items,
                (SELECT collectible_id FROM player_collectibles 
                 GROUP BY collectible_id ORDER BY COUNT(*) DESC LIMIT 1) as most_collected
            FROM player_collectibles
        ''')
        
        return {
            'total_collectors': stats['total_collectors'] if stats else 0,
            'total_items': stats['total_items'] if stats else 0,
            'most_collected': stats['most_collected'] if stats else None,
            'total_value': 0
        }


# ==================== STOCK MARKET ====================

async def get_stock_price(symbol: str) -> Optional[int]:
    """Get current stock price"""
    async with pool.acquire() as conn:
        return await conn.fetchval(
            'SELECT price FROM stock_prices WHERE symbol = $1',
            symbol
        )

async def set_stock_price(symbol: str, price: int):
    """Set/update stock price"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO stock_prices (symbol, price, updated_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT (symbol)
            DO UPDATE SET price = $2, updated_at = CURRENT_TIMESTAMP
        ''', symbol, price)

async def get_all_stock_prices() -> Dict[str, int]:
    """Get all current stock prices"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT symbol, price FROM stock_prices')
        return {row['symbol']: row['price'] for row in rows}

async def log_stock_price_change(symbol: str, old_price: int, new_price: int, change_percent: float):
    """Log stock price change"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO stock_price_history (symbol, old_price, new_price, change_percent, changed_at)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
        ''', symbol, old_price, new_price, change_percent)

async def get_stock_price_history(symbol: str, limit: int = 10) -> List[Dict]:
    """Get stock price history"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM stock_price_history
            WHERE symbol = $1
            ORDER BY changed_at DESC
            LIMIT $2
        ''', symbol, limit)
        return [dict(row) for row in rows]

async def add_stock_to_portfolio(user_id: str, symbol: str, shares: int, buy_price: int):
    """Add stocks to player's portfolio"""
    async with pool.acquire() as conn:
        existing = await conn.fetchrow('''
            SELECT * FROM player_stocks WHERE user_id = $1 AND symbol = $2
        ''', user_id, symbol)
        
        if existing:
            total_shares = existing['shares'] + shares
            total_cost = (existing['average_price'] * existing['shares']) + (buy_price * shares)
            new_avg = total_cost // total_shares
            
            await conn.execute('''
                UPDATE player_stocks
                SET shares = $3, average_price = $4
                WHERE user_id = $1 AND symbol = $2
            ''', user_id, symbol, total_shares, new_avg)
        else:
            await conn.execute('''
                INSERT INTO player_stocks (user_id, symbol, shares, average_price)
                VALUES ($1, $2, $3, $4)
            ''', user_id, symbol, shares, buy_price)

async def remove_stock_from_portfolio(user_id: str, symbol: str, shares: int):
    """Remove stocks from player's portfolio"""
    async with pool.acquire() as conn:
        existing = await conn.fetchrow('''
            SELECT * FROM player_stocks WHERE user_id = $1 AND symbol = $2
        ''', user_id, symbol)
        
        if not existing:
            return
        
        if existing['shares'] <= shares:
            await conn.execute('''
                DELETE FROM player_stocks WHERE user_id = $1 AND symbol = $2
            ''', user_id, symbol)
        else:
            await conn.execute('''
                UPDATE player_stocks
                SET shares = shares - $3
                WHERE user_id = $1 AND symbol = $2
            ''', user_id, symbol, shares)

async def get_player_stock_holdings(user_id: str, symbol: str) -> Optional[Dict]:
    """Get player's holdings for a specific stock"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM player_stocks WHERE user_id = $1 AND symbol = $2
        ''', user_id, symbol)
        return dict(row) if row else None

async def get_player_portfolio(user_id: str) -> List[Dict]:
    """Get player's entire stock portfolio"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM player_stocks WHERE user_id = $1 ORDER BY symbol
        ''', user_id)
        return [dict(row) for row in rows]

async def set_stock_market_channel(guild_id: str, channel_id: str):
    """Set stock market display channel"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, stock_market_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET stock_market_channel_id = $2
        ''', guild_id, channel_id)

async def get_stock_market_channel(guild_id: str) -> Optional[str]:
    """Get stock market display channel"""
    async with pool.acquire() as conn:
        return await conn.fetchval(
            'SELECT stock_market_channel_id FROM guild_settings WHERE guild_id = $1',
            guild_id
        )

async def set_stock_market_message(guild_id: str, message_id: str):
    """Set stock market display message"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, stock_market_message_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET stock_market_message_id = $2
        ''', guild_id, message_id)

async def get_stock_market_message(guild_id: str) -> Optional[str]:
    """Get stock market display message"""
    async with pool.acquire() as conn:
        return await conn.fetchval(
            'SELECT stock_market_message_id FROM guild_settings WHERE guild_id = $1',
            guild_id
        )

async def set_stock_update_interval(guild_id: str, minutes: int):
    """Set stock update interval"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, stock_update_interval_minutes)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET stock_update_interval_minutes = $2
        ''', guild_id, minutes)


# ==================== COMPANY WARS/RAIDS ====================

async def get_last_raid_time(company_id: int) -> Optional[datetime]:
    """Get last raid time for a company"""
    async with pool.acquire() as conn:
        return await conn.fetchval('''
            SELECT MAX(raided_at) FROM company_raids
            WHERE attacker_id = $1
        ''', company_id)

async def log_company_raid(attacker_id: int, defender_id: int, success: bool, loot: int, reputation_loss: int):
    """Log a company raid"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO company_raids 
            (attacker_id, defender_id, success, loot, reputation_loss, raided_at)
            VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
        ''', attacker_id, defender_id, success, loot, reputation_loss)

async def create_company_war(attacker_id: int, defender_id: int) -> int:
    """Create a new company war"""
    async with pool.acquire() as conn:
        return await conn.fetchval('''
            INSERT INTO company_wars 
            (attacker_id, defender_id, starts_at, ends_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '24 hours')
            RETURNING id
        ''', attacker_id, defender_id)

async def get_active_war(company1_id: int, company2_id: int) -> Optional[Dict]:
    """Check if there's an active war between two companies"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM company_wars
            WHERE ((attacker_id = $1 AND defender_id = $2) OR (attacker_id = $2 AND defender_id = $1))
            AND ends_at > CURRENT_TIMESTAMP
            AND active = TRUE
        ''', company1_id, company2_id)
        return dict(row) if row else None

async def get_company_wars(company_id: int) -> List[Dict]:
    """Get all active wars for a company"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM company_wars
            WHERE (attacker_id = $1 OR defender_id = $1)
            AND ends_at > CURRENT_TIMESTAMP
            AND active = TRUE
            ORDER BY starts_at DESC
        ''', company_id)
        return [dict(row) for row in rows]


# ==================== CORPORATIONS ====================

async def corporation_name_exists(name: str) -> bool:
    """Check if corporation name exists"""
    async with pool.acquire() as conn:
        result = await conn.fetchval('''
            SELECT COUNT(*) FROM corporations WHERE LOWER(name) = LOWER($1)
        ''', name)
        return result > 0

async def corporation_tag_exists(tag: str) -> bool:
    """Check if corporation tag exists"""
    async with pool.acquire() as conn:
        result = await conn.fetchval('''
            SELECT COUNT(*) FROM corporations WHERE UPPER(tag) = UPPER($1)
        ''', tag)
        return result > 0

async def create_corporation(name: str, tag: str, leader_id: str, guild_id: str) -> int:
    """Create a new corporation"""
    async with pool.acquire() as conn:
        corp_id = await conn.fetchval('''
            INSERT INTO corporations (name, tag, leader_id, guild_id, created_at)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            RETURNING id
        ''', name, tag, leader_id, guild_id)
        
        await conn.execute('''
            INSERT INTO corporation_members (corporation_id, user_id, joined_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
        ''', corp_id, leader_id)
        
        return corp_id

async def get_corporation_by_id(corp_id: int) -> Optional[Dict]:
    """Get corporation by ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM corporations WHERE id = $1
        ''', corp_id)
        return dict(row) if row else None

async def get_corporation_by_leader(leader_id: str) -> Optional[Dict]:
    """Get corporation by leader ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM corporations WHERE leader_id = $1
        ''', leader_id)
        return dict(row) if row else None

async def get_player_corporation(user_id: str) -> Optional[Dict]:
    """Get the corporation a player belongs to"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT c.* FROM corporations c
            JOIN corporation_members cm ON c.id = cm.corporation_id
            WHERE cm.user_id = $1
        ''', user_id)
        return dict(row) if row else None

async def get_corporation_member_limit(guild_id: str) -> int:
    """Get corporation member limit for guild"""
    async with pool.acquire() as conn:
        result = await conn.fetchval('''
            SELECT corporation_member_limit FROM guild_settings WHERE guild_id = $1
        ''', guild_id)
        return result if result is not None else 5

async def get_corporation_member_count(corp_id: int) -> int:
    """Get current member count of corporation"""
    async with pool.acquire() as conn:
        result = await conn.fetchval('''
            SELECT COUNT(*) FROM corporation_members WHERE corporation_id = $1
        ''', corp_id)
        return result or 0

async def create_corporation_invite(corp_id: int, user_id: str):
    """Create a corporation invitation"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO corporation_invites (corporation_id, user_id, created_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT (corporation_id, user_id) DO NOTHING
        ''', corp_id, user_id)

async def get_pending_corporation_invite(user_id: str) -> Optional[Dict]:
    """Get pending corporation invite for user"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM corporation_invites
            WHERE user_id = $1 AND accepted = FALSE
            ORDER BY created_at DESC
            LIMIT 1
        ''', user_id)
        return dict(row) if row else None

async def accept_corporation_invite(invite_id: int, user_id: str):
    """Accept a corporation invitation"""
    async with pool.acquire() as conn:
        corp_id = await conn.fetchval('''
            SELECT corporation_id FROM corporation_invites WHERE id = $1
        ''', invite_id)
        
        await conn.execute('''
            UPDATE corporation_invites SET accepted = TRUE WHERE id = $1
        ''', invite_id)
        
        await conn.execute('''
            INSERT INTO corporation_members (corporation_id, user_id, joined_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
        ''', corp_id, user_id)

async def remove_player_from_corporation(user_id: str):
    """Remove player from their corporation"""
    async with pool.acquire() as conn:
        await conn.execute('''
            DELETE FROM corporation_members WHERE user_id = $1
        ''', user_id)

async def get_corporation_members(corp_id: int) -> List[Dict]:
    """Get all members of a corporation with their balances"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT cm.user_id, p.username, p.balance, cm.joined_at
            FROM corporation_members cm
            JOIN players p ON cm.user_id = p.user_id
            WHERE cm.corporation_id = $1
            ORDER BY p.balance DESC
        ''', corp_id)
        return [dict(row) for row in rows]

async def get_corporation_leaderboard(guild_id: str, limit: int = 25) -> List[Dict]:
    """Get corporation leaderboard by total member wealth"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT 
                c.id,
                c.name,
                c.tag,
                c.leader_id,
                COUNT(cm.user_id) as member_count,
                COALESCE(SUM(p.balance), 0) as total_wealth
            FROM corporations c
            LEFT JOIN corporation_members cm ON c.id = cm.corporation_id
            LEFT JOIN players p ON cm.user_id = p.user_id
            WHERE c.guild_id = $1
            GROUP BY c.id, c.name, c.tag, c.leader_id
            ORDER BY total_wealth DESC
            LIMIT $2
        ''', guild_id, limit)
        return [dict(row) for row in rows]

async def set_corporation_member_limit(guild_id: str, limit: int):
    """Set corporation member limit"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, corporation_member_limit)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET corporation_member_limit = $2
        ''', guild_id, limit)
