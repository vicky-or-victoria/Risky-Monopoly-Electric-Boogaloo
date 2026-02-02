# Database module for Risky Monopoly Discord Bot
# Handles all PostgreSQL database operations using asyncpg

import asyncpg
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Database connection pool
pool: Optional[asyncpg.Pool] = None


# ===== CONNECTION MANAGEMENT =====

async def init_database():
    """Initialize database connection pool and create all tables"""
    global pool
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    try:
        pool = await asyncpg.create_pool(
            database_url,
            min_size=5,
            max_size=20,
            statement_cache_size=0,
            max_inactive_connection_lifetime=300
        )
        
        logger.info("Database connection pool created successfully")
        
        # Create all tables
        await _create_tables()
        
        # Run migrations
        await _run_migrations()
        
        logger.info("✅ Database initialization completed - ALL FEATURES READY")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def _run_migrations():
    """Run database migrations to update schema"""
    async with pool.acquire() as conn:
        # All migrations for backward compatibility
        migrations = [
            'ALTER TABLE players ADD COLUMN IF NOT EXISTS registered_at TIMESTAMP',
            'ALTER TABLE players ADD COLUMN IF NOT EXISTS registration_role_id VARCHAR(255)',
            'ALTER TABLE players ADD COLUMN IF NOT EXISTS loan_dm_notifications BOOLEAN DEFAULT TRUE',
            'ALTER TABLE companies ADD COLUMN IF NOT EXISTS specialization VARCHAR(50) DEFAULT \'stable\'',
            'ALTER TABLE companies ADD COLUMN IF NOT EXISTS last_specialization_change TIMESTAMP',
            'ALTER TABLE companies ADD COLUMN IF NOT EXISTS logo_emoji VARCHAR(255)',
            'ALTER TABLE company_assets ADD COLUMN IF NOT EXISTS is_black_market BOOLEAN DEFAULT FALSE',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS announcements_channel_id VARCHAR(255)',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS achievements_channel_id VARCHAR(255)',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS npc_companies_channel_id VARCHAR(255)',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS npc_companies_message_id VARCHAR(255)',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS bankruptcy_channel_id VARCHAR(255)',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS registration_message_id VARCHAR(255)',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS registration_channel_id VARCHAR(255)',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS registration_role_id VARCHAR(255)',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS daily_quest_message_id VARCHAR(255)',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS sabotage_catch_chance DECIMAL(5,2) DEFAULT 0.20',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS specialization_cooldown_hours INTEGER DEFAULT 24',
            'ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS hall_of_fame_channel_id VARCHAR(255)',
        ]
        
        for migration in migrations:
            try:
                await conn.execute(migration)
            except Exception as e:
                logger.warning(f"Migration note: {e}")


async def close_database():
    """Close database connection pool"""
    global pool
    
    if pool:
        await pool.close()
        pool = None
        logger.info("Database connection pool closed")


async def _create_tables():
    """Create all database tables for ALL features"""
    async with pool.acquire() as conn:
        async with conn.transaction():
            
            # ===== CORE TABLES =====
            
            # Players table - Enhanced with registration and notifications
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    user_id VARCHAR(255) PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    balance BIGINT DEFAULT 0,
                    registered_at TIMESTAMP,
                    registration_role_id VARCHAR(255),
                    loan_dm_notifications BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Companies table - Enhanced with specialization and logo
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
                    specialization VARCHAR(50) DEFAULT 'stable',
                    last_specialization_change TIMESTAMP,
                    logo_emoji VARCHAR(255),
                    thread_id VARCHAR(255) UNIQUE,
                    embed_message_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_event_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Company assets/upgrades table - Enhanced with black market flag
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS company_assets (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    asset_name VARCHAR(255) NOT NULL,
                    asset_type VARCHAR(100) NOT NULL,
                    income_boost BIGINT NOT NULL,
                    cost BIGINT NOT NULL,
                    is_black_market BOOLEAN DEFAULT FALSE,
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
            
            # ===== GUILD SETTINGS - COMPREHENSIVE =====
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id VARCHAR(255) PRIMARY KEY,
                    company_forum_id VARCHAR(255),
                    bank_forum_id VARCHAR(255),
                    leaderboard_channel_id VARCHAR(255),
                    leaderboard_message_id VARCHAR(255),
                    announcements_channel_id VARCHAR(255),
                    achievements_channel_id VARCHAR(255),
                    npc_companies_channel_id VARCHAR(255),
                    npc_companies_message_id VARCHAR(255),
                    bankruptcy_channel_id VARCHAR(255),
                    registration_message_id VARCHAR(255),
                    registration_channel_id VARCHAR(255),
                    registration_role_id VARCHAR(255),
                    daily_quest_message_id VARCHAR(255),
                    hall_of_fame_channel_id VARCHAR(255),
                    event_frequency_hours INTEGER DEFAULT 6,
                    sabotage_catch_chance DECIMAL(5,2) DEFAULT 0.20,
                    specialization_cooldown_hours INTEGER DEFAULT 24,
                    admin_role_ids TEXT[],
                    create_company_post_id VARCHAR(255),
                    request_loan_post_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ===== NEW FEATURE TABLES =====
            
            # Company Mergers
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS company_mergers (
                    id SERIAL PRIMARY KEY,
                    player_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    company1_id INTEGER NOT NULL,
                    company2_id INTEGER NOT NULL,
                    resulting_rank VARCHAR(10) NOT NULL,
                    resulting_company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
                    merged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Server/Seasonal Events
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS server_events (
                    id SERIAL PRIMARY KEY,
                    guild_id VARCHAR(255) NOT NULL,
                    event_name VARCHAR(255) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    event_description TEXT NOT NULL,
                    effect_data JSONB,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ends_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Achievements
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    achievement_type VARCHAR(100) NOT NULL,
                    achievement_name VARCHAR(255) NOT NULL,
                    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, achievement_type)
                )
            ''')
            
            # Daily Quests
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_quests (
                    id SERIAL PRIMARY KEY,
                    guild_id VARCHAR(255) NOT NULL,
                    quest_date DATE NOT NULL,
                    quest_data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, quest_date)
                )
            ''')
            
            # Daily Quest Progress
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_quest_progress (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    guild_id VARCHAR(255) NOT NULL,
                    quest_id INTEGER NOT NULL REFERENCES daily_quests(id) ON DELETE CASCADE,
                    quest_type VARCHAR(100) NOT NULL,
                    progress INTEGER DEFAULT 0,
                    target INTEGER NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    completed_at TIMESTAMP,
                    UNIQUE(user_id, quest_id, quest_type)
                )
            ''')
            
            # Black Market Purchases
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS black_market_purchases (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
                    purchase_type VARCHAR(100) NOT NULL,
                    item_type VARCHAR(100) NOT NULL,
                    cost BIGINT NOT NULL,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Black Market Effects
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS black_market_effects (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    effect_type VARCHAR(100) NOT NULL,
                    effect_value DECIMAL(10,2) NOT NULL,
                    expires_at TIMESTAMP,
                    UNIQUE(company_id, effect_type)
                )
            ''')
            
            # Sabotage Actions
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS sabotage_operations (
                    id SERIAL PRIMARY KEY,
                    saboteur_company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    target_company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    action_type VARCHAR(100) NOT NULL,
                    spy_count INTEGER DEFAULT 0,
                    planning_cost BIGINT DEFAULT 0,
                    preparation_time_hours INTEGER DEFAULT 0,
                    is_prepared BOOLEAN DEFAULT FALSE,
                    executed BOOLEAN DEFAULT FALSE,
                    was_successful BOOLEAN,
                    was_caught BOOLEAN,
                    damage_dealt BIGINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ready_at TIMESTAMP,
                    executed_at TIMESTAMP,
                    sabotage_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Espionage Missions
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS espionage_missions (
                    id SERIAL PRIMARY KEY,
                    spy_company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    target_company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    mission_type VARCHAR(50) NOT NULL,
                    was_successful BOOLEAN NOT NULL,
                    mission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Company Raids
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS company_raids (
                    id SERIAL PRIMARY KEY,
                    attacker_company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    target_company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                    was_successful BOOLEAN NOT NULL,
                    income_stolen BIGINT DEFAULT 0,
                    raid_cost BIGINT NOT NULL,
                    battle_duration_hours INTEGER DEFAULT 24,
                    raid_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ends_at TIMESTAMP
                )
            ''')
            
            # Mega Projects
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS mega_projects (
                    id SERIAL PRIMARY KEY,
                    guild_id VARCHAR(255) NOT NULL,
                    project_key VARCHAR(100) NOT NULL,
                    project_name VARCHAR(255) NOT NULL,
                    project_rank VARCHAR(10) NOT NULL,
                    project_description TEXT NOT NULL,
                    cost BIGINT NOT NULL,
                    owner_id VARCHAR(255) REFERENCES players(user_id) ON DELETE SET NULL,
                    funder_id VARCHAR(255) REFERENCES players(user_id) ON DELETE SET NULL,
                    effect_data JSONB,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, project_key),
                    UNIQUE(guild_id, project_name)
                )
            ''')
            
            # Corporations
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS corporations (
                    id SERIAL PRIMARY KEY,
                    guild_id VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    tag VARCHAR(10) NOT NULL,
                    leader_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    treasury BIGINT DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    wars_won INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, name),
                    UNIQUE(guild_id, tag)
                )
            ''')
            
            # Corporation Members
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS corporation_members (
                    id SERIAL PRIMARY KEY,
                    corporation_id INTEGER NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(corporation_id, user_id)
                )
            ''')
            
            # Corporation Wars
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS corporation_wars (
                    id SERIAL PRIMARY KEY,
                    attacker_corp_id INTEGER NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
                    defender_corp_id INTEGER NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
                    prize_pool BIGINT NOT NULL,
                    attacker_score INTEGER DEFAULT 0,
                    defender_score INTEGER DEFAULT 0,
                    winner_corp_id INTEGER REFERENCES corporations(id) ON DELETE SET NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ends_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # NPC Companies
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS npc_companies (
                    id SERIAL PRIMARY KEY,
                    guild_id VARCHAR(255) NOT NULL,
                    company_key VARCHAR(100) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    rank VARCHAR(10) NOT NULL,
                    sector VARCHAR(100) NOT NULL,
                    base_value BIGINT NOT NULL,
                    base_income BIGINT NOT NULL,
                    current_value BIGINT NOT NULL,
                    current_income BIGINT NOT NULL,
                    share_price BIGINT NOT NULL,
                    total_shares INTEGER DEFAULT 1000,
                    available_shares INTEGER DEFAULT 1000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_event_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, company_key)
                )
            ''')
            
            # NPC Investments
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS npc_investments (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    npc_company_id INTEGER NOT NULL REFERENCES npc_companies(id) ON DELETE CASCADE,
                    shares INTEGER NOT NULL,
                    shares_owned INTEGER NOT NULL,
                    purchase_price BIGINT NOT NULL,
                    invested_amount BIGINT NOT NULL,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    invested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, npc_company_id)
                )
            ''')
            
            # NPC Dividend Payments
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS npc_dividend_payments (
                    id SERIAL PRIMARY KEY,
                    investment_id INTEGER NOT NULL REFERENCES npc_investments(id) ON DELETE CASCADE,
                    amount BIGINT NOT NULL,
                    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Hall of Fame
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS hall_of_fame (
                    id SERIAL PRIMARY KEY,
                    guild_id VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    user_id VARCHAR(255) NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
                    record_value BIGINT NOT NULL,
                    additional_info TEXT,
                    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, category)
                )
            ''')
            
            # Hall of Fame Announcements
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS hall_of_fame_announcements (
                    id SERIAL PRIMARY KEY,
                    guild_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    announced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            logger.info("✅ All database tables created successfully")


# ===== PLAYER FUNCTIONS =====

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


async def register_player(user_id: str, username: str, role_id: str) -> Dict:
    """Register a player with a role"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO players (user_id, username, balance, registered_at, registration_role_id)
            VALUES ($1, $2, 0, CURRENT_TIMESTAMP, $3)
            ON CONFLICT (user_id)
            DO UPDATE SET 
                username = $2, 
                registered_at = COALESCE(players.registered_at, CURRENT_TIMESTAMP),
                registration_role_id = $3,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
        ''', user_id, username, role_id)
        return dict(row)


