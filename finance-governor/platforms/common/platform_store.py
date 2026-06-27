"""Durable platform persistence — Postgres when DATABASE_URL set, else in-memory."""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from .platform_metrics import get_platform_counters


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_param(value: dict, dialect: str) -> str | dict:
    raw = json.dumps(value)
    return raw if dialect == "sqlite" else raw


class PlatformStore(ABC):
    @abstractmethod
    def ready(self) -> bool: ...

    @abstractmethod
    def append_event(self, platform: str, event_type: str, operation_id: str, metadata: dict | None = None) -> None: ...

    @abstractmethod
    def reset(self) -> None: ...


class SubledgerStore(PlatformStore):
    @abstractmethod
    def ingest(self, *, txn_hash: str, record: dict) -> bool: ...

    @abstractmethod
    def list_pending_records(self) -> list[dict]: ...

    @abstractmethod
    def mark_matched(self, *, txn_hash: str, mirror_hash: str, fx_hash: str) -> None: ...

    @abstractmethod
    def record_discrepancy(self, *, txn_hash: str, reason: str, metadata: dict) -> None: ...

    @abstractmethod
    def count_pending(self) -> int: ...

    @abstractmethod
    def count_matched(self) -> int: ...

    @abstractmethod
    def list_discrepancies(self, limit: int) -> list[dict]: ...

    @abstractmethod
    def count_orphans(self) -> int: ...


class AssetStore(PlatformStore):
    @abstractmethod
    def register_asset(self, asset: dict) -> None: ...

    @abstractmethod
    def get_asset(self, asset_id: str) -> dict | None: ...

    @abstractmethod
    def list_assets(self) -> list[dict]: ...

    @abstractmethod
    def apply_charge(self, *, asset_id: str, period: str, charge: str, reg_table_version: str, crystal_id: str | None) -> dict | None: ...

    @abstractmethod
    def list_events(self, limit: int) -> list[dict]: ...


class CreditStore(PlatformStore):
    @abstractmethod
    def record_evaluation(self, row: dict) -> bool: ...

    @abstractmethod
    def get_evaluation(self, application_id: str) -> dict | None: ...


# ─── In-memory implementations ───────────────────────────────────────────────


class MemorySubledgerStore(SubledgerStore):
    def __init__(self) -> None:
        self._txns: dict[str, dict] = {}
        self._discrepancies: list[dict] = []
        self._events: list[dict] = []

    def ready(self) -> bool:
        return True

    def reset(self) -> None:
        self._txns.clear()
        self._discrepancies.clear()
        self._events.clear()

    def append_event(self, platform: str, event_type: str, operation_id: str, metadata: dict | None = None) -> None:
        self._events.append(
            {"platform": platform, "event_type": event_type, "operation_id": operation_id, "metadata": metadata or {}}
        )

    def ingest(self, *, txn_hash: str, record: dict) -> bool:
        if txn_hash in self._txns:
            return False
        self._txns[txn_hash] = {**record, "txn_hash": txn_hash, "status": "PENDING"}
        self.append_event("subledger_sync", "TXN_INGESTED", txn_hash, record)
        return True

    def list_pending_records(self) -> list[dict]:
        return [t for t in self._txns.values() if t["status"] == "PENDING"]

    def mark_matched(self, *, txn_hash: str, mirror_hash: str, fx_hash: str) -> None:
        if txn_hash in self._txns:
            self._txns[txn_hash].update({"status": "MATCHED", "mirror_hash": mirror_hash, "fx_hash": fx_hash})
        if mirror_hash in self._txns:
            self._txns[mirror_hash]["status"] = "MATCHED"
        get_platform_counters("subledger_sync").increment("ic_matched_total")
        self.append_event("subledger_sync", "MATCHED", txn_hash, {"mirror_hash": mirror_hash, "fx_hash": fx_hash})

    def record_discrepancy(self, *, txn_hash: str, reason: str, metadata: dict) -> None:
        item = {"txn_hash": txn_hash, "reason": reason, "metadata": metadata, "recorded_at": _utcnow().isoformat()}
        self._discrepancies.append(item)
        if reason == "NO_MIRROR_OR_FX_DRIFT":
            get_platform_counters("subledger_sync").increment("match_tolerance_breach_total")
        self.append_event("subledger_sync", "DISCREPANCY", txn_hash, {"reason": reason, **metadata})

    def count_pending(self) -> int:
        return sum(1 for t in self._txns.values() if t["status"] == "PENDING")

    def count_matched(self) -> int:
        return sum(1 for t in self._txns.values() if t["status"] == "MATCHED") // 2

    def list_discrepancies(self, limit: int) -> list[dict]:
        return list(reversed(self._discrepancies[-limit:]))

    def count_orphans(self) -> int:
        return self.count_pending()


