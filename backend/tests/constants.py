from app.models import Role

ADMIN = {"email": "admin@test.io", "name": "Test Admin", "password": "AdminPass123", "role": Role.ADMIN}
REVIEWER = {"email": "reviewer@test.io", "name": "Test Reviewer", "password": "ReviewPass123", "role": Role.REVIEWER}
INACTIVE = {"email": "inactive@test.io", "name": "Inactive User", "password": "InactivePass123", "role": Role.REVIEWER}