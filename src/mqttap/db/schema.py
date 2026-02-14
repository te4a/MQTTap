from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    JSON,
    String,
    Table,
    Text,
    func,
)

metadata = MetaData()

roles = Table(
    "roles",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(50), unique=True, nullable=False),
)

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(255), unique=True, nullable=False),
    Column("email", String(255), unique=True, nullable=True),
    Column("password_hash", String(255), nullable=False),
    Column("role_id", Integer, nullable=False),
    Column("email_verified", Boolean, nullable=False, server_default="false"),
    Column("max_points", Integer, nullable=False, server_default="5000"),
    Column("allowed_topics", JSON, nullable=True),
    Column("allowed_signals", JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

settings = Table(
    "settings",
    metadata,
    Column("key", String(100), primary_key=True),
    Column("value", Text, nullable=False),
    Column("type", String(30), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
)

topic_registry = Table(
    "topic_registry",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("topic", String(255), unique=True, nullable=False),
    Column("table_name", String(255), unique=True, nullable=False),
    Column("is_json", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

user_charts = Table(
    "user_charts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("name", String(255), nullable=True),
    Column("config", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

invites = Table(
    "invites",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("code", String(64), unique=True, nullable=False),
    Column("role_name", String(50), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("is_single_use", Boolean, nullable=False, server_default="false"),
    Column("created_by", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
)
