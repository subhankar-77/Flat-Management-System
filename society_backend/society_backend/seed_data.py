"""
seed_data.py — Run ONCE to populate the database with:
  • All 9 flats
  • All 9 flat owners (edit details below to match your society)
  • The admin user (also done by /api/auth/seed-admin endpoint)

Usage:
  cd society_backend
  python seed_data.py
"""

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.models import Flat, FlatOwner, User, OwnershipType
from app.auth import hash_password
from app.config import settings

# ── EDIT THESE TO MATCH YOUR SOCIETY ─────────────────────────────────────────

FLATS = [
    {"flat_number": "101", "floor": "Ground Floor", "area_sqft": 650},
    {"flat_number": "102", "floor": "Ground Floor", "area_sqft": 650},
    {"flat_number": "103", "floor": "Ground Floor", "area_sqft": 630},
    
    {"flat_number": "201", "floor": "1st Floor",    "area_sqft": 650},
    {"flat_number": "202", "floor": "1st Floor",    "area_sqft": 650},
    {"flat_number": "203", "floor": "1st Floor",    "area_sqft": 630},
    
    {"flat_number": "301", "floor": "2nd Floor",    "area_sqft": 650},
    {"flat_number": "302", "floor": "2nd Floor",    "area_sqft": 650},
    {"flat_number": "303", "floor": "2nd Floor",    "area_sqft": 630},
]

OWNERS = [
    # flat_number, full_name, email, phone, ownership_type
    ("101", "Somnath Goswami",    "somnath.goswami@gmail.com",    "+91 98765 43210", OwnershipType.owner_occupied),
    ("102", "Sital Chakrabartti",  "sital.chakrabartti@gmail.com",  "+91 87654 32109", OwnershipType.owner_occupied),
    ("103", "Adtiya Moitra",   "adtiya.moitra@gmail.com",   "+91 76543 21098", OwnershipType.tenant),
    ("201", "P K Dey",  "p.k.dey@gmail.com",  "+91 65432 10987", OwnershipType.owner_occupied),
    ("202", "N R Singha Roy",     "mohan.das@outlook.com",   "+91 54321 09876", OwnershipType.owner_not_residing),
    ("203", "Kavitha Nair",  "kavitha.nair@gmail.com",  "+91 43210 98765", OwnershipType.owner_occupied),
    ("301", "Deepak Singh",  "deepak.singh@gmail.com",  "+91 32109 87654", OwnershipType.owner_occupied),
    ("302", "Meena Iyer",    "meena.iyer@yahoo.com",    "+91 21098 76543", OwnershipType.tenant),
    ("303", "Suresh Reddy",  "suresh.reddy@gmail.com",  "+91 10987 65432", OwnershipType.owner_occupied),
]

# ─────────────────────────────────────────────────────────────────────────────

def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Admin user
        if not db.query(User).filter(User.email == settings.ADMIN_EMAIL).first():
            admin = User(
                name=settings.ADMIN_NAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            print(f"✅ Admin created: {settings.ADMIN_EMAIL}")
        else:
            print(f"⏭  Admin already exists")

        # 2. Flats
        flat_map = {}   # flat_number → Flat object
        for f in FLATS:
            existing = db.query(Flat).filter(Flat.flat_number == f["flat_number"]).first()
            if existing:
                flat_map[f["flat_number"]] = existing
                print(f"⏭  Flat {f['flat_number']} already exists")
                continue
            flat = Flat(**f)
            db.add(flat)
            db.commit()
            db.refresh(flat)
            flat_map[f["flat_number"]] = flat
            print(f"✅ Created Flat {f['flat_number']}")

        # 3. Owners
        for flat_num, name, email, phone, otype in OWNERS:
            flat = flat_map.get(flat_num)
            if not flat:
                print(f"⚠️  Flat {flat_num} not found — skipping owner {name}")
                continue

            existing = db.query(FlatOwner).filter(FlatOwner.flat_id == flat.id).first()
            if existing:
                print(f"⏭  Owner for Flat {flat_num} already exists")
                continue

            owner = FlatOwner(
                flat_id=flat.id,
                full_name=name,
                email=email,
                phone=phone,
                ownership_type=otype,
            )
            db.add(owner)
            db.commit()
            print(f"✅ Owner added: {name} → Flat {flat_num}")

        print("\n🎉 Seed complete!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
