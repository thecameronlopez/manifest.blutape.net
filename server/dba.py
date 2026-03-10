from sqlalchemy import inspect, text

from app import create_app
from app.models import Base
from app.extensions import db

app = create_app()


def _column_names(inspector, table_name):
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name):
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _add_missing_columns(connection, inspector):
    manifest_columns = _column_names(inspector, "manifests")
    machine_columns = _column_names(inspector, "machines")
    dialect = connection.dialect.name

    manifest_ddls = {
        "manifest_kind": "ALTER TABLE manifests ADD COLUMN manifest_kind VARCHAR(32) NOT NULL DEFAULT 'truck_upload'",
        "source_system": "ALTER TABLE manifests ADD COLUMN source_system VARCHAR(50) NULL",
        "source_date": "ALTER TABLE manifests ADD COLUMN source_date DATE NULL",
    }
    machine_ddls = {
        "entry_kind": "ALTER TABLE machines ADD COLUMN entry_kind VARCHAR(32) NOT NULL DEFAULT 'inventory'",
        "source_machine_id": "ALTER TABLE machines ADD COLUMN source_machine_id INTEGER NULL",
        "source_work_order_id": "ALTER TABLE machines ADD COLUMN source_work_order_id INTEGER NULL",
        "source_event_id": "ALTER TABLE machines ADD COLUMN source_event_id INTEGER NULL",
        "serial": "ALTER TABLE machines ADD COLUMN serial VARCHAR(150) NULL",
        "brand": "ALTER TABLE machines ADD COLUMN brand VARCHAR(100) NULL",
        "model": "ALTER TABLE machines ADD COLUMN model VARCHAR(100) NULL",
        "vendor": "ALTER TABLE machines ADD COLUMN vendor VARCHAR(100) NULL",
        "condition": "ALTER TABLE machines ADD COLUMN `condition` VARCHAR(50) NULL"
        if dialect == "mysql"
        else "ALTER TABLE machines ADD COLUMN condition VARCHAR(50) NULL",
        "color": "ALTER TABLE machines ADD COLUMN color VARCHAR(50) NULL",
        "form_factor": "ALTER TABLE machines ADD COLUMN form_factor VARCHAR(100) NULL",
        "completed_on": "ALTER TABLE machines ADD COLUMN completed_on DATE NULL",
    }

    for column_name, ddl in manifest_ddls.items():
        if column_name not in manifest_columns:
            connection.execute(text(ddl))

    for column_name, ddl in machine_ddls.items():
        if column_name not in machine_columns:
            connection.execute(text(ddl))


def _add_missing_indexes(connection, inspector):
    manifest_indexes = _index_names(inspector, "manifests")
    machine_indexes = _index_names(inspector, "machines")

    manifest_index_ddls = {
        "ix_manifests_manifest_kind": "CREATE INDEX ix_manifests_manifest_kind ON manifests (manifest_kind)",
        "ix_manifests_source_system": "CREATE INDEX ix_manifests_source_system ON manifests (source_system)",
        "ix_manifests_source_date": "CREATE INDEX ix_manifests_source_date ON manifests (source_date)",
    }
    machine_index_ddls = {
        "ix_machines_entry_kind": "CREATE INDEX ix_machines_entry_kind ON machines (entry_kind)",
        "ix_machines_source_machine_id": "CREATE INDEX ix_machines_source_machine_id ON machines (source_machine_id)",
        "ix_machines_source_work_order_id": "CREATE INDEX ix_machines_source_work_order_id ON machines (source_work_order_id)",
        "ix_machines_source_event_id": "CREATE INDEX ix_machines_source_event_id ON machines (source_event_id)",
        "ix_machines_serial": "CREATE INDEX ix_machines_serial ON machines (serial)",
        "ix_machines_vendor": "CREATE INDEX ix_machines_vendor ON machines (vendor)",
        "ix_machines_completed_on": "CREATE INDEX ix_machines_completed_on ON machines (completed_on)",
    }

    for index_name, ddl in manifest_index_ddls.items():
        if index_name not in manifest_indexes:
            connection.execute(text(ddl))

    for index_name, ddl in machine_index_ddls.items():
        if index_name not in machine_indexes:
            connection.execute(text(ddl))


def _relax_machine_price_nullability(connection):
    dialect = connection.dialect.name
    if dialect == "mysql":
        connection.execute(text("ALTER TABLE machines MODIFY COLUMN msrp INTEGER NULL"))
        connection.execute(text("ALTER TABLE machines MODIFY COLUMN your_cost INTEGER NULL"))
        return
    if dialect == "sqlite":
        print("SQLite detected: msrp/your_cost nullability change requires a table rebuild and was skipped.")
        return

    print(f"Unsupported dialect for nullability migration: {dialect}. Skipped msrp/your_cost alteration.")


def migrate_completed_manifest_schema():
    try:
        with app.app_context():
            Base.metadata.create_all(bind=db.engine)
            with db.engine.begin() as connection:
                inspector = inspect(connection)
                _add_missing_columns(connection, inspector)
                inspector = inspect(connection)
                _add_missing_indexes(connection, inspector)
                _relax_machine_price_nullability(connection)
        print("Completed-manifest schema migration finished.")
    except Exception as e:
        print(f"[ERROR]: {e}")


def start():
    try:
        with app.app_context():
            Base.metadata.create_all(bind=db.engine)
        print("DB started!")
    except Exception as e:
        print(f"[ERROR]: {e}")


def restart():
    try:
        with app.app_context():
            Base.metadata.drop_all(bind=db.engine)
            Base.metadata.create_all(bind=db.engine)
        print("DB reset")
    except Exception as e:
        print(f"[ERROR]: {e}")
