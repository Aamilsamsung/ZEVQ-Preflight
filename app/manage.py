"""Provision closed-staging accounts after an operator verifies identity."""
import argparse
import getpass
from sqlalchemy import select
from .db import make_engine, factory, User, Organization, Membership
from .security import hasher


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['create-user'])
    parser.add_argument('--email', required=True)
    parser.add_argument('--organization', default='ZEVQ Labs')
    parser.add_argument('--identity-verified', action='store_true')
    args = parser.parse_args()
    if not args.identity_verified:
        parser.error('Operator must verify ownership of the email before using --identity-verified')
    password = getpass.getpass('New password (at least 14 characters): ')
    if len(password) < 14 or len(password) > 256:
        parser.error('Password must be 14–256 characters')
    with factory(make_engine())() as db:
        if db.scalar(select(User).where(User.email == args.email.strip().lower())):
            parser.error('Account already exists')
        user = User(email=args.email.strip().lower(), password_hash=hasher.hash(password), verified=1)
        org = Organization(name=args.organization)
        db.add_all([user, org]); db.flush()
        db.add(Membership(org_id=org.id, user_id=user.id, role='owner')); db.commit()
    print('Account provisioned; public registration remains disabled.')

if __name__ == '__main__':
    main()
