"""using uuids instead of ids

Revision ID: 0373eaa00528
Revises: 4a1135ae4cfe
Create Date: 2026-03-14 04:50:48.106838

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0373eaa00528"
down_revision: Union[str, Sequence[str], None] = "4a1135ae4cfe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Truncate all tables — integer FK values cannot be meaningfully mapped to UUIDs.
    # Safe for dev; in production a proper data migration would be required.
    op.execute(
        'TRUNCATE TABLE memory_log, chat_message, memory_structured, chat, "user" CASCADE'
    )

    # Drop FK constraints (most-dependent tables first)
    op.drop_constraint("memory_log_user_id_fkey", "memory_log", type_="foreignkey")
    op.drop_constraint("memory_log_message_id_fkey", "memory_log", type_="foreignkey")
    op.drop_constraint("chat_message_chat_id_fkey", "chat_message", type_="foreignkey")
    op.drop_constraint(
        "memory_structured_superseded_by_fkey", "memory_structured", type_="foreignkey"
    )
    op.drop_constraint(
        "memory_structured_user_id_fkey", "memory_structured", type_="foreignkey"
    )
    op.drop_constraint("chat_user_id_fkey", "chat", type_="foreignkey")

    # Drop partial unique index (references superseded_by column)
    op.drop_index("idx_active_memory_unique", table_name="memory_structured")

    # Drop integer sequences / serial defaults from PK columns
    op.execute('ALTER TABLE "user" ALTER COLUMN id DROP DEFAULT')
    op.execute("ALTER TABLE chat ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE chat_message ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE memory_structured ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE memory_log ALTER COLUMN id DROP DEFAULT")

    # Change PK columns to UUID
    op.execute('ALTER TABLE "user" ALTER COLUMN id TYPE uuid USING gen_random_uuid()')
    op.execute("ALTER TABLE chat ALTER COLUMN id TYPE uuid USING gen_random_uuid()")
    op.execute(
        "ALTER TABLE chat_message ALTER COLUMN id TYPE uuid USING gen_random_uuid()"
    )
    op.execute(
        "ALTER TABLE memory_structured ALTER COLUMN id TYPE uuid USING gen_random_uuid()"
    )
    op.execute(
        "ALTER TABLE memory_log ALTER COLUMN id TYPE uuid USING gen_random_uuid()"
    )

    # Change FK columns to UUID
    op.execute(
        "ALTER TABLE chat ALTER COLUMN user_id TYPE uuid USING gen_random_uuid()"
    )
    op.execute(
        "ALTER TABLE chat_message ALTER COLUMN chat_id TYPE uuid USING gen_random_uuid()"
    )
    op.execute(
        "ALTER TABLE memory_structured ALTER COLUMN user_id TYPE uuid USING gen_random_uuid()"
    )
    op.execute(
        "ALTER TABLE memory_structured ALTER COLUMN superseded_by TYPE uuid USING NULL::uuid"
    )
    op.execute(
        "ALTER TABLE memory_log ALTER COLUMN user_id TYPE uuid USING gen_random_uuid()"
    )
    op.execute(
        "ALTER TABLE memory_log ALTER COLUMN message_id TYPE uuid USING gen_random_uuid()"
    )

    # Set gen_random_uuid() as default for all PK columns
    op.execute('ALTER TABLE "user" ALTER COLUMN id SET DEFAULT gen_random_uuid()')
    op.execute("ALTER TABLE chat ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE chat_message ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute(
        "ALTER TABLE memory_structured ALTER COLUMN id SET DEFAULT gen_random_uuid()"
    )
    op.execute("ALTER TABLE memory_log ALTER COLUMN id SET DEFAULT gen_random_uuid()")

    # Re-create FK constraints
    op.create_foreign_key(None, "chat", "user", ["user_id"], ["id"])
    op.create_foreign_key(None, "chat_message", "chat", ["chat_id"], ["id"])
    op.create_foreign_key(None, "memory_structured", "user", ["user_id"], ["id"])
    op.create_foreign_key(
        None, "memory_structured", "memory_structured", ["superseded_by"], ["id"]
    )
    op.create_foreign_key(None, "memory_log", "user", ["user_id"], ["id"])
    op.create_foreign_key(None, "memory_log", "chat_message", ["message_id"], ["id"])

    # Re-create partial unique index
    op.create_index(
        "idx_active_memory_unique",
        "memory_structured",
        ["user_id", "key"],
        unique=True,
        postgresql_where=sa.text("superseded_by IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Truncate all tables — UUID values cannot be cast back to integers.
    op.execute(
        'TRUNCATE TABLE memory_log, chat_message, memory_structured, chat, "user" CASCADE'
    )

    # Drop FK constraints
    op.drop_constraint("memory_log_user_id_fkey", "memory_log", type_="foreignkey")
    op.drop_constraint("memory_log_message_id_fkey", "memory_log", type_="foreignkey")
    op.drop_constraint("chat_message_chat_id_fkey", "chat_message", type_="foreignkey")
    op.drop_constraint(
        "memory_structured_superseded_by_fkey", "memory_structured", type_="foreignkey"
    )
    op.drop_constraint(
        "memory_structured_user_id_fkey", "memory_structured", type_="foreignkey"
    )
    op.drop_constraint("chat_user_id_fkey", "chat", type_="foreignkey")

    op.drop_index("idx_active_memory_unique", table_name="memory_structured")

    # Drop UUID defaults
    op.execute('ALTER TABLE "user" ALTER COLUMN id DROP DEFAULT')
    op.execute("ALTER TABLE chat ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE chat_message ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE memory_structured ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE memory_log ALTER COLUMN id DROP DEFAULT")

    # Change PK columns back to INTEGER
    op.execute('ALTER TABLE "user" ALTER COLUMN id TYPE integer USING 0')
    op.execute("ALTER TABLE chat ALTER COLUMN id TYPE integer USING 0")
    op.execute("ALTER TABLE chat_message ALTER COLUMN id TYPE integer USING 0")
    op.execute("ALTER TABLE memory_structured ALTER COLUMN id TYPE integer USING 0")
    op.execute("ALTER TABLE memory_log ALTER COLUMN id TYPE integer USING 0")

    # Change FK columns back to INTEGER
    op.execute("ALTER TABLE chat ALTER COLUMN user_id TYPE integer USING 0")
    op.execute("ALTER TABLE chat_message ALTER COLUMN chat_id TYPE integer USING 0")
    op.execute(
        "ALTER TABLE memory_structured ALTER COLUMN user_id TYPE integer USING 0"
    )
    op.execute(
        "ALTER TABLE memory_structured ALTER COLUMN superseded_by TYPE integer USING NULL::integer"
    )
    op.execute("ALTER TABLE memory_log ALTER COLUMN user_id TYPE integer USING 0")
    op.execute("ALTER TABLE memory_log ALTER COLUMN message_id TYPE integer USING 0")

    # Restore sequences for PK columns
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS user_id_seq; ALTER TABLE \"user\" ALTER COLUMN id SET DEFAULT nextval('user_id_seq')"
    )
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS chat_id_seq; ALTER TABLE chat ALTER COLUMN id SET DEFAULT nextval('chat_id_seq')"
    )
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS chat_message_id_seq; ALTER TABLE chat_message ALTER COLUMN id SET DEFAULT nextval('chat_message_id_seq')"
    )
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS memory_structured_id_seq; ALTER TABLE memory_structured ALTER COLUMN id SET DEFAULT nextval('memory_structured_id_seq')"
    )
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS memory_log_id_seq; ALTER TABLE memory_log ALTER COLUMN id SET DEFAULT nextval('memory_log_id_seq')"
    )

    # Re-create FK constraints
    op.create_foreign_key(None, "chat", "user", ["user_id"], ["id"])
    op.create_foreign_key(None, "chat_message", "chat", ["chat_id"], ["id"])
    op.create_foreign_key(None, "memory_structured", "user", ["user_id"], ["id"])
    op.create_foreign_key(
        None, "memory_structured", "memory_structured", ["superseded_by"], ["id"]
    )
    op.create_foreign_key(None, "memory_log", "user", ["user_id"], ["id"])
    op.create_foreign_key(None, "memory_log", "chat_message", ["message_id"], ["id"])

    op.create_index(
        "idx_active_memory_unique",
        "memory_structured",
        ["user_id", "key"],
        unique=True,
        postgresql_where=sa.text("superseded_by IS NULL"),
    )
