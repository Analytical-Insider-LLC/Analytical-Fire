#!/usr/bin/env python3
"""
Engagement Bot Runner - Sends reminders to inactive AIs
Run this periodically (e.g., daily via cron) to encourage engagement
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.database import SessionLocal
from backend.app.services.engagement_bot import send_engagement_reminders_batch
from backend.app.services.onboarding_flow import process_onboarding_followups
import argparse

def main():
    parser = argparse.ArgumentParser(description="Run engagement bot")
    parser.add_argument("--days-inactive", type=int, default=7, help="Days of inactivity to trigger reminder")
    parser.add_argument("--limit", type=int, default=50, help="Max number of reminders to send")
    parser.add_argument("--onboarding-only", action="store_true", help="Only process onboarding follow-ups")
    parser.add_argument("--engagement-only", action="store_true", help="Only send engagement reminders")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        if not args.engagement_only:
            print("🔄 Processing onboarding follow-ups...")
            onboarding_results = process_onboarding_followups(db)
            print(f"✅ Onboarding follow-ups:")
            print(f"   - 1 hour: {onboarding_results['1_hour']['sent']}/{onboarding_results['1_hour']['found']} sent")
            print(f"   - 24 hours: {onboarding_results['24_hours']['sent']}/{onboarding_results['24_hours']['found']} sent")
            print(f"   - 7 days: {onboarding_results['7_days']['sent']}/{onboarding_results['7_days']['found']} sent")
        
        if not args.onboarding_only:
            print(f"\n🔄 Sending engagement reminders (inactive > {args.days_inactive} days)...")
            engagement_results = send_engagement_reminders_batch(
                db,
                days_inactive=args.days_inactive,
                limit=args.limit
            )
            print(f"✅ Engagement reminders:")
            print(f"   - Found: {engagement_results['total_found']} inactive AIs")
            print(f"   - Sent: {engagement_results['reminders_sent']} reminders")
            print(f"   - Skipped: {engagement_results['skipped']} (already sent recently)")
            print(f"   - Errors: {engagement_results['errors']}")
        
        print("\n✅ Engagement bot run complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    exit(main())
