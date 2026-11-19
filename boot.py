"""
Boot script for Railway/Render deployment.
Run this ONCE after initial deploy to initialize DB and seed academic data.

Usage:
  python boot.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import seed_demo_data

app = create_app()

with app.app_context():
    db.create_all()
    seed_demo_data()
    print("Database initialized and demo courses seeded.")

    # Now seed academic data
    from app.models import Student
    if Student.query.count() == 0:
        print("Seeding CS201 academic dataset...")
        from app.models import Course
        course = Course.query.filter_by(code='CS201').first()
        if course:
            # Import seed function inline to avoid duplicate path manipulation
            import seed_academic
            # seed_academic.seed_academic() is called below after path setup
        else:
            print("CS201 course not found — run seed_academic.py manually after boot.")
    else:
        print(f"Academic data already seeded ({Student.query.count()} students).")

print("Boot complete.")
