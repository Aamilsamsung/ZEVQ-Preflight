"""Persistent records. SQLite is development-only; staging requires PostgreSQL."""
import os
import time
import uuid
from sqlalchemy import create_engine, String, Text, Integer, Float, ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    verified: Mapped[int] = mapped_column(Integer, default=0)


class Organization(Base):
    __tablename__ = 'organizations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))


class Membership(Base):
    __tablename__ = 'memberships'
    org_id: Mapped[str] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))


class SessionRecord(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires: Mapped[float] = mapped_column(Float)


class Repository(Base):
    __tablename__ = 'repositories'
    __table_args__ = (UniqueConstraint('org_id', 'full_name'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    full_name: Mapped[str] = mapped_column(String(210))
    source_kind: Mapped[str] = mapped_column(String(12), default='public', server_default='public')


class Scan(Base):
    __tablename__ = 'scans'
    __table_args__ = (UniqueConstraint('org_id', 'idempotency_key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    repository: Mapped[str] = mapped_column(String(210), default='Uploaded archive')
    base_ref: Mapped[str] = mapped_column(String(120), default='')
    head_ref: Mapped[str] = mapped_column(String(120), default='')
    status: Mapped[str] = mapped_column(String(20), default='queued', index=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Audit(Base):
    __tablename__ = 'audit_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    actor_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class RateBucket(Base):
    __tablename__ = 'rate_buckets'
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    expires: Mapped[float] = mapped_column(Float)


def make_engine(url=None, *, health=False):
    url = url or os.getenv('DATABASE_URL', 'sqlite:///./preflight.db')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    options = {'pool_size': 1 if health else 2, 'max_overflow': 0 if health else 2, 'pool_timeout': 0.5 if health else 30, 'pool_recycle': 300} if not url.startswith('sqlite') else {}
    engine = create_engine(url, hide_parameters=True, pool_pre_ping=True, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {'connect_timeout': 2 if health else 15, 'prepare_threshold': None}, **options)
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def foreign_keys(dbapi, _):
            dbapi.execute('PRAGMA foreign_keys=ON')
    return engine


def factory(engine):
    return sessionmaker(engine, expire_on_commit=False)


class FindingReview(Base):
    __tablename__ = 'finding_reviews'
    scan_id: Mapped[str] = mapped_column(ForeignKey('scans.id', ondelete='CASCADE'), primary_key=True)
    finding_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    actor_id: Mapped[str] = mapped_column(String(36))
    updated_at: Mapped[float] = mapped_column(Float)


class FindingReviewEvent(Base):
    __tablename__ = 'finding_review_events'
    __table_args__ = (UniqueConstraint('scan_id', 'finding_id', 'version'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    scan_id: Mapped[str] = mapped_column(ForeignKey('scans.id', ondelete='CASCADE'), index=True)
    finding_id: Mapped[str] = mapped_column(String(128))
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    actor_id: Mapped[str] = mapped_column(String(36))
    updated_at: Mapped[float] = mapped_column(Float)


class RetentionPolicy(Base):
    __tablename__='retention_policies'
    org_id: Mapped[str]=mapped_column(ForeignKey('organizations.id',ondelete='CASCADE'),primary_key=True)
    days: Mapped[int | None]=mapped_column(Integer,nullable=True)
    version: Mapped[int]=mapped_column(Integer)
    updated_at: Mapped[float]=mapped_column(Float)


class CleanupRun(Base):
    __tablename__='cleanup_runs'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    org_id: Mapped[str]=mapped_column(ForeignKey('organizations.id',ondelete='CASCADE'),index=True)
    actor_id: Mapped[str]=mapped_column(String(36))
    policy_version: Mapped[int]=mapped_column(Integer)
    cutoff: Mapped[float]=mapped_column(Float)
    scan_ids: Mapped[str]=mapped_column(Text)
    created_at: Mapped[float]=mapped_column(Float)
    expires_at: Mapped[float]=mapped_column(Float)
    status: Mapped[str]=mapped_column(String(24))
    deleted_count: Mapped[int]=mapped_column(Integer,default=0)
    preserved_count: Mapped[int]=mapped_column(Integer,default=0)
    reason: Mapped[str]=mapped_column(Text,default='')


class EmailToken(Base):
    __tablename__ = 'email_tokens'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    purpose: Mapped[str] = mapped_column(String(12))
    expires: Mapped[float] = mapped_column(Float)
    consumed_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class RepositoryCredential(Base):
    __tablename__ = 'repository_credentials'
    repo_id: Mapped[str] = mapped_column(ForeignKey('repositories.id', ondelete='CASCADE'), primary_key=True)
    org_id: Mapped[str] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'), index=True)
    ciphertext: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer)