async def update_player_balance(user_id: str, amount: int) -> Dict:
    """Update a player's balance"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE players
            SET balance = balance + $2, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1
            RETURNING *
        ''', user_id, amount)
        return dict(row) if row else None


async def set_loan_notifications(user_id: str, enabled: bool):
    """Set whether user receives loan DM notifications"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE players
            SET loan_dm_notifications = $2
            WHERE user_id = $1
        ''', user_id, enabled)


async def get_player_stats(user_id: str) -> Dict:
    """Get comprehensive player statistics"""
    async with pool.acquire() as conn:
        player = await conn.fetchrow('SELECT * FROM players WHERE user_id = $1', user_id)
        
        if not player:
            return {}
        
        loans_taken = await conn.fetchval(
            'SELECT COUNT(*) FROM loans WHERE borrower_id = $1', user_id
        ) or 0
        
        loans_repaid = await conn.fetchval(
            'SELECT COUNT(*) FROM loans WHERE borrower_id = $1 AND is_paid = TRUE', user_id
        ) or 0
        
        companies = await conn.fetch(
            'SELECT * FROM companies WHERE owner_id = $1', user_id
        )
        
        active_companies = len(companies)
        ranks = set([c['rank'] for c in companies])
        max_income = max([c['current_income'] for c in companies]) if companies else 0
        max_reputation = max([c['reputation'] for c in companies]) if companies else 0
        
        mergers = await conn.fetchval(
            'SELECT COUNT(*) FROM company_mergers WHERE player_id = $1', user_id
        ) or 0
        
        black_market = await conn.fetchval(
            'SELECT COUNT(*) FROM black_market_purchases WHERE user_id = $1', user_id
        ) or 0
        
        quests = await conn.fetchval(
            'SELECT COUNT(*) FROM daily_quest_progress WHERE user_id = $1 AND completed = TRUE', user_id
        ) or 0
        
        achievements = await conn.fetchval(
            'SELECT COUNT(*) FROM achievements WHERE user_id = $1', user_id
        ) or 0
        
        return {
            'balance': player['balance'],
            'loans_taken': loans_taken,
            'loans_repaid': loans_repaid,
            'active_companies': active_companies,
            'ranks_achieved': list(ranks),
            'mergers_completed': mergers,
            'black_market_uses': black_market,
            'quests_completed': quests,
            'max_reputation': max_reputation,
            'max_company_income': max_income,
            'achievements_count': achievements
        }


# ===== COMPANY FUNCTIONS =====

async def create_company(owner_id: str, name: str, rank: str, company_type: str, base_income: int) -> Dict:
    """Create a new company"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO companies (owner_id, name, rank, type, base_income, current_income, reputation, specialization)
            VALUES ($1, $2, $3, $4, $5, $5, 50, 'stable')
            RETURNING *
        ''', owner_id, name, rank, company_type, base_income)
        return dict(row)


async def get_company_by_id(company_id: int) -> Optional[Dict]:
    """Get a company by ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM companies WHERE id = $1', company_id)
        return dict(row) if row else None


async def get_companies_by_owner(owner_id: str) -> List[Dict]:
    """Get all companies owned by a user"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM companies
            WHERE owner_id = $1
            ORDER BY created_at DESC
        ''', owner_id)
        return [dict(row) for row in rows]


async def get_company_by_thread(thread_id: str) -> Optional[Dict]:
    """Get a company by its thread ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM companies WHERE thread_id = $1', thread_id)
        return dict(row) if row else None


async def set_company_thread(company_id: int, thread_id: str, embed_message_id: str) -> Dict:
    """Set company thread and embed message"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE companies
            SET thread_id = $2, embed_message_id = $3
            WHERE id = $1
            RETURNING *
        ''', company_id, thread_id, embed_message_id)
        return dict(row)


