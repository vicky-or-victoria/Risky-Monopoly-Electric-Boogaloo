# Database connection and operations using asyncpg for Neon PostgreSQL - COMPLETE REWRITE

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
        statement_cache_size=0,  # Disable statement caching to prevent "plan is invalid" errors
        max_inactive_connection_lifetime=300  # Recycle connections after 5 minutes of inactivity
    )
    
    async with pool.acquire() as conn:
        async with conn.transaction():
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
            
            # Companies table - WITH embed_message_id
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
            
            # Loans table - WITH loan_tier and embed_message_id
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
            
            # Guild settings table - WITH admin_role_ids AND post restrictions
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Migration: Add columns if they don't exist (for existing databases)
            
            # Add event_frequency_hours column
            try:
                await conn.execute('''
                    ALTER TABLE guild_settings 
                    ADD COLUMN IF NOT EXISTS event_frequency_hours INTEGER DEFAULT 6
                ''')
            except Exception as e:
                print(f"Note: event_frequency_hours column: {e}")
            
            # Add admin_role_ids column
            try:
                await conn.execute('''
                    ALTER TABLE guild_settings 
                    ADD COLUMN IF NOT EXISTS admin_role_ids TEXT[]
                ''')
            except Exception as e:
                print(f"Note: admin_role_ids column: {e}")
            
            # Add post restriction columns
            try:
                await conn.execute('''
                    ALTER TABLE guild_settings 
                    ADD COLUMN IF NOT EXISTS create_company_post_id VARCHAR(255)
                ''')
            except Exception as e:
                print(f"Note: create_company_post_id column: {e}")
            
            try:
                await conn.execute('''
                    ALTER TABLE guild_settings 
                    ADD COLUMN IF NOT EXISTS request_loan_post_id VARCHAR(255)
                ''')
            except Exception as e:
                print(f"Note: request_loan_post_id column: {e}")
            
            # Add loan_tier column to loans
            try:
                await conn.execute('''
                    ALTER TABLE loans 
                    ADD COLUMN IF NOT EXISTS loan_tier VARCHAR(10)
                ''')
                # Set default value for existing rows
                await conn.execute('''
                    UPDATE loans 
                    SET loan_tier = 'F' 
                    WHERE loan_tier IS NULL
                ''')
            except Exception as e:
                print(f"Note: loan_tier column: {e}")
            
            # Add embed_message_id column to loans
            try:
                await conn.execute('''
                    ALTER TABLE loans 
                    ADD COLUMN IF NOT EXISTS embed_message_id VARCHAR(255)
                ''')
            except Exception as e:
                print(f"Note: loans embed_message_id column: {e}")
    
    print('✅ Database initialized successfully')

async def close_database():
    """Close database connection pool"""
    global pool
    if pool:
        await pool.close()


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
    """Update player balance by adding/subtracting amount"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE players
            SET balance = balance + $2, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1
            RETURNING *
        ''', user_id, amount)
        result = dict(row) if row else None
        
        # Trigger auto-updates
        if result:
            try:
                from auto_updates import trigger_updates_for_balance_change
                import asyncio
                asyncio.create_task(trigger_updates_for_balance_change(user_id))
            except:
                pass
        
        return result

async def set_player_balance(user_id: str, amount: int) -> Dict:
    """Set player balance to a specific amount"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE players
            SET balance = $2, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = $1
            RETURNING *
        ''', user_id, amount)
        result = dict(row) if row else None
        
        # Trigger auto-updates
        if result:
            try:
                from auto_updates import trigger_updates_for_balance_change
                import asyncio
                asyncio.create_task(trigger_updates_for_balance_change(user_id))
            except:
                pass
        
        return result


async def create_company(owner_id: str, name: str, rank: str, company_type: str,
                        base_income: int, thread_id: str = None, 
                        embed_message_id: str = None) -> Dict:
    """Create a new company"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO companies (owner_id, name, rank, type, base_income, current_income, 
                                 reputation, thread_id, embed_message_id)
            VALUES ($1, $2, $3, $4, $5, $5, 50, $6, $7)
            RETURNING *
        ''', owner_id, name, rank, company_type, base_income, thread_id, embed_message_id)
        return dict(row)

async def get_company_by_id(company_id: int) -> Optional[Dict]:
    """Get a company by ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM companies WHERE id = $1', company_id)
        return dict(row) if row else None

async def get_company_by_thread(thread_id: str) -> Optional[Dict]:
    """Get a company by its thread ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM companies WHERE thread_id = $1', thread_id)
        return dict(row) if row else None

async def get_player_companies(user_id: str) -> List[Dict]:
    """Get all companies owned by a player"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM companies 
            WHERE owner_id = $1 
            ORDER BY created_at DESC
        ''', user_id)
        return [dict(row) for row in rows]

async def get_all_companies() -> List[Dict]:
    """Get all companies"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM companies ORDER BY id')
        return [dict(row) for row in rows]