class MemoryAssetStore(AssetStore):
    def __init__(self) -> None:
        self._assets: dict[str, dict] = {}
        self._charges: set[tuple[str, str]] = set()
        self._events: list[dict] = []

    def ready(self) -> bool:
        return True

    def reset(self) -> None:
        self._assets.clear()
        self._charges.clear()
        self._events.clear()

    def append_event(self, platform: str, event_type: str, operation_id: str, metadata: dict | None = None) -> None:
        pass

    def register_asset(self, asset: dict) -> None:
        if Decimal(asset["book_value"]) < 0:
            get_platform_counters("asset_ledger").increment("negative_book_value_total")
            raise ValueError("book value cannot be negative")
        self._assets[asset["asset_id"]] = asset

    def get_asset(self, asset_id: str) -> dict | None:
        return self._assets.get(asset_id)

    def list_assets(self) -> list[dict]:
        return list(self._assets.values())

    def apply_charge(self, *, asset_id: str, period: str, charge: str, reg_table_version: str, crystal_id: str | None) -> dict | None:
        key = (asset_id, period)
        if key in self._charges:
            get_platform_counters("asset_ledger").increment("depreciation_duplicate_blocked_total")
            return None
        asset = self._assets[asset_id]
        charge_d = Decimal(charge)
        charge_d = min(charge_d, Decimal(asset["book_value"]))
        if charge_d <= 0:
            return None
        asset["accumulated_depreciation"] = str(Decimal(asset["accumulated_depreciation"]) + charge_d)
        asset["book_value"] = str(Decimal(asset["book_value"]) - charge_d)
        if Decimal(asset["book_value"]) < 0:
            get_platform_counters("asset_ledger").increment("negative_book_value_total")
        self._charges.add(key)
        row = {
            "asset_id": asset_id,
            "period": period,
            "charge": str(charge_d),
            "book_value": asset["book_value"],
            "reg_table_version": reg_table_version,
            "crystal_id": crystal_id,
        }
        self._events.append(row)
        return row

    def list_events(self, limit: int) -> list[dict]:
        return list(reversed(self._events[-limit:]))


class MemoryCreditStore(CreditStore):
    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}

    def ready(self) -> bool:
        return True

    def reset(self) -> None:
        self._rows.clear()

    def append_event(self, platform: str, event_type: str, operation_id: str, metadata: dict | None = None) -> None:
        pass

    def record_evaluation(self, row: dict) -> bool:
        app_id = row["application_id"]
        if app_id in self._rows:
            return False
        self._rows[app_id] = row
        append_platform_event("credit_govern", "EVALUATED", app_id, row)
        return True

    def get_evaluation(self, application_id: str) -> dict | None:
        return self._rows.get(application_id)


# ─── SQL implementation ──────────────────────────────────────────────────────