async def update_company_income(company_id: int, income_change: int) -> Dict:
    """Update company income"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE companies
            SET current_income = current_income + $2, last_event_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING *
        ''', company_id, income_change)
        
        if row:
            try:
                import auto_updates
                await auto_updates.trigger_updates_for_company_change(company_id)
            except:
                pass
        
        return dict(row) if row else None


async def set_company_income(company_id: int, new_income: int):
    """Set company income to a specific value"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE companies
            SET current_income = $1
            WHERE id = $2
        ''', new_income, company_id)


async def modify_company_income(company_id: int, income_change: int, duration_hours: int = None):
    """Modify company income (temporarily if duration specified)"""
    await update_company_income(company_id, income_change)


async def update_company_specialization(company_id: int, specialization: str) -> Dict:
    """Update company specialization"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE companies
            SET specialization = $2, last_specialization_change = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING *
        ''', company_id, specialization)
        return dict(row) if row else None


async def delete_company(company_id: int):
    """Delete a company"""
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM companies WHERE id = $1', company_id)


async def get_all_companies() -> List[Dict]:
    """Get all companies"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM companies ORDER BY created_at DESC')
        return [dict(row) for row in rows]


async def get_guild_companies_by_rank(guild_id: str, rank: str) -> List[Dict]:
    """Get all companies in a guild by rank"""
    # Note: This is simplified - in production you'd want guild_id in companies table
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM companies WHERE rank = $1', rank)
        return [dict(row) for row in rows]


# ===== COMPANY MERGERS =====

async def merge_companies(player_id: str, company1_id: int, company2_id: int, 
                          resulting_rank: str, resulting_company_id: int):
    """Record a company merger"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO company_mergers (player_id, company1_id, company2_id, resulting_rank, resulting_company_id)
            VALUES ($1, $2, $3, $4, $5)
        ''', player_id, company1_id, company2_id, resulting_rank, resulting_company_id)


async def get_player_mergers(player_id: str) -> List[Dict]:
    """Get all mergers by a player"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM company_mergers
            WHERE player_id = $1
            ORDER BY merged_at DESC
        ''', player_id)
        return [dict(row) for row in rows]


# ===== COMPANY ASSETS =====

async def add_company_asset(company_id: int, asset_name: str, asset_type: str, 
                           income_boost: int, cost: int, is_black_market: bool = False):
    """Add an asset to a company"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO company_assets (company_id, asset_name, asset_type, income_boost, cost, is_black_market)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', company_id, asset_name, asset_type, income_boost, cost, is_black_market)


async def get_company_assets(company_id: int) -> List[Dict]:
    """Get all assets for a company"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM company_assets
            WHERE company_id = $1
            ORDER BY purchased_at DESC
        ''', company_id)
        return [dict(row) for row in rows]


# Continuing in next message due to length...

# ===== EVENTS =====

async def log_company_event(company_id: int, event_type: str, event_description: str, income_change: int):
    """Log a company event"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO company_events (company_id, event_type, event_description, income_change)
            VALUES ($1, $2, $3, $4)
        ''', company_id, event_type, event_description, income_change)


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


async def get_company_event_history(company_id: int, limit: int = 5) -> List[Dict]:
    """Alias for get_company_events"""
    return await get_company_events(company_id, limit)


# ===== SERVER EVENTS =====

async def create_server_event(guild_id: str, event_name: str, event_type: str, 
                              event_description: str, effect_data: dict, duration_hours: int = 24) -> Dict:
    """Create a new server event"""
    async with pool.acquire() as conn:
        ends_at = datetime.now() + timedelta(hours=duration_hours)
        row = await conn.fetchrow('''
            INSERT INTO server_events (guild_id, event_name, event_type, event_description, effect_data, ends_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        ''', guild_id, event_name, event_type, event_description, json.dumps(effect_data), ends_at)
        return dict(row)


async def get_active_server_events(guild_id: str) -> List[Dict]:
    """Get all active server events"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM server_events
            WHERE guild_id = $1 AND is_active = TRUE 
            AND (ends_at IS NULL OR ends_at > CURRENT_TIMESTAMP)
            ORDER BY started_at DESC
        ''', guild_id)
        results = []
        for row in rows:
            data = dict(row)
            if data.get('effect_data'):
                data['effect_data'] = json.loads(data['effect_data'])
            results.append(data)
        return results


async def end_server_event(event_id: int):
    """End a server event"""
    async with pool.acquire() as conn:
        await conn.execute('UPDATE server_events SET is_active = FALSE WHERE id = $1', event_id)


# ===== ACHIEVEMENTS =====

async def grant_achievement(user_id: str, achievement_type: str, achievement_name: str) -> bool:
    """Grant achievement. Returns True if newly granted"""
    async with pool.acquire() as conn:
        try:
            await conn.execute('''
                INSERT INTO achievements (user_id, achievement_type, achievement_name)
                VALUES ($1, $2, $3)
            ''', user_id, achievement_type, achievement_name)
            return True
        except asyncpg.UniqueViolationError:
            return False


async def get_player_achievements(user_id: str) -> List[Dict]:
    """Get all achievements for a player"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM achievements WHERE user_id = $1 ORDER BY achieved_at DESC
        ''', user_id)
        return [dict(row) for row in rows]


async def has_achievement(user_id: str, achievement_type: str) -> bool:
    """Check if player has achievement"""
    async with pool.acquire() as conn:
        result = await conn.fetchval('''
            SELECT EXISTS(SELECT 1 FROM achievements WHERE user_id = $1 AND achievement_type = $2)
        ''', user_id, achievement_type)
        return result


# ===== DAILY QUESTS =====

async def create_daily_quests(guild_id: str, quest_data: dict) -> Dict:
    """Create daily quests"""
    async with pool.acquire() as conn:
        quest_date = datetime.now().date()
        row = await conn.fetchrow('''
            INSERT INTO daily_quests (guild_id, quest_date, quest_data)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, quest_date)
            DO UPDATE SET quest_data = $3
            RETURNING *
        ''', guild_id, quest_date, json.dumps(quest_data))
        result = dict(row)
        result['quest_data'] = json.loads(result['quest_data'])
        return result


async def get_daily_quests(guild_id: str) -> Optional[Dict]:
    """Get today's daily quests"""
    async with pool.acquire() as conn:
        quest_date = datetime.now().date()
        row = await conn.fetchrow('''
            SELECT * FROM daily_quests WHERE guild_id = $1 AND quest_date = $2
        ''', guild_id, quest_date)
        if row:
            result = dict(row)
            result['quest_data'] = json.loads(result['quest_data'])
            return result
        return None


async def update_quest_progress(user_id: str, guild_id: str, quest_id: int, 
                                quest_type: str, progress: int, target: int) -> Dict:
    """Update quest progress"""
    async with pool.acquire() as conn:
        completed = progress >= target
        row = await conn.fetchrow('''
            INSERT INTO daily_quest_progress (user_id, guild_id, quest_id, quest_type, progress, target, completed, completed_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id, quest_id, quest_type)
            DO UPDATE SET progress = $5, completed = $7, 
                         completed_at = CASE WHEN $7 THEN CURRENT_TIMESTAMP ELSE NULL END
            RETURNING *
        ''', user_id, guild_id, quest_id, quest_type, progress, target, completed, 
             datetime.now() if completed else None)
        return dict(row)


async def get_quest_progress(user_id: str, guild_id: str) -> List[Dict]:
    """Get quest progress for user today"""
    async with pool.acquire() as conn:
        quest_date = datetime.now().date()
        rows = await conn.fetch('''
            SELECT dqp.* FROM daily_quest_progress dqp
            JOIN daily_quests dq ON dqp.quest_id = dq.id
            WHERE dqp.user_id = $1 AND dqp.guild_id = $2 AND dq.quest_date = $3
        ''', user_id, guild_id, quest_date)
        return [dict(row) for row in rows]


# ===== BLACK MARKET =====

async def log_black_market_purchase(user_id: str, purchase_type: str, company_id: Optional[int], cost: int):
    """Log black market purchase"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO black_market_purchases (user_id, company_id, purchase_type, item_type, cost)
            VALUES ($1, $2, $3, $3, $4)
        ''', user_id, company_id, purchase_type, cost)


