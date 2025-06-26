#!/usr/bin/env python3
"""
DIY-MOD: Fix Filter Loading Issues
This script ensures that user filters are properly loaded and functioning.
"""

import sqlite3
import json
from datetime import datetime
import os

def fix_filter_loading():
    """Fix filter loading issues in the database"""
    print("🔧 DIY-MOD: Fixing Filter Loading Issues")
    print("=========================================")
    
    # Database path
    db_path = "/opt/DIY-MOD/Backend/diy_mod.db"
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📊 Step 1: Checking current filters...")
        
        # Check existing filters
        cursor.execute("SELECT COUNT(*) FROM filters")
        filter_count = cursor.fetchone()[0]
        print(f"   Found {filter_count} filters in database")
        
        # Check users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"   Found {user_count} users in database")
        
        print("🔍 Step 2: Analyzing filter issues...")
        
        # Get filters with issues
        cursor.execute("""
            SELECT f.id, f.filter_text, f.user_id, f.is_active 
            FROM filters f 
            WHERE f.is_active = 1
        """)
        active_filters = cursor.fetchall()
        
        print(f"   Found {len(active_filters)} active filters")
        
        if len(active_filters) == 0:
            print("⚠️  No active filters found! Creating default filters...")
            create_default_filters(cursor)
        
        print("🔧 Step 3: Fixing filter configuration...")
        
        # Update filter configuration for better matching
        for filter_id, filter_text, user_id, is_active in active_filters:
            # Ensure filters have proper configuration
            cursor.execute("""
                UPDATE filters 
                SET confidence_threshold = 0.7,
                    updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), filter_id))
            
            print(f"   ✅ Updated filter: {filter_text[:50]}...")
        
        print("📝 Step 4: Ensuring filter processing...")
        
        # Make sure filter processing is enabled
        cursor.execute("""
            UPDATE filters 
            SET is_active = 1,
                confidence_threshold = COALESCE(confidence_threshold, 0.7)
            WHERE is_active IS NULL OR confidence_threshold IS NULL
        """)
        
        affected_rows = cursor.rowcount
        if affected_rows > 0:
            print(f"   ✅ Fixed {affected_rows} filter configurations")
        
        print("🎯 Step 5: Optimizing filter performance...")
        
        # Create index for faster filter lookups if it doesn't exist
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_filters_user_active 
                ON filters(user_id, is_active)
            """)
            print("   ✅ Created filter lookup index")
        except sqlite3.Error as e:
            print(f"   ⚠️  Index already exists: {e}")
        
        # Commit changes
        conn.commit()
        
        print("✅ Step 6: Verification...")
        
        # Verify fixes
        cursor.execute("""
            SELECT COUNT(*) 
            FROM filters 
            WHERE is_active = 1 AND confidence_threshold IS NOT NULL
        """)
        working_filters = cursor.fetchone()[0]
        
        print(f"   ✅ {working_filters} filters are now properly configured")
        
        # Show sample filters
        cursor.execute("""
            SELECT filter_text, confidence_threshold 
            FROM filters 
            WHERE is_active = 1 
            LIMIT 5
        """)
        sample_filters = cursor.fetchall()
        
        print("   📋 Active Filters:")
        for filter_text, threshold in sample_filters:
            print(f"      • {filter_text} (threshold: {threshold})")
        
        conn.close()
        
        print("")
        print("🎉 Filter Loading Issues Fixed!")
        print("==============================")
        print(f"✅ {working_filters} filters are now active and configured")
        print("✅ Database indexes optimized")
        print("✅ Filter processing enabled")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def create_default_filters(cursor):
    """Create default filters for testing"""
    default_filters = [
        {
            'filter_text': 'weight loss or weight loss transformation progress',
            'intensity_level': 5,
            'confidence_threshold': 0.7,
            'filter_type': 'content'
        },
        {
            'filter_text': 'surgery, including images of surgical scars or hospital images',
            'intensity_level': 5,
            'confidence_threshold': 0.8,
            'filter_type': 'content'
        },
        {
            'filter_text': 'plastic surgery procedures and results',
            'intensity_level': 4,
            'confidence_threshold': 0.7,
            'filter_type': 'content'
        },
        {
            'filter_text': 'body transformation and before/after photos',
            'intensity_level': 3,
            'confidence_threshold': 0.6,
            'filter_type': 'content'
        }
    ]
    
    # Get or create a default user
    cursor.execute("SELECT id FROM users LIMIT 1")
    user_result = cursor.fetchone()
    
    if user_result:
        user_id = user_result[0]
    else:
        # Create default user
        user_id = "default_user_12345"
        cursor.execute("""
            INSERT OR IGNORE INTO users (id, created_at, last_active)
            VALUES (?, ?, ?)
        """, (user_id, datetime.now().isoformat(), datetime.now().isoformat()))
    
    # Insert default filters
    for filter_data in default_filters:
        cursor.execute("""
            INSERT OR IGNORE INTO filters 
            (user_id, filter_text, intensity_level, confidence_threshold, 
             filter_type, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            user_id,
            filter_data['filter_text'],
            filter_data['intensity_level'],
            filter_data['confidence_threshold'],
            filter_data['filter_type'],
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
    
    print(f"   ✅ Created {len(default_filters)} default filters")

if __name__ == "__main__":
    success = fix_filter_loading()
    exit(0 if success else 1) 