"""
STACKSNIPER MLB — Referral System
Generates referral codes, tracks signups, and grants credits.
"""
import string
import random
from sports.mlb.utils.logger import get_logger

log = get_logger("Referral")


def generate_referral_code(length=6):
    """Generate a unique 6-char alphanumeric referral code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


class ReferralSystem:
    def __init__(self, db=None):
        self.db = db

    def _get_db(self):
        """Lazy-load database singleton if not injected."""
        if self.db is None:
            from sports.mlb.data.database import db
            self.db = db
        return self.db

    def _ensure_tables(self):
        """Ensure referral-specific tables exist (idempotent)."""
        db = self._get_db()
        conn = db._conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS referral_credits (
                    id INTEGER PRIMARY KEY,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    credit_type TEXT DEFAULT 'free_month',
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(referrer_id, referred_id)
                );
            """)
        finally:
            conn.close()

    def get_referral_stats(self, user_id):
        """
        Get referral stats for a user: code, link, total referrals, successful conversions.
        Returns dict with referral data.
        """
        db = self._get_db()
        self._ensure_tables()

        # Get the user's referral code
        user = db.get_user_by_id(user_id)
        if not user:
            return {"error": "User not found"}

        referral_code = user.get("referral_code", "")
        if not referral_code:
            # Generate one if missing
            referral_code = generate_referral_code()
            db.update_user(user_id, referral_code=referral_code)

        # Count total referrals (users who signed up with this code)
        conn = db._conn()
        try:
            total_referrals = conn.execute(
                "SELECT COUNT(*) FROM users WHERE referred_by = ?",
                (referral_code,),
            ).fetchone()[0]

            # Count successful conversions (referred users who became subscribers)
            conversions = conn.execute(
                "SELECT COUNT(*) FROM users WHERE referred_by = ? AND subscription_status = 'active'",
                (referral_code,),
            ).fetchone()[0]

            # Count credits earned
            credits_earned = conn.execute(
                "SELECT COUNT(*) FROM referral_credits WHERE referrer_id = ?",
                (user_id,),
            ).fetchone()[0]
        finally:
            conn.close()

        share_link = f"https://stacksniper.com/signup?ref={referral_code}"

        return {
            "user_id": user_id,
            "referral_code": referral_code,
            "share_link": share_link,
            "total_referrals": total_referrals,
            "conversions": conversions,
            "credits_earned": credits_earned,
            "referral_message": (
                f"Join me on STACKSNIPER MLB for AI-powered DFS projections! "
                f"Sign up with my link and we both get a free month: {share_link}"
            ),
        }

    def process_referral(self, new_user_id, referral_code):
        """
        When a new user signs up with a referral code, link them.
        Returns dict with result status.
        """
        db = self._get_db()
        self._ensure_tables()

        if not referral_code:
            return {"success": False, "reason": "No referral code provided"}

        # Find the referrer by their code
        conn = db._conn()
        try:
            conn.row_factory = None
            referrer_row = conn.execute(
                "SELECT id, email FROM users WHERE referral_code = ?",
                (referral_code,),
            ).fetchone()
        finally:
            conn.close()

        if not referrer_row:
            log.warning(f"Invalid referral code used: {referral_code}")
            return {"success": False, "reason": "Invalid referral code"}

        referrer_id = referrer_row[0]

        # Prevent self-referral
        if referrer_id == new_user_id:
            return {"success": False, "reason": "Cannot refer yourself"}

        # Link the new user to the referrer
        db.update_user(new_user_id, referred_by=referral_code)

        log.info(f"User {new_user_id} referred by user {referrer_id} (code: {referral_code})")
        return {
            "success": True,
            "referrer_id": referrer_id,
            "new_user_id": new_user_id,
            "referral_code": referral_code,
        }

    def grant_referral_credit(self, referrer_id):
        """
        Grant 1 free month credit to the referrer when their referral subscribes.
        Returns dict with credit grant status.
        """
        db = self._get_db()
        self._ensure_tables()

        user = db.get_user_by_id(referrer_id)
        if not user:
            return {"success": False, "reason": "Referrer not found"}

        referral_code = user.get("referral_code", "")

        # Find the most recent referred user who subscribed and hasn't been credited yet
        conn = db._conn()
        try:
            # Get referred users who subscribed
            subscribed_referrals = conn.execute(
                """SELECT id FROM users
                   WHERE referred_by = ? AND subscription_status = 'active'
                   ORDER BY created_at DESC""",
                (referral_code,),
            ).fetchall()

            # Get already credited referrals
            credited = conn.execute(
                "SELECT referred_id FROM referral_credits WHERE referrer_id = ?",
                (referrer_id,),
            ).fetchall()
            credited_ids = {row[0] for row in credited}

            # Find uncredited conversions
            uncredited = [row[0] for row in subscribed_referrals if row[0] not in credited_ids]

            if not uncredited:
                return {"success": False, "reason": "No new conversions to credit"}

            # Grant credit for the first uncredited conversion
            referred_id = uncredited[0]
            conn.execute(
                "INSERT INTO referral_credits (referrer_id, referred_id, credit_type) VALUES (?, ?, 'free_month')",
                (referrer_id, referred_id),
            )
            conn.commit()
        finally:
            conn.close()

        # Extend the referrer's subscription by updating their tier/status
        # The actual billing extension would integrate with Stripe in production.
        # Here we mark the credit and log it.
        log.info(f"Granted free month credit to user {referrer_id} for referring user {referred_id}")

        return {
            "success": True,
            "referrer_id": referrer_id,
            "referred_id": referred_id,
            "credit_type": "free_month",
            "message": "Free month credit granted successfully",
        }


referral_system = ReferralSystem()