async def record_black_market_purchase(user_id: str, company_id: int, item_type: str, cost: int):
    """Record black market purchase (alias)"""
    await log_black_market_purchase(user_id, item_type, company_id, cost)


async def get_black_market_purchases(user_id: str) -> List[Dict]:
    """Get all black market purchases"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM black_market_purchases
            WHERE user_id = $1 ORDER BY purchased_at DESC
        ''', user_id)
        return [dict(row) for row in rows]


async def add_black_market_effect(company_id: int, effect_type: str, effect_value: float, duration_hours: int):
    """Add black market effect"""
    expires_at = datetime.now() + timedelta(hours=duration_hours)
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO black_market_effects (company_id, effect_type, effect_value, expires_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (company_id, effect_type) 
            DO UPDATE SET effect_value = $2, expires_at = $4
        ''', company_id, effect_type, effect_value, expires_at)


async def get_black_market_effect(company_id: int, effect_type: str):
    """Get black market effect"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM black_market_effects
            WHERE company_id = $1 AND effect_type = $2
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        ''', company_id, effect_type)
        return dict(row) if row else None


async def consume_black_market_effect(effect_id: int):
    """Consume/remove effect"""
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM black_market_effects WHERE id = $1', effect_id)


# ===== SABOTAGE =====

async def create_sabotage_action(attacker_id: str, target_company_id: int, action_type: str,
                                  spy_count: int = 0, planning_cost: int = 0, 
                                  preparation_time_hours: int = 0) -> Dict:
    """Create sabotage action"""
    async with pool.acquire() as conn:
        ready_at = datetime.now() + timedelta(hours=preparation_time_hours) if preparation_time_hours > 0 else datetime.now()
        is_prepared = preparation_time_hours == 0
        
        # Get attacker's company
        attacker_company = await conn.fetchrow(
            'SELECT id FROM companies WHERE owner_id = $1 LIMIT 1', attacker_id
        )
        if not attacker_company:
            raise ValueError("Attacker has no company")
        
        row = await conn.fetchrow('''
            INSERT INTO sabotage_operations 
            (saboteur_company_id, target_company_id, action_type, spy_count, planning_cost, 
             preparation_time_hours, is_prepared, ready_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        ''', attacker_company['id'], target_company_id, action_type, spy_count, planning_cost,
             preparation_time_hours, is_prepared, ready_at)
        return dict(row)


async def record_sabotage_operation(saboteur_company_id: int, target_company_id: int,
                                     was_successful: bool, was_caught: bool, damage_dealt: int):
    """Record sabotage operation"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO sabotage_operations 
            (saboteur_company_id, target_company_id, was_successful, was_caught, damage_dealt, executed = TRUE)
            VALUES ($1, $2, $3, $4, $5)
        ''', saboteur_company_id, target_company_id, was_successful, was_caught, damage_dealt)


async def get_ready_sabotage_actions(attacker_id: str) -> List[Dict]:
    """Get ready sabotage actions"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT so.* FROM sabotage_operations so
            JOIN companies c ON so.saboteur_company_id = c.id
            WHERE c.owner_id = $1 AND so.is_prepared = TRUE AND so.executed = FALSE
            ORDER BY so.ready_at DESC
        ''', attacker_id)
        return [dict(row) for row in rows]


async def execute_sabotage_action(sabotage_id: int, was_caught: bool):
    """Mark sabotage as executed"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE sabotage_operations
            SET executed = TRUE, was_caught = $2, executed_at = CURRENT_TIMESTAMP
            WHERE id = $1
        ''', sabotage_id, was_caught)


# ===== ESPIONAGE =====

async def record_espionage_mission(spy_company_id: int, target_company_id: int,
                                    mission_type: str, was_successful: bool):
    """Record espionage mission"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO espionage_missions (spy_company_id, target_company_id, mission_type, was_successful)
            VALUES ($1, $2, $3, $4)
        ''', spy_company_id, target_company_id, mission_type, was_successful)


# ===== COMPANY RAIDS =====

async def record_company_raid(attacker_company_id: int, target_company_id: int,
                               was_successful: bool, income_stolen: int, raid_cost: int):
    """Record company raid"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO company_raids 
            (attacker_company_id, target_company_id, was_successful, income_stolen, raid_cost)
            VALUES ($1, $2, $3, $4, $5)
        ''', attacker_company_id, target_company_id, was_successful, income_stolen, raid_cost)


async def create_company_battle(attacker_company_id: int, defender_company_id: int,
                                 battle_cost: int, duration_hours: int = 24) -> Dict:
    """Create company battle"""
    async with pool.acquire() as conn:
        ends_at = datetime.now() + timedelta(hours=duration_hours)
        row = await conn.fetchrow('''
            INSERT INTO company_raids
            (attacker_company_id, target_company_id, was_successful, raid_cost, battle_duration_hours, ends_at)
            VALUES ($1, $2, FALSE, $3, $4, $5)
            RETURNING *
        ''', attacker_company_id, defender_company_id, battle_cost, duration_hours, ends_at)
        return dict(row)


async def resolve_company_battle(battle_id: int, success: bool, income_stolen: int):
    """Resolve company battle"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE company_raids
            SET was_successful = $2, income_stolen = $3
            WHERE id = $1
        ''', battle_id, success, income_stolen)


async def get_recent_raid(company_id: int):
    """Get most recent raid"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM company_raids
            WHERE attacker_company_id = $1
            ORDER BY raid_time DESC LIMIT 1
        ''', company_id)
        return dict(row) if row else None


async def get_company_raid_history(company_id: int, limit: int = 10):
    """Get raid history"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM company_raids
            WHERE attacker_company_id = $1 OR target_company_id = $1
            ORDER BY raid_time DESC LIMIT $2
        ''', company_id, limit)
        return [dict(row) for row in rows]


async def get_active_company_battles(company_id: int) -> List[Dict]:
    """Get active battles"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM company_raids
            WHERE (attacker_company_id = $1 OR target_company_id = $1)
            AND ends_at > CURRENT_TIMESTAMP
            ORDER BY raid_time DESC
        ''', company_id)
        return [dict(row) for row in rows]


# ===== MEGA PROJECTS =====

async def create_mega_project(guild_id: str, project_key: str, project_name: str,
                               project_rank: str, project_description: str, cost: int,
                               owner_id: str, effect_data: dict) -> Dict:
    """Create mega project"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO mega_projects 
            (guild_id, project_key, project_name, project_rank, project_description, cost, owner_id, funder_id, effect_data)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $7, $8)
            RETURNING *
        ''', guild_id, project_key, project_name, project_rank, project_description, cost, owner_id, json.dumps(effect_data))
        result = dict(row)
        result['effect_data'] = json.loads(result['effect_data'])
        return result


async def get_active_mega_projects(guild_id: str) -> List[Dict]:
    """Get active mega projects"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM mega_projects
            WHERE guild_id = $1 AND is_active = TRUE
            ORDER BY created_at DESC
        ''', guild_id)
        results = []
        for row in rows:
            data = dict(row)
            if data.get('effect_data'):
                data['effect_data'] = json.loads(data['effect_data'])
            results.append(data)
        return results


async def get_mega_projects_by_rank(guild_id: str, rank: str) -> List[Dict]:
    """Get mega projects by rank"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM mega_projects
            WHERE guild_id = $1 AND project_rank = $2 AND is_active = TRUE
        ''', guild_id, rank)
        results = []
        for row in rows:
            data = dict(row)
            if data.get('effect_data'):
                data['effect_data'] = json.loads(data['effect_data'])
            results.append(data)
        return results


async def get_completed_mega_projects(guild_id: str) -> List[Dict]:
    """Get completed mega projects"""
    return await get_active_mega_projects(guild_id)


# ===== CORPORATIONS =====

async def create_corporation(guild_id: str, name: str, leader_id: str, tag: str = None) -> int:
    """Create corporation"""
    if not tag:
        tag = name[:3].upper()
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO corporations (guild_id, name, tag, leader_id)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        ''', guild_id, name, tag, leader_id)
        return row['id']


