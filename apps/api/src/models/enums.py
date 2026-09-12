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
