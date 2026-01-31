# Bot maintenance and shutdown system

# Global state for bot maintenance
_bot_shutdown = False

def is_bot_shutdown() -> bool:
    """Check if bot is in shutdown/maintenance mode"""
    global _bot_shutdown
    return _bot_shutdown

def set_bot_shutdown(shutdown: bool):
    """Set bot shutdown/maintenance state"""
    global _bot_shutdown
    _bot_shutdown = shutdown

def get_shutdown_message() -> str:
    """Get the message to show when bot is shutdown"""
    return (
        "🔧 **Bot in Maintenance Mode**\n\n"
        "The bot is currently shut down for maintenance or updates.\n"
        "You can still browse and plan, but actions won't be finalized.\n\n"
        "Please wait for an admin to restart the bot's functions."
    )