async def get_corporation(corp_id: int) -> Optional[Dict]:
    """Get corporation by ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM corporations WHERE id = $1', corp_id)
        return dict(row) if row else None


async def get_corporation_by_id(corp_id: int) -> Optional[Dict]:
    """Alias for get_corporation"""
    return await get_corporation(corp_id)


async def get_corporation_by_name(guild_id: str, name: str) -> Optional[Dict]:
    """Get corporation by name"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM corporations
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
        ''', guild_id, name)
        return dict(row) if row else None


async def get_corporation_by_tag(guild_id: str, tag: str) -> Optional[Dict]:
    """Get corporation by tag"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM corporations
            WHERE guild_id = $1 AND UPPER(tag) = UPPER($2)
        ''', guild_id, tag)
        return dict(row) if row else None


async def get_player_corporation(guild_id: str, user_id: str) -> Optional[Dict]:
    """Get player's corporation"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT c.* FROM corporations c
            JOIN corporation_members cm ON c.id = cm.corporation_id
            WHERE c.guild_id = $1 AND cm.user_id = $2
        ''', guild_id, user_id)
        return dict(row) if row else None


async def add_corporation_member(corp_id: int, user_id: str, role: str = 'member'):
    """Add member to corporation"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO corporation_members (corporation_id, user_id, role)
            VALUES ($1, $2, $3)
        ''', corp_id, user_id, role)


async def remove_corporation_member(corp_id: int, user_id: str):
    """Remove member from corporation"""
    async with pool.acquire() as conn:
        await conn.execute('''
            DELETE FROM corporation_members
            WHERE corporation_id = $1 AND user_id = $2
        ''', corp_id, user_id)


async def get_corporation_member(corp_id: int, user_id: str):
    """Get corporation member"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM corporation_members
            WHERE corporation_id = $1 AND user_id = $2
        ''', corp_id, user_id)
        return dict(row) if row else None


async def get_corporation_members(corp_id: int) -> List[Dict]:
    """Get all corporation members"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT cm.*, p.username, p.balance
            FROM corporation_members cm
            JOIN players p ON cm.user_id = p.user_id
            WHERE cm.corporation_id = $1
            ORDER BY 
                CASE cm.role 
                    WHEN 'leader' THEN 1 
                    WHEN 'officer' THEN 2 
                    ELSE 3 
                END,
                cm.joined_at ASC
        ''', corp_id)
        return [dict(row) for row in rows]


async def get_corporation_member_count(corp_id: int) -> int:
    """Get member count"""
    async with pool.acquire() as conn:
        count = await conn.fetchval('''
            SELECT COUNT(*) FROM corporation_members WHERE corporation_id = $1
        ''', corp_id)
        return count or 0


async def add_to_corporation_treasury(corp_id: int, amount: int):
    """Add to treasury"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE corporations SET treasury = treasury + $1 WHERE id = $2
        ''', amount, corp_id)


async def delete_corporation(corp_id: int):
    """Delete corporation"""
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM corporations WHERE id = $1', corp_id)


async def get_all_corporations(guild_id: str) -> List[Dict]:
    """Get all corporations in guild"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM corporations
            WHERE guild_id = $1
            ORDER BY level DESC, treasury DESC
        ''', guild_id)
        return [dict(row) for row in rows]


async def get_guild_corporations(guild_id: str) -> List[Dict]:
    """Alias for get_all_corporations"""
    return await get_all_corporations(guild_id)


async def get_corporation_stats(corp_id: int) -> Dict:
    """Get corporation stats"""
    async with pool.acquire() as conn:
        total_raids = await conn.fetchval('''
            SELECT COUNT(*) FROM company_raids cr
            JOIN companies c ON cr.attacker_company_id = c.id
            JOIN corporation_members cm ON c.owner_id = cm.user_id
            WHERE cm.corporation_id = $1
        ''', corp_id) or 0
        
        wars_won = await conn.fetchval(
            'SELECT wars_won FROM corporations WHERE id = $1', corp_id
        ) or 0
        
        return {
            'total_raids': total_raids,
            'wars_won': wars_won
        }


# ===== CORPORATION WARS =====

async def create_corporation_war(attacker_corp_id: int, defender_corp_id: int,
                                  prize_pool: int, duration_hours: int = 168) -> int:
    """Create corporation war"""
    ends_at = datetime.now() + timedelta(hours=duration_hours)
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO corporation_wars (attacker_corp_id, defender_corp_id, prize_pool, ends_at)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        ''', attacker_corp_id, defender_corp_id, prize_pool, ends_at)
        return row['id']


async def create_corporation_battle(attacker_corp_id: int, defender_corp_id: int,
                                     battle_cost: int, duration_hours: int = 24) -> Dict:
    """Alias for create_corporation_war"""
    war_id = await create_corporation_war(attacker_corp_id, defender_corp_id, battle_cost, duration_hours)
    return await get_active_corporation_war_by_id(war_id)


async def resolve_corporation_battle(battle_id: int, success: bool, reward_amount: int):
    """Resolve corporation battle"""
    async with pool.acquire() as conn:
        winner_id = None
        if success:
            war = await conn.fetchrow('SELECT attacker_corp_id FROM corporation_wars WHERE id = $1', battle_id)
            if war:
                winner_id = war['attacker_corp_id']
        
        await conn.execute('''
            UPDATE corporation_wars
            SET winner_corp_id = $2, is_active = FALSE
            WHERE id = $1
        ''', battle_id, winner_id)


async def get_active_corporation_war(attacker_corp_id: int, defender_corp_id: int):
    """Get active war between corps"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM corporation_wars
            WHERE ((attacker_corp_id = $1 AND defender_corp_id = $2)
               OR (attacker_corp_id = $2 AND defender_corp_id = $1))
            AND is_active = TRUE
        ''', attacker_corp_id, defender_corp_id)
        return dict(row) if row else None


async def get_active_corporation_war_by_id(war_id: int):
    """Get war by ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM corporation_wars WHERE id = $1', war_id)
        return dict(row) if row else None


async def get_active_corporation_wars(guild_id: str) -> List[Dict]:
    """Get all active wars in guild"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT cw.* FROM corporation_wars cw
            JOIN corporations c ON cw.attacker_corp_id = c.id
            WHERE c.guild_id = $1 AND cw.is_active = TRUE
            ORDER BY cw.started_at DESC
        ''', guild_id)
        return [dict(row) for row in rows]


async def get_corporation_war_by_id(war_id: int) -> Optional[Dict]:
    """Get any war by ID (active or not)"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM corporation_wars WHERE id = $1', war_id)
        return dict(row) if row else None


async def end_corporation_war(war_id: int, winner_corp_id: Optional[int] = None, forced: bool = False):
    """End a corporation war"""
    async with pool.acquire() as conn:
        # Update war status
        await conn.execute('''
            UPDATE corporation_wars
            SET is_active = FALSE, 
                winner_corp_id = $2,
                ended = TRUE,
                ended_at = $3
            WHERE id = $1
        ''', war_id, winner_corp_id, datetime.now())
        
        # If there's a winner and not forced, update their stats
        if winner_corp_id and not forced:
            await conn.execute('''
                UPDATE corporations
                SET wars_won = wars_won + 1
                WHERE id = $1
            ''', winner_corp_id)


async def update_corporation_treasury(corp_id: int, amount: int):
    """Update corporation treasury (can be positive or negative)"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE corporations SET treasury = treasury + $1 WHERE id = $2
        ''', amount, corp_id)


