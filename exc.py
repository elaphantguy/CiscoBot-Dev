

class BotException(Exception):
    """Base Exception for the bot"""

class ModuleInitFailed(BotException):
    """Raised when module fail init"""

class BusyException(BotException):
    """Raised when a second instance of unique class try to be created"""

class InvalidArgs(BotException):
    """represent a error when a user type wrongly a command"""

class NotFound(BotException):
    """NotFound"""

class Forbidden(BotException):
    """Forbidden"""

class ALEDException(BotException):
    """Exception occured by a error in bot implementation"""

class Timeout(BotException):
    """Exception occured when a player don't interact in time"""

class AntiRelouException(BotException):
    """Exception raise when a relou want to use the bot"""

### DATABASE EXCEPTION ###

class DatabaseException(Exception):
    ...

class AlreadyExist(DatabaseException):
    ...