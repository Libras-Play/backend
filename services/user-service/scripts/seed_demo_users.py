#!/usr/bin/env python3
"""
Seed demo users for user-service in LocalStack
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import dynamo


async def seed_demo_users():
    """Create demo users for testing"""
    
    demo_users = [
        {
            "userId": "demo-user-1",
            "email": "alice@example.com",
            "username": "alice_signs",
            "preferredLanguage": "LSB",
            "settings": {"notifications": True}
        },
        {
            "userId": "demo-user-2",
            "email": "bob@example.com",
            "username": "bob_learner",
            "preferredLanguage": "ASL",
            "settings": {"notifications": False}
        },
        {
            "userId": "demo-user-3",
            "email": "charlie@example.com",
            "username": "charlie_pro",
            "preferredLanguage": "LSB",
            "settings": {"notifications": True}
        }
    ]
    
    print("🌱 Seeding demo users...")
    
    for user_data in demo_users:
        try:
            # Check if user exists
            existing = await dynamo.get_user(user_data["userId"])
            if existing:
                print(f"  ⚠️  User {user_data['username']} already exists, skipping")
                continue
            
            # Create user
            user = await dynamo.create_user(user_data)
            print(f"  ✅ Created user: {user['username']} ({user['email']})")
            
            # Add some initial progress for user 1
            if user_data["userId"] == "demo-user-1":
                await dynamo.update_progress(
                    user_id=user_data["userId"],
                    level_id=1,
                    exercise_id=1,
                    score=85,
                    xp_earned=50,
                    completed=True
                )
                print(f"     └─ Added progress: Level 1, Exercise 1 (85%)")
                
                # Consume a life
                await dynamo.update_user_lives(user_data["userId"], consume=1)
                print(f"     └─ Consumed 1 life (4 remaining)")
            
        except Exception as e:
            print(f"  ❌ Error creating user {user_data['username']}: {str(e)}")
    
    print("\n✅ Seed data created successfully!")
    print("\n📊 Summary:")
    print(f"   - Total users: {len(demo_users)}")
    print(f"   - User 1 (alice): Has progress and 4 lives")
    print(f"   - User 2 (bob): Fresh account, 5 lives")
    print(f"   - User 3 (charlie): Fresh account, 5 lives")
    print("\n🔗 Test the API:")
    print("   GET  http://localhost:8001/api/v1/users/demo-user-1/status")
    print("   GET  http://localhost:8001/api/v1/users/demo-user-1")
    print("   POST http://localhost:8001/api/v1/users/demo-user-1/consume-life")


if __name__ == "__main__":
    asyncio.run(seed_demo_users())
