import enum


class MembershipRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class ProjectStatus(str, enum.Enum):
    CREATED = "CREATED"
    CONNECTING = "CONNECTING"
    READY = "READY"
    ERROR = "ERROR"


class IntegrationProvider(str, enum.Enum):
    GITHUB = "GITHUB"


class IntegrationStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class SnapshotStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    CLONING = "CLONING"
    SCANNING = "SCANNING"
    PARSING = "PARSING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SymbolType(str, enum.Enum):
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    INTERFACE = "INTERFACE"
    TYPE = "TYPE"
    ENUM = "ENUM"
    MODULE = "MODULE"


class DependencyType(str, enum.Enum):
    IMPORT = "IMPORT"
    REQUIRE = "REQUIRE"
    FROM_IMPORT = "FROM_IMPORT"
