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


class FindingCategory(str, enum.Enum):
    UNUSED_CODE = "UNUSED_CODE"
    COUPLING = "COUPLING"
    DOCUMENTATION_GAP = "DOCUMENTATION_GAP"
    DUPLICATION = "DUPLICATION"
    ARCHITECTURE = "ARCHITECTURE"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    CHANGE_RISK = "CHANGE_RISK"
    LEGACY = "LEGACY"
    TEST_GAP = "TEST_GAP"


class FindingSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingConfidence(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class DiscoveryJobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class KnowledgeClass(str, enum.Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    CUSTOMER = "CUSTOMER"
    RECOMMENDED = "RECOMMENDED"


class KnowledgeCategory(str, enum.Enum):
    INTENT = "INTENT"
    BUSINESS_RULE = "BUSINESS_RULE"
    ARCHITECTURE_DECISION = "ARCHITECTURE_DECISION"
    EXCEPTION = "EXCEPTION"
    CONSTRAINT = "CONSTRAINT"
    LEGACY_CONTEXT = "LEGACY_CONTEXT"
    CRITICAL_COMPONENT = "CRITICAL_COMPONENT"
    TEMPORARY_STATE = "TEMPORARY_STATE"
    OTHER = "OTHER"


class KnowledgeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