# Continuing in next message...

# ===== NPC COMPANIES =====

async def create_npc_company(guild_id: str, company_key: str, name: str, rank: str,
                             sector: str, base_value: int, share_price: int) -> int:
    """Create NPC company"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO npc_companies 
            (guild_id, company_key, name, rank, sector, base_value, base_income, 
             current_value, current_income, share_price)
            VALUES ($1, $2, $3, $4, $5, $6, $6, $6, $6, $7)
            RETURNING id
        ''', guild_id, company_key, name, rank, sector, base_value, share_price)
        return row['id']


async def get_npc_company(npc_company_id: int) -> Optional[Dict]:
    """Get NPC company by ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM npc_companies WHERE id = $1', npc_company_id)
        return dict(row) if row else None


async def get_npc_company_by_id(npc_company_id: int) -> Optional[Dict]:
    """Alias for get_npc_company"""
    return await get_npc_company(npc_company_id)


async def get_npc_company_by_key(guild_id: str, company_key: str):
    """Get NPC company by key"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM npc_companies WHERE guild_id = $1 AND company_key = $2
        ''', guild_id, company_key)
        return dict(row) if row else None


async def get_npc_company_by_name(guild_id: str, name: str):
    """Get NPC company by name"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM npc_companies
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
        ''', guild_id, name)
        return dict(row) if row else None


async def get_all_npc_companies(guild_id: str) -> List[Dict]:
    """Get all NPC companies"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM npc_companies WHERE guild_id = $1 ORDER BY name ASC
        ''', guild_id)
        return [dict(row) for row in rows]


async def get_guild_npc_companies(guild_id: str) -> List[Dict]:
    """Alias for get_all_npc_companies"""
    return await get_all_npc_companies(guild_id)


async def update_npc_company_value(npc_company_id: int, new_value: int):
    """Update NPC company value"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE npc_companies SET current_value = $1 WHERE id = $2
        ''', new_value, npc_company_id)


async def update_npc_company_income(npc_company_id: int, income_change: int):
    """Update NPC company income"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE npc_companies
            SET current_income = current_income + $2, last_event_at = CURRENT_TIMESTAMP
            WHERE id = $1
        ''', npc_company_id, income_change)


# ===== NPC INVESTMENTS =====

async def invest_in_npc_company(user_id: str, npc_company_id: int, shares: int, amount: int) -> Dict:
    """Create/update NPC investment"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE npc_companies
            SET available_shares = available_shares - $2
            WHERE id = $1
        ''', npc_company_id, shares)
        
        row = await conn.fetchrow('''
            INSERT INTO npc_investments (user_id, npc_company_id, shares, shares_owned, purchase_price, invested_amount)
            VALUES ($1, $2, $3, $3, $4, $4)
            ON CONFLICT (user_id, npc_company_id)
            DO UPDATE SET 
                shares = npc_investments.shares + $3,
                shares_owned = npc_investments.shares_owned + $3,
                invested_amount = npc_investments.invested_amount + $4
            RETURNING *
        ''', user_id, npc_company_id, shares, amount)
        return dict(row)


async def create_npc_investment(user_id: str, npc_company_id: int, shares: int, purchase_price: int) -> int:
    """Create NPC investment (alias)"""
    result = await invest_in_npc_company(user_id, npc_company_id, shares, purchase_price)
    return result['id']


async def get_player_npc_investment(user_id: str, npc_company_id: int):
    """Get player's investment in NPC company"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM npc_investments
            WHERE user_id = $1 AND npc_company_id = $2
        ''', user_id, npc_company_id)
        return dict(row) if row else None


async def get_player_investments(user_id: str) -> List[Dict]:
    """Get all player investments"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM npc_investments WHERE user_id = $1
        ''', user_id)
        return [dict(row) for row in rows]


async def get_player_npc_investments(user_id: str) -> List[Dict]:
    """Get player NPC investments with company data"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT ni.*, nc.name, nc.rank, nc.current_income, nc.share_price
            FROM npc_investments ni
            JOIN npc_companies nc ON ni.npc_company_id = nc.id
            WHERE ni.user_id = $1
            ORDER BY ni.invested_at DESC
        ''', user_id)
        return [dict(row) for row in rows]


async def get_all_investments() -> List[Dict]:
    """Get all investments"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM npc_investments')
        return [dict(row) for row in rows]


async def update_npc_investment_shares(investment_id: int, new_shares: int):
    """Update investment shares"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE npc_investments SET shares = $1, shares_owned = $1 WHERE id = $2
        ''', new_shares, investment_id)


async def delete_npc_investment(investment_id: int):
    """Delete NPC investment"""
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM npc_investments WHERE id = $1', investment_id)


async def record_dividend_payment(investment_id: int, amount: int):
    """Record dividend payment"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO npc_dividend_payments (investment_id, amount)
            VALUES ($1, $2)
        ''', investment_id, amount)


# ===== HALL OF FAME =====

async def set_hall_of_fame_record(guild_id: str, category: str, user_id: str,
                                   record_value: int, additional_info: str = None):
    """Set Hall of Fame record"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO hall_of_fame (guild_id, category, user_id, record_value, additional_info)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (guild_id, category)
            DO UPDATE SET user_id = $3, record_value = $4, additional_info = $5, achieved_at = CURRENT_TIMESTAMP
        ''', guild_id, category, user_id, record_value, additional_info)


async def get_hall_of_fame_record(guild_id: str, category: str):
    """Get Hall of Fame record"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM hall_of_fame WHERE guild_id = $1 AND category = $2
        ''', guild_id, category)
        return dict(row) if row else None


async def get_guild_hall_of_fame(guild_id: str) -> List[Dict]:
    """Get all Hall of Fame records"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM hall_of_fame WHERE guild_id = $1 ORDER BY achieved_at DESC
        ''', guild_id)
        return [dict(row) for row in rows]


async def record_hall_of_fame_announcement(guild_id: str, user_id: str, category: str):
    """Record Hall of Fame announcement"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO hall_of_fame_announcements (guild_id, user_id, category)
            VALUES ($1, $2, $3)
        ''', guild_id, user_id, category)


async def set_hall_of_fame_channel(guild_id: str, channel_id: str):
    """Set Hall of Fame channel"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, hall_of_fame_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET hall_of_fame_channel_id = $2
        ''', guild_id, channel_id)


# ===== LOANS =====

async def create_loan(borrower_id: str, company_id: Optional[int], principal_amount: int,
                      interest_rate: float, total_owed: int, loan_tier: str,
                      due_date: datetime) -> Dict:
    """Create loan"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO loans 
            (borrower_id, company_id, principal_amount, interest_rate, total_owed, loan_tier, due_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        ''', borrower_id, company_id, principal_amount, interest_rate, total_owed, loan_tier, due_date)
        return dict(row)


async def get_player_loans(user_id: str, unpaid_only: bool = False) -> List[Dict]:
    """Get player loans"""
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
    """Get loan by ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM loans WHERE id = $1', loan_id)
        return dict(row) if row else None


async def pay_loan(loan_id: int) -> Dict:
    """Mark loan as paid"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE loans SET is_paid = TRUE WHERE id = $1 RETURNING *
        ''', loan_id)
        return dict(row) if row else None


async def get_overdue_loans() -> List[Dict]:
    """Get overdue loans"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM loans
            WHERE is_paid = FALSE AND due_date < CURRENT_TIMESTAMP
            ORDER BY due_date
        ''')
        return [dict(row) for row in rows]