async def update_company_income(company_id: int, income_change: int) -> Dict:
    """Update company income (ensures it doesn't go below 0)"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE companies
            SET current_income = GREATEST(0, current_income + $2),
                last_event_at = CURRENT_TIMESTAMP
            WHERE id = $1
            RETURNING *
        ''', company_id, income_change)
        result = dict(row) if row else None
        
        # Trigger auto-updates
        if result:
            try:
                from auto_updates import trigger_updates_for_company_change
                import asyncio
                asyncio.create_task(trigger_updates_for_company_change(company_id))
            except:
                pass
        
        return result

async def delete_company(company_id: int):
    """Delete a company"""
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM companies WHERE id = $1', company_id)

async def rename_company(company_id: int, new_name: str) -> Dict:
    """Rename a company"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE companies
            SET name = $2
            WHERE id = $1
            RETURNING *
        ''', company_id, new_name)
        return dict(row) if row else None

async def update_company_embed_id(company_id: int, embed_message_id: str) -> Dict:
    """Update company's embed message ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE companies
            SET embed_message_id = $2
            WHERE id = $1
            RETURNING *
        ''', company_id, embed_message_id)
        return dict(row) if row else None


async def add_company_asset(company_id: int, asset_name: str, asset_type: str,
                           income_boost: int, cost: int) -> Dict:
    """Add an asset to a company and update its income"""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Add the asset
            asset_row = await conn.fetchrow('''
                INSERT INTO company_assets (company_id, asset_name, asset_type, income_boost, cost)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
            ''', company_id, asset_name, asset_type, income_boost, cost)
            
            # Update company income
            company_row = await conn.fetchrow('''
                UPDATE companies
                SET current_income = current_income + $2
                WHERE id = $1
                RETURNING *
            ''', company_id, income_boost)
            
            # Trigger auto-updates
            try:
                from auto_updates import trigger_updates_for_company_change
                import asyncio
                asyncio.create_task(trigger_updates_for_company_change(company_id))
            except:
                pass
            
            return dict(asset_row)

async def get_company_assets(company_id: int) -> List[Dict]:
    """Get all assets for a company"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM company_assets 
            WHERE company_id = $1 
            ORDER BY purchased_at DESC
        ''', company_id)
        return [dict(row) for row in rows]


async def log_company_event(company_id: int, event_type: str, description: str,
                            income_change: int) -> Dict:
    """Log a company event"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO company_events (company_id, event_type, event_description, income_change)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        ''', company_id, event_type, description, income_change)
        return dict(row)

async def get_company_events(company_id: int, limit: int = 20) -> List[Dict]:
    """Get recent events for a company"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM company_events
            WHERE company_id = $1
            ORDER BY occurred_at DESC
            LIMIT $2
        ''', company_id, limit)
        return [dict(row) for row in rows]


async def create_loan(borrower_id: str, company_id: Optional[int], principal: int,
                     interest_rate: float, due_days: int, loan_tier: str, 
                     thread_id: str, embed_message_id: str = None) -> Dict:
    """Create a new loan"""
    total_owed = int(principal * (1 + interest_rate / 100))
    due_date = datetime.now() + timedelta(days=due_days)
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO loans (borrower_id, company_id, principal_amount, interest_rate, 
                             total_owed, loan_tier, due_date, thread_id, embed_message_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        ''', borrower_id, company_id, principal, interest_rate, total_owed, loan_tier, due_date, thread_id, embed_message_id)
        return dict(row)

async def update_loan_embed_id(loan_id: int, embed_message_id: str) -> Dict:
    """Update loan's embed message ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            UPDATE loans
            SET embed_message_id = $2
            WHERE id = $1
            RETURNING *
        ''', loan_id, embed_message_id)
        return dict(row) if row else None

async def get_player_loans(user_id: str, unpaid_only: bool = True) -> List[Dict]:
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

# Alias for backwards compatibility
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
        return result if result is not None else 6  # Default 6 hours


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
    async with pool.acquire() as conn:
        # Get current roles
        current_roles = await get_admin_roles(guild_id)
        
        # Add new role if not already present
        if role_id not in current_roles:
            current_roles.append(role_id)
            await set_admin_roles(guild_id, current_roles)

async def remove_admin_role(guild_id: str, role_id: str):
    """Remove a single admin role from a guild"""
    async with pool.acquire() as conn:
        # Get current roles
        current_roles = await get_admin_roles(guild_id)
        
        # Remove role if present
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
        # First ensure guild settings exist
        await conn.execute('''
            INSERT INTO guild_settings (guild_id)
            VALUES ($1)
            ON CONFLICT (guild_id) DO NOTHING
        ''', guild_id)
        
        # Then update the specific post restriction using dynamic query
        # Note: Using string formatting here is safe because column_name is controlled by us
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
        # Using string formatting here is safe because column_name is controlled by us
        query = f'SELECT {column_name} FROM guild_settings WHERE guild_id = $1'
        result = await conn.fetchval(query, guild_id)
        return result
