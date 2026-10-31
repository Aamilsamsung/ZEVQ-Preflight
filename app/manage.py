"""Provision closed-staging accounts after an operator verifies identity."""
import argparse
import getpass
from sqlalchemy import select
from .db import make_engine, factory, User, Organization, Membership
from .security import hasher
from .accounts import reset_password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['create-user', 'reset-password'])
    parser.add_argument('--email', required=True)
    parser.add_argument('--organization', default='ZEVQ Labs')
    parser.add_argument('--reference', default='', help='Non-secret support ticket reference for password resets')
    parser.add_argument('--identity-verified', action='store_true')
    parser.add_argument('--require-email-verification', action='store_true', help='Create a pending account that must confirm its mailbox before sign-in')
    args = parser.parse_args()
    if args.command == 'reset-password' and args.require_email_verification:
        parser.error('--require-email-verification is only for create-user')
    if not args.identity_verified:
        parser.error('Operator must verify ownership of the email before using --identity-verified')
    password = getpass.getpass('New password (at least 14 characters): ')
    if len(password) < 14 or len(password) > 256:
        parser.error('Password must be 14–256 characters')
    if getpass.getpass('Confirm new password: ') != password:
        parser.error('Passwords do not match')
    if args.command == 'reset-password':
        try:
            reset_password(factory(make_engine()), args.email, password, identity_verified=True, reference=args.reference)
        except ValueError as error:
            parser.error(str(error))
        print('Password reset; every existing account session revoked.')
        return
    with factory(make_engine())() as db:
        if db.scalar(select(User).where(User.email == args.email.strip().lower())):
            parser.error('Account already exists')
        user = User(email=args.email.strip().lower(), password_hash=hasher.hash(password), verified=0 if args.require_email_verification else 1)
        org = Organization(name=args.organization)
        db.add_all([user, org]); db.flush()
        db.add(Membership(org_id=org.id, user_id=user.id, role='owner')); db.commit()
    print('Account provisioned; public registration remains disabled.' + (' Email confirmation is required before sign-in; delivery must be configured separately.' if args.require_email_verification else ''))

if __name__ == '__main__':
    main()