async def set_loan_thread(loan_id: int, thread_id: str, embed_message_id: str):
    """Set loan thread"""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE loans SET thread_id = $2, embed_message_id = $3 WHERE id = $1
        ''', loan_id, thread_id, embed_message_id)


# ===== LEADERBOARD =====

async def get_top_players(limit: int = 25, offset: int = 0) -> List[Dict]:
    """Get top players"""
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
    """Get total player count"""
    async with pool.acquire() as conn:
        count = await conn.fetchval('SELECT COUNT(*) FROM players WHERE balance > 0')
        return count or 0


# ===== GUILD SETTINGS =====

async def get_guild_settings(guild_id: str) -> Optional[Dict]:
    """Get guild settings"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM guild_settings WHERE guild_id = $1', guild_id)
        return dict(row) if row else None


async def set_company_forum(guild_id: str, forum_id: str):
    """Set company forum"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, company_forum_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET company_forum_id = $2
        ''', guild_id, forum_id)


async def set_bank_forum(guild_id: str, forum_id: str):
    """Set bank forum"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, bank_forum_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET bank_forum_id = $2
        ''', guild_id, forum_id)


async def set_leaderboard_channel(guild_id: str, channel_id: str, message_id: str):
    """Set leaderboard channel"""
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


async def set_announcements_channel(guild_id: str, channel_id: str):
    """Set announcements channel"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, announcements_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET announcements_channel_id = $2
        ''', guild_id, channel_id)


async def set_achievements_channel(guild_id: str, channel_id: str):
    """Set achievements channel"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, achievements_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET achievements_channel_id = $2
        ''', guild_id, channel_id)


async def set_npc_companies_channel(guild_id: str, channel_id: str, message_id: Optional[str] = None):
    """Set NPC companies channel"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, npc_companies_channel_id, npc_companies_message_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id)
            DO UPDATE SET npc_companies_channel_id = $2, npc_companies_message_id = $3
        ''', guild_id, channel_id, message_id)


async def set_bankruptcy_channel(guild_id: str, channel_id: str):
    """Set bankruptcy channel"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, bankruptcy_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET bankruptcy_channel_id = $2
        ''', guild_id, channel_id)


async def set_registration_settings(guild_id: str, channel_id: str, message_id: str, role_id: str):
    """Set registration settings"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, registration_channel_id, registration_message_id, registration_role_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id)
            DO UPDATE SET registration_channel_id = $2, registration_message_id = $3, registration_role_id = $4
        ''', guild_id, channel_id, message_id, role_id)


async def set_daily_quest_message(guild_id: str, message_id: str):
    """Set daily quest message"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, daily_quest_message_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET daily_quest_message_id = $2
        ''', guild_id, message_id)


async def set_event_frequency(guild_id: str, hours: int):
    """Set event frequency"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, event_frequency_hours)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET event_frequency_hours = $2
        ''', guild_id, hours)


async def get_event_frequency(guild_id: str) -> int:
    """Get event frequency"""
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            'SELECT event_frequency_hours FROM guild_settings WHERE guild_id = $1',
            guild_id
        )
        return result if result is not None else 6


async def set_sabotage_catch_chance(guild_id: str, chance: float):
    """Set sabotage catch chance"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, sabotage_catch_chance)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET sabotage_catch_chance = $2
        ''', guild_id, chance)


async def get_sabotage_catch_chance(guild_id: str) -> float:
    """Get sabotage catch chance"""
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            'SELECT sabotage_catch_chance FROM guild_settings WHERE guild_id = $1',
            guild_id
        )
        return float(result) if result is not None else 0.20


async def set_specialization_cooldown(guild_id: str, hours: int):
    """Set specialization cooldown"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, specialization_cooldown_hours)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET specialization_cooldown_hours = $2
        ''', guild_id, hours)


async def get_specialization_cooldown(guild_id: str) -> int:
    """Get specialization cooldown"""
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            'SELECT specialization_cooldown_hours FROM guild_settings WHERE guild_id = $1',
            guild_id
        )
        return result if result is not None else 24


async def set_admin_roles(guild_id: str, role_ids: List[str]):
    """Set admin roles"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id, admin_role_ids)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET admin_role_ids = $2
        ''', guild_id, role_ids)


async def get_admin_roles(guild_id: str) -> List[str]:
    """Get admin roles"""
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            'SELECT admin_role_ids FROM guild_settings WHERE guild_id = $1',
            guild_id
        )
        return result if result is not None else []


async def add_admin_role(guild_id: str, role_id: str):
    """Add admin role"""
    current_roles = await get_admin_roles(guild_id)
    if role_id not in current_roles:
        current_roles.append(role_id)
        await set_admin_roles(guild_id, current_roles)


async def remove_admin_role(guild_id: str, role_id: str):
    """Remove admin role"""
    current_roles = await get_admin_roles(guild_id)
    if role_id in current_roles:
        current_roles.remove(role_id)
        await set_admin_roles(guild_id, current_roles)


async def clear_admin_roles(guild_id: str):
    """Clear admin roles"""
    await set_admin_roles(guild_id, [])


async def set_command_post_restriction(guild_id: str, command_name: str, post_id: str = None):
    """Set command post restriction"""
    column_name = f'{command_name}_post_id'
    
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guild_settings (guild_id)
            VALUES ($1)
            ON CONFLICT (guild_id) DO NOTHING
        ''', guild_id)
        
    ALLOWED_COLUMNS = {'create_company_post_id', 'request_loan_post_id'}
    if column_name not in ALLOWED_COLUMNS:
        raise ValueError(f"Invalid column name: {column_name}")
    
    await conn.execute(query, guild_id, post_id)


async def get_command_post_restriction(guild_id: str, command_name: str) -> Optional[str]:
    """Get command post restriction"""
    if not pool:
        return None
    column_name = f'{command_name}_post_id'
    
    async with pool.acquire() as conn:
        query = f'SELECT {column_name} FROM guild_settings WHERE guild_id = $1'
        result = await conn.fetchval(query, guild_id)
        return result


async def health_check() -> Dict[str, Any]:
    """Check database health"""
    if not pool:
        return {"healthy": False, "error": "Pool not initialized"}
    try:
        async with pool.acquire() as conn:
            start_time = datetime.utcnow()
            await conn.execute("SELECT 1")
            end_time = datetime.utcnow()
            latency = (end_time - start_time).total_seconds() * 1000
            return {
                "healthy": True,
                "latency_ms": latency,
                "pool_size": pool.get_size(),
                "pool_min": pool.get_min_size(),
                "pool_max": pool.get_max_size()
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"healthy": False, "error": str(e)}


async def cleanup_old_data() -> Dict[str, Any]:
    """Clean up old logs and expired data"""
    if not pool:
        return {"success": False, "error": "Pool not initialized"}
    
    results = {}
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Cleanup old company events
            deleted_events = await conn.execute('''
                DELETE FROM company_events 
                WHERE occurred_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
            ''')
            results['events_cleaned'] = deleted_events
            
            # Cleanup expired black market effects
            deleted_effects = await conn.execute('''
                DELETE FROM black_market_effects 
                WHERE expires_at < CURRENT_TIMESTAMP
            ''')
            results['effects_cleaned'] = deleted_effects
            
            # Cleanup completed daily quests older than 30 days
            deleted_quests = await conn.execute('''
                DELETE FROM daily_quests 
                WHERE quest_date < (CURRENT_DATE - INTERVAL '30 days')
            ''')
            results['quests_cleaned'] = deleted_quests
            
    return {"success": True, "results": results}