class _SqlBase:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @property
    def _dialect(self) -> str:
        return self._engine.dialect.name

    def ready(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def append_event(self, platform: str, event_type: str, operation_id: str, metadata: dict | None = None) -> None:
        meta_json = json.dumps(metadata or {})
        meta_sql = ":metadata" if self._dialect == "sqlite" else "CAST(:metadata AS jsonb)"
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    INSERT INTO platform_events (platform, event_type, operation_id, metadata)
                    VALUES (:platform, :event_type, :operation_id, {meta_sql})
                    """
                ),
                {
                    "platform": platform,
                    "event_type": event_type,
                    "operation_id": operation_id,
                    "metadata": meta_json,
                },
            )


class SqlSubledgerStore(_SqlBase, SubledgerStore):
    def reset(self) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM subledger_transactions"))
            conn.execute(text("DELETE FROM platform_events WHERE platform = 'subledger_sync'"))

    def ingest(self, *, txn_hash: str, record: dict) -> bool:
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO subledger_transactions (
                            txn_hash, entity_id, counterparty_id, amount, currency, value_date, reference, status
                        ) VALUES (
                            :txn_hash, :entity_id, :counterparty_id, :amount, :currency, :value_date, :reference, 'PENDING'
                        )
                        """
                    ),
                    {
                        "txn_hash": txn_hash,
                        "entity_id": record["entity_id"],
                        "counterparty_id": record["counterparty_id"],
                        "amount": record["amount"],
                        "currency": record["currency"],
                        "value_date": record["value_date"],
                        "reference": record.get("reference", ""),
                    },
                )
            self.append_event("subledger_sync", "TXN_INGESTED", txn_hash, record)
            return True
        except Exception:
            return False

    def list_pending_records(self) -> list[dict]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM subledger_transactions WHERE status = 'PENDING' ORDER BY recorded_at")
            ).mappings().all()
        return [dict(r) for r in rows]

    def mark_matched(self, *, txn_hash: str, mirror_hash: str, fx_hash: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE subledger_transactions
                    SET status = 'MATCHED', mirror_hash = :mirror_hash, fx_hash = :fx_hash
                    WHERE txn_hash IN (:txn_hash, :mirror_hash)
                    """
                ),
                {"txn_hash": txn_hash, "mirror_hash": mirror_hash, "fx_hash": fx_hash},
            )
        get_platform_counters("subledger_sync").increment("ic_matched_total")
        self.append_event("subledger_sync", "MATCHED", txn_hash, {"mirror_hash": mirror_hash, "fx_hash": fx_hash})

    def record_discrepancy(self, *, txn_hash: str, reason: str, metadata: dict) -> None:
        if reason == "NO_MIRROR_OR_FX_DRIFT":
            get_platform_counters("subledger_sync").increment("match_tolerance_breach_total")
        self.append_event("subledger_sync", "DISCREPANCY", txn_hash, {"reason": reason, **metadata})

    def count_pending(self) -> int:
        with self._engine.connect() as conn:
            return int(conn.execute(text("SELECT COUNT(*) FROM subledger_transactions WHERE status = 'PENDING'")).scalar_one())

    def count_matched(self) -> int:
        with self._engine.connect() as conn:
            n = int(conn.execute(text("SELECT COUNT(*) FROM subledger_transactions WHERE status = 'MATCHED'")).scalar_one())
        return n // 2

    def list_discrepancies(self, limit: int) -> list[dict]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT operation_id AS txn_hash, metadata, recorded_at
                    FROM platform_events
                    WHERE platform = 'subledger_sync' AND event_type = 'DISCREPANCY'
                    ORDER BY event_id DESC LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
        out = []
        for row in rows:
            meta = row["metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta)
            out.append({"txn_hash": row["txn_hash"], "reason": meta.get("reason"), "metadata": meta, "recorded_at": str(row["recorded_at"])})
        return out

    def count_orphans(self) -> int:
        pending = self.count_pending()
        return pending


class SqlAssetStore(_SqlBase, AssetStore):
    def reset(self) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM asset_depreciation_charges"))
            conn.execute(text("DELETE FROM asset_ledger_assets"))
            conn.execute(text("DELETE FROM platform_events WHERE platform = 'asset_ledger'"))

    def register_asset(self, asset: dict) -> None:
        if Decimal(asset["book_value"]) < 0:
            get_platform_counters("asset_ledger").increment("negative_book_value_total")
            raise ValueError("book value cannot be negative")
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO asset_ledger_assets (
                        asset_id, description, acquisition_cost, book_value,
                        accumulated_depreciation, method, jurisdiction, useful_life_months
                    ) VALUES (
                        :asset_id, :description, :acquisition_cost, :book_value,
                        :accumulated_depreciation, :method, :jurisdiction, :useful_life_months
                    )
                    """
                ),
                asset,
            )
        self.append_event("asset_ledger", "ASSET_REGISTERED", asset["asset_id"], asset)

    def get_asset(self, asset_id: str) -> dict | None:
        with self._engine.connect() as conn:
            row = conn.execute(text("SELECT * FROM asset_ledger_assets WHERE asset_id = :id"), {"id": asset_id}).mappings().first()
        return dict(row) if row else None

    def list_assets(self) -> list[dict]:
        with self._engine.connect() as conn:
            rows = conn.execute(text("SELECT * FROM asset_ledger_assets")).mappings().all()
        return [dict(r) for r in rows]

    def apply_charge(self, *, asset_id: str, period: str, charge: str, reg_table_version: str, crystal_id: str | None) -> dict | None:
        try:
            with self._engine.begin() as conn:
                asset = conn.execute(
                    text("SELECT book_value, accumulated_depreciation FROM asset_ledger_assets WHERE asset_id = :id"),
                    {"id": asset_id},
                ).mappings().first()
                if not asset:
                    return None
                charge_d = min(Decimal(charge), Decimal(str(asset["book_value"])))
                if charge_d <= 0:
                    return None
                new_book = Decimal(str(asset["book_value"])) - charge_d
                new_acc = Decimal(str(asset["accumulated_depreciation"])) + charge_d
                conn.execute(
                    text(
                        """
                        INSERT INTO asset_depreciation_charges (asset_id, period, charge, reg_table_version, crystal_id)
                        VALUES (:asset_id, :period, :charge, :reg_table_version, :crystal_id)
                        """
                    ),
                    {
                        "asset_id": asset_id,
                        "period": period,
                        "charge": str(charge_d),
                        "reg_table_version": reg_table_version,
                        "crystal_id": crystal_id,
                    },
                )
                conn.execute(
                    text(
                        """
                        UPDATE asset_ledger_assets
                        SET book_value = :book_value, accumulated_depreciation = :accumulated_depreciation
                        WHERE asset_id = :asset_id
                        """
                    ),
                    {"asset_id": asset_id, "book_value": str(new_book), "accumulated_depreciation": str(new_acc)},
                )
        except Exception:
            get_platform_counters("asset_ledger").increment("depreciation_duplicate_blocked_total")
            return None
        row = {
            "asset_id": asset_id,
            "period": period,
            "charge": str(charge_d),
            "book_value": str(new_book),
            "reg_table_version": reg_table_version,
            "crystal_id": crystal_id,
        }
        self.append_event("asset_ledger", "DEPRECIATION_CHARGED", f"{asset_id}:{period}", row)
        return row

    def list_events(self, limit: int) -> list[dict]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT asset_id, period, charge, reg_table_version, crystal_id, recorded_at
                    FROM asset_depreciation_charges ORDER BY recorded_at DESC LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
        return [dict(r) for r in rows]


