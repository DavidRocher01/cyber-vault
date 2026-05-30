#!/usr/bin/env python3
"""
Create or elevate an admin account in production.

Usage (inside ECS container):
    python scripts/create_admin.py <email> <password>

Run via ECS exec:
    TASK_ID=$(aws ecs list-tasks --cluster <cluster> --service-name <service> \
              --query 'taskArns[0]' --output text --region eu-west-3)
    aws ecs execute-command \
      --cluster <cluster> \
      --task "$TASK_ID" \
      --container app \
      --interactive \
      --region eu-west-3 \
      --command "python scripts/create_admin.py you@example.com 'YourPassword123!'"
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")

from app.core.config import settings
from app.core.security import hash_password
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User


async def main(email: str, password: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # Highest active plan
        result = await db.execute(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.tier_level.desc()).limit(1)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            print("ERROR: aucun plan actif trouvé en base.")
            await engine.dispose()
            sys.exit(1)

        # Create or update user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            print(f"Utilisateur existant {email} (id={user.id}) — mise à jour...")
            user.hashed_password = hash_password(password)
            user.is_active = True
            user.is_rssi_consultant = True
            user.failed_login_attempts = 0
            user.locked_until = None
        else:
            print(f"Création du compte {email}...")
            user = User(
                email=email,
                hashed_password=hash_password(password),
                is_active=True,
                is_rssi_consultant=True,
            )
            db.add(user)
            await db.flush()

        # Create or upgrade subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == "active",
            )
        )
        sub = result.scalar_one_or_none()

        far_future = datetime.now(UTC) + timedelta(days=36500)  # ~100 ans

        if sub:
            print(f"Abonnement existant (plan_id={sub.plan_id}) → upgrade vers '{plan.name}'...")
            sub.plan_id = plan.id
            sub.current_period_end = far_future
        else:
            print(f"Création abonnement '{plan.name}' (tier {plan.tier_level})...")
            sub = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                stripe_customer_id="manual_admin",
                stripe_subscription_id="manual_admin",
                status="active",
                current_period_start=datetime.now(UTC),
                current_period_end=far_future,
            )
            db.add(sub)

        await db.commit()

    await engine.dispose()

    print("\n" + "=" * 50)
    print("  COMPTE ADMIN CRÉÉ / MIS À JOUR")
    print("=" * 50)
    print(f"  Email    : {email}")
    print(f"  Plan     : {plan.name} (tier {plan.tier_level}, {plan.max_sites} sites)")
    print("  RSSI     : True")
    print("  Expire   : ~2126")
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_admin.py <email> <password>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