async def reset_server_data(guild_id: str) -> Dict:
    """Reset all server game data - DANGEROUS!
    
    This removes:
    - All companies
    - All corporations and members
    - All corporation wars
    - All loans
    - All company raids
    - All mega projects
    - All hall of fame records
    - All server events
    - All NPC investments
    - All achievements
    
    Returns a dict with counts of deleted items
    """
    async with pool.acquire() as conn:
        stats = {}
        
        # Count before deleting
        stats['companies'] = await conn.fetchval(
            'SELECT COUNT(*) FROM companies WHERE guild_id = $1', guild_id
        ) or 0
        
        stats['corporations'] = await conn.fetchval(
            'SELECT COUNT(*) FROM corporations WHERE guild_id = $1', guild_id
        ) or 0
        
        stats['wars'] = await conn.fetchval('''
            SELECT COUNT(*) FROM corporation_wars cw
            JOIN corporations c ON cw.attacker_corp_id = c.id
            WHERE c.guild_id = $1
        ''', guild_id) or 0
        
        stats['loans'] = await conn.fetchval(
            'SELECT COUNT(*) FROM loans WHERE guild_id = $1', guild_id
        ) or 0
        
        stats['raids'] = await conn.fetchval('''
            SELECT COUNT(*) FROM company_raids cr
            JOIN companies c ON cr.attacker_company_id = c.id
            WHERE c.guild_id = $1
        ''', guild_id) or 0
        
        stats['mega_projects'] = await conn.fetchval(
            'SELECT COUNT(*) FROM mega_projects WHERE guild_id = $1', guild_id
        ) or 0
        
        stats['hall_of_fame'] = await conn.fetchval(
            'SELECT COUNT(*) FROM hall_of_fame WHERE guild_id = $1', guild_id
        ) or 0
        
        # Delete in correct order (respecting foreign keys)
        
        # Delete company-related data first
        await conn.execute('''
            DELETE FROM company_raids WHERE attacker_company_id IN (
                SELECT id FROM companies WHERE guild_id = $1
            )
        ''', guild_id)
        
        await conn.execute('''
            DELETE FROM company_assets WHERE company_id IN (
                SELECT id FROM companies WHERE guild_id = $1
            )
        ''', guild_id)
        
        await conn.execute('''
            DELETE FROM espionage_missions WHERE target_company_id IN (
                SELECT id FROM companies WHERE guild_id = $1
            )
        ''', guild_id)
        
        # Delete corporation wars
        await conn.execute('''
            DELETE FROM corporation_wars WHERE attacker_corp_id IN (
                SELECT id FROM corporations WHERE guild_id = $1
            )
        ''', guild_id)
        
        # Delete corporation members
        await conn.execute('''
            DELETE FROM corporation_members WHERE corporation_id IN (
                SELECT id FROM corporations WHERE guild_id = $1
            )
        ''', guild_id)
        
        # Delete corporations
        await conn.execute('DELETE FROM corporations WHERE guild_id = $1', guild_id)
        
        # Delete companies
        await conn.execute('DELETE FROM companies WHERE guild_id = $1', guild_id)
        
        # Delete loans
        await conn.execute('DELETE FROM loans WHERE guild_id = $1', guild_id)
        
        # Delete mega projects
        await conn.execute('DELETE FROM mega_projects WHERE guild_id = $1', guild_id)
        
        # Delete hall of fame
        await conn.execute('DELETE FROM hall_of_fame WHERE guild_id = $1', guild_id)
        await conn.execute('DELETE FROM hall_of_fame_announcements WHERE guild_id = $1', guild_id)
        
        # Delete server events
        await conn.execute('DELETE FROM server_events WHERE guild_id = $1', guild_id)
        
        # Delete NPC investments (if table exists)
        try:
            await conn.execute('''
                DELETE FROM npc_investments WHERE player_id IN (
                    SELECT user_id FROM players WHERE guild_id = $1
                )
            ''', guild_id)
        except:
            pass  # Table might not exist
        
        # Delete achievements for guild players (if table exists)
        try:
            await conn.execute('''
                DELETE FROM player_achievements WHERE player_id IN (
                    SELECT user_id FROM players WHERE guild_id = $1
                )
            ''', guild_id)
        except:
            pass  # Table might not exist
        
        return stats


__all__ = [
    # Connection
    'init_database',
    'close_database',
    
    # Players
    'get_player',
    'upsert_player',
    'register_player',
    'update_player_balance',
    'set_loan_notifications',
    'get_player_stats',
    
    # Companies
    'create_company',
    'get_company_by_id',
    'get_companies_by_owner',
    'get_company_by_thread',
    'set_company_thread',
    'update_company_income',
    'set_company_income',
    'modify_company_income',
    'update_company_specialization',
    'delete_company',
    'get_all_companies',
    'get_guild_companies_by_rank',
    
    # Company Assets
    'add_company_asset',
    'get_company_assets',
    
    # Company Mergers
    'merge_companies',
    'get_player_mergers',
    
    # Events
    'log_company_event',
    'get_company_events',
    'get_company_event_history',
    
    # Server Events
    'create_server_event',
    'get_active_server_events',
    'end_server_event',
    
    # Achievements
    'grant_achievement',
    'get_player_achievements',
    'has_achievement',
    
    # Daily Quests
    'create_daily_quests',
    'get_daily_quests',
    'update_quest_progress',
    'get_quest_progress',
    
    # Black Market
    'log_black_market_purchase',
    'record_black_market_purchase',
    'get_black_market_purchases',
    'add_black_market_effect',
    'get_black_market_effect',
    'consume_black_market_effect',
    
    # Sabotage
    'create_sabotage_action',
    'record_sabotage_operation',
    'get_ready_sabotage_actions',
    'execute_sabotage_action',
    
    # Espionage
    'record_espionage_mission',
    
    # Company Raids
    'record_company_raid',
    'create_company_battle',
    'resolve_company_battle',
    'get_recent_raid',
    'get_company_raid_history',
    'get_active_company_battles',
    
    # Mega Projects
    'create_mega_project',
    'get_active_mega_projects',
    'get_mega_projects_by_rank',
    'get_completed_mega_projects',
    
    # Corporations
    'create_corporation',
    'get_corporation',
    'get_corporation_by_id',
    'get_corporation_by_name',
    'get_corporation_by_tag',
    'get_player_corporation',
    'add_corporation_member',
    'remove_corporation_member',
    'get_corporation_member',
    'get_corporation_members',
    'get_corporation_member_count',
    'add_to_corporation_treasury',
    'delete_corporation',
    'get_all_corporations',
    'get_guild_corporations',
    'get_corporation_stats',
    
    # Corporation Wars
    'create_corporation_war',
    'create_corporation_battle',
    'resolve_corporation_battle',
    'get_active_corporation_war',
    'get_active_corporation_wars',
    
    # NPC Companies
    'create_npc_company',
    'get_npc_company',
    'get_npc_company_by_id',
    'get_npc_company_by_key',
    'get_npc_company_by_name',
    'get_all_npc_companies',
    'get_guild_npc_companies',
    'update_npc_company_value',
    'update_npc_company_income',
    
    # NPC Investments
    'invest_in_npc_company',
    'create_npc_investment',
    'get_player_npc_investment',
    'get_player_investments',
    'get_player_npc_investments',
    'get_all_investments',
    'update_npc_investment_shares',
    'delete_npc_investment',
    'record_dividend_payment',
    
    # Hall of Fame
    'set_hall_of_fame_record',
    'get_hall_of_fame_record',
    'get_guild_hall_of_fame',
    'record_hall_of_fame_announcement',
    'set_hall_of_fame_channel',
    
    # Loans
    'create_loan',
    'get_player_loans',
    'get_loan_by_id',
    'pay_loan',
    'get_overdue_loans',
    'set_loan_thread',
    
    # Leaderboard
    'get_top_players',
    'get_total_player_count',
    
    # Guild Settings
    'get_guild_settings',
    'set_company_forum',
    'set_bank_forum',
    'set_leaderboard_channel',
    'upsert_guild_leaderboard',
    'set_announcements_channel',
    'set_achievements_channel',
    'set_npc_companies_channel',
    'set_bankruptcy_channel',
    'set_registration_settings',
    'set_daily_quest_message',
    'set_event_frequency',
    'get_event_frequency',
    'set_sabotage_catch_chance',
    'get_sabotage_catch_chance',
    'set_specialization_cooldown',
    'get_specialization_cooldown',
    'set_admin_roles',
    'get_admin_roles',
    'add_admin_role',
    'remove_admin_role',
    'clear_admin_roles',
    'set_command_post_restriction',
    'get_command_post_restriction',
    'health_check',
    'reset_server_data',
]

logger.info(f"✅ Database module loaded - {len(__all__)} functions available")