class SqlCreditStore(_SqlBase, CreditStore):
    def reset(self) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM credit_evaluations"))
            conn.execute(text("DELETE FROM platform_events WHERE platform = 'credit_govern'"))

    def record_evaluation(self, row: dict) -> bool:
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO credit_evaluations (
                            application_id, decision, exposure_amount, model_version_id,
                            desk_id, score, explanation_id, crystal_id
                        ) VALUES (
                            :application_id, :decision, :exposure_amount, :model_version_id,
                            :desk_id, :score, :explanation_id, :crystal_id
                        )
                        """
                    ),
                    row,
                )
            self.append_event("credit_govern", "EVALUATED", row["application_id"], row)
            return True
        except Exception:
            return False

    def get_evaluation(self, application_id: str) -> dict | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM credit_evaluations WHERE application_id = :id"), {"id": application_id}
            ).mappings().first()
        return dict(row) if row else None


_engines: dict[str, Engine] = {}
_stores: dict[str, Any] = {}
_memory_events: list[dict[str, Any]] = []


def _get_engine() -> Engine | None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    if url not in _engines:
        kwargs: dict[str, Any] = {"future": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            kwargs["poolclass"] = StaticPool
        _engines[url] = create_engine(url, **kwargs)
    return _engines[url]


def get_subledger_store() -> SubledgerStore:
    if "subledger" not in _stores:
        engine = _get_engine()
        _stores["subledger"] = SqlSubledgerStore(engine) if engine else MemorySubledgerStore()
    return _stores["subledger"]


def get_asset_store() -> AssetStore:
    if "asset" not in _stores:
        engine = _get_engine()
        _stores["asset"] = SqlAssetStore(engine) if engine else MemoryAssetStore()
    return _stores["asset"]


def get_credit_store() -> CreditStore:
    if "credit" not in _stores:
        engine = _get_engine()
        _stores["credit"] = SqlCreditStore(engine) if engine else MemoryCreditStore()
    return _stores["credit"]


def reset_all_stores() -> None:
    global _memory_events
    _memory_events.clear()
    for store in _stores.values():
        if hasattr(store, "reset"):
            store.reset()


def append_platform_event(platform: str, event_type: str, operation_id: str, metadata: dict | None = None) -> None:
    item = {
        "platform": platform,
        "event_type": event_type,
        "operation_id": operation_id,
        "metadata": metadata or {},
        "recorded_at": _utcnow().isoformat(),
    }
    engine = _get_engine()
    if engine:
        _SqlBase(engine).append_event(platform, event_type, operation_id, metadata)
    else:
        _memory_events.append(item)


def list_platform_events(platform: str | None = None, *, limit: int = 50) -> list[dict]:
    engine = _get_engine()
    if engine:
        clause = "WHERE platform = :platform" if platform else ""
        params: dict[str, Any] = {"limit": limit}
        if platform:
            params["platform"] = platform
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT platform, event_type, operation_id, metadata, recorded_at
                    FROM platform_events
                    {clause}
                    ORDER BY event_id DESC
                    LIMIT :limit
                    """
                ),
                params,
            ).mappings().all()
        out = []
        for row in rows:
            item = dict(row)
            meta = item.get("metadata")
            if isinstance(meta, str):
                item["metadata"] = json.loads(meta)
            out.append(item)
        return out
    events = _memory_events if platform is None else [e for e in _memory_events if e["platform"] == platform]
    return list(reversed(events[-limit:]))
