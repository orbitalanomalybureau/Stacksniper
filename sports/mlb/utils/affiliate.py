"""
STACKSNIPER MLB — Affiliate System
Manages affiliate partners, tracks signups, and processes commissions.
"""
import string
import random
from datetime import datetime
from sports.mlb.utils.logger import get_logger

log = get_logger("Affiliate")


def _generate_affiliate_code(length=8):
    """Generate a unique affiliate code."""
    chars = string.ascii_uppercase + string.digits
    return "AFF-" + "".join(random.choices(chars, k=length))


class AffiliateSystem:
    def __init__(self, db=None):
        self.db = db

    def _get_db(self):
        """Lazy-load database singleton if not injected."""
        if self.db is None:
            from sports.mlb.data.database import db
            self.db = db
        return self.db

    def _ensure_tables(self):
        """Ensure affiliate-specific tables exist (idempotent)."""
        db = self._get_db()
        conn = db._conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS affiliate_signups (
                    id INTEGER PRIMARY KEY,
                    affiliate_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    converted INTEGER DEFAULT 0,
                    signup_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    converted_at TIMESTAMP,
                    UNIQUE(affiliate_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS affiliate_commissions (
                    id INTEGER PRIMARY KEY,
                    affiliate_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    commission REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    paid_at TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_aff_signups_aff ON affiliate_signups(affiliate_id);
                CREATE INDEX IF NOT EXISTS idx_aff_commissions_aff ON affiliate_commissions(affiliate_id);
            """)
        finally:
            conn.close()

    def register_affiliate(self, name, email, code=None):
        """
        Register a new affiliate partner.
        Returns the affiliate record dict.
        """
        db = self._get_db()
        self._ensure_tables()

        if not code:
            code = _generate_affiliate_code()

        # Check if email already registered
        conn = db._conn()
        try:
            existing = conn.execute(
                "SELECT id FROM affiliates WHERE email = ?", (email,)
            ).fetchone()
            if existing:
                log.warning(f"Affiliate already exists for email: {email}")
                return self.get_affiliate_stats(existing[0])

            conn.execute(
                "INSERT INTO affiliates (name, code, email) VALUES (?, ?, ?)",
                (name, code, email),
            )
            conn.commit()

            row = conn.execute(
                "SELECT id, name, code, email, commission_rate, total_earned, created_at FROM affiliates WHERE code = ?",
                (code,),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            return {"error": "Failed to create affiliate"}

        result = {
            "id": row[0],
            "name": row[1],
            "code": row[2],
            "email": row[3],
            "commission_rate": row[4],
            "total_earned": row[5],
            "created_at": row[6],
            "signup_link": f"https://stacksniper.com/signup?aff={row[2]}",
        }
        log.info(f"Registered new affiliate: {name} ({code})")
        return result

    def track_signup(self, user_id, affiliate_code):
        """
        Track when a user signs up via affiliate link.
        Returns dict with tracking result.
        """
        db = self._get_db()
        self._ensure_tables()

        # Find the affiliate by code
        conn = db._conn()
        try:
            aff_row = conn.execute(
                "SELECT id, name FROM affiliates WHERE code = ?", (affiliate_code,)
            ).fetchone()

            if not aff_row:
                log.warning(f"Invalid affiliate code: {affiliate_code}")
                return {"success": False, "reason": "Invalid affiliate code"}

            affiliate_id = aff_row[0]
            affiliate_name = aff_row[1]

            # Check for duplicate tracking
            existing = conn.execute(
                "SELECT id FROM affiliate_signups WHERE affiliate_id = ? AND user_id = ?",
                (affiliate_id, user_id),
            ).fetchone()

            if existing:
                return {"success": False, "reason": "Signup already tracked"}

            conn.execute(
                "INSERT INTO affiliate_signups (affiliate_id, user_id) VALUES (?, ?)",
                (affiliate_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

        log.info(f"Tracked signup: user {user_id} via affiliate {affiliate_name} ({affiliate_code})")
        return {
            "success": True,
            "affiliate_id": affiliate_id,
            "affiliate_name": affiliate_name,
            "user_id": user_id,
        }

    def process_commission(self, user_id, amount):
        """
        Credit 30% commission to the affiliate who referred this user.
        Called when the user makes a payment.
        Returns dict with commission details.
        """
        db = self._get_db()
        self._ensure_tables()

        conn = db._conn()
        try:
            # Find which affiliate referred this user
            signup_row = conn.execute(
                "SELECT affiliate_id FROM affiliate_signups WHERE user_id = ?",
                (user_id,),
            ).fetchone()

            if not signup_row:
                return {"success": False, "reason": "User not referred by an affiliate"}

            affiliate_id = signup_row[0]

            # Get affiliate's commission rate
            aff_row = conn.execute(
                "SELECT commission_rate, name FROM affiliates WHERE id = ?",
                (affiliate_id,),
            ).fetchone()

            if not aff_row:
                return {"success": False, "reason": "Affiliate not found"}

            commission_rate = aff_row[0] or 0.30
            affiliate_name = aff_row[1]
            commission = round(amount * commission_rate, 2)

            # Record the commission
            conn.execute(
                "INSERT INTO affiliate_commissions (affiliate_id, user_id, amount, commission) VALUES (?, ?, ?, ?)",
                (affiliate_id, user_id, amount, commission),
            )

            # Update total earned for the affiliate
            conn.execute(
                "UPDATE affiliates SET total_earned = total_earned + ? WHERE id = ?",
                (commission, affiliate_id),
            )

            # Mark signup as converted if not already
            conn.execute(
                "UPDATE affiliate_signups SET converted = 1, converted_at = ? WHERE affiliate_id = ? AND user_id = ?",
                (datetime.now().isoformat(), affiliate_id, user_id),
            )

            conn.commit()
        finally:
            conn.close()

        log.info(
            f"Commission processed: ${commission:.2f} ({commission_rate * 100:.0f}% of ${amount:.2f}) "
            f"for affiliate {affiliate_name} (user {user_id})"
        )
        return {
            "success": True,
            "affiliate_id": affiliate_id,
            "affiliate_name": affiliate_name,
            "user_id": user_id,
            "amount": amount,
            "commission_rate": commission_rate,
            "commission": commission,
        }

    def get_affiliate_stats(self, affiliate_id):
        """
        Get affiliate's stats: signups, conversions, earnings, commission history.
        """
        db = self._get_db()
        self._ensure_tables()

        conn = db._conn()
        try:
            # Basic affiliate info
            aff_row = conn.execute(
                "SELECT id, name, code, email, commission_rate, total_earned, created_at FROM affiliates WHERE id = ?",
                (affiliate_id,),
            ).fetchone()

            if not aff_row:
                return {"error": "Affiliate not found"}

            # Signup counts
            total_signups = conn.execute(
                "SELECT COUNT(*) FROM affiliate_signups WHERE affiliate_id = ?",
                (affiliate_id,),
            ).fetchone()[0]

            conversions = conn.execute(
                "SELECT COUNT(*) FROM affiliate_signups WHERE affiliate_id = ? AND converted = 1",
                (affiliate_id,),
            ).fetchone()[0]

            # Commission totals
            pending_commissions = conn.execute(
                "SELECT COALESCE(SUM(commission), 0) FROM affiliate_commissions WHERE affiliate_id = ? AND status = 'pending'",
                (affiliate_id,),
            ).fetchone()[0]

            paid_commissions = conn.execute(
                "SELECT COALESCE(SUM(commission), 0) FROM affiliate_commissions WHERE affiliate_id = ? AND status = 'paid'",
                (affiliate_id,),
            ).fetchone()[0]

            # Recent commissions (last 20)
            recent_rows = conn.execute(
                """SELECT user_id, amount, commission, status, created_at
                   FROM affiliate_commissions
                   WHERE affiliate_id = ?
                   ORDER BY created_at DESC LIMIT 20""",
                (affiliate_id,),
            ).fetchall()
        finally:
            conn.close()

        recent_commissions = [
            {
                "user_id": r[0],
                "amount": r[1],
                "commission": r[2],
                "status": r[3],
                "date": r[4],
            }
            for r in recent_rows
        ]

        conversion_rate = round((conversions / total_signups) * 100, 1) if total_signups > 0 else 0.0

        return {
            "id": aff_row[0],
            "name": aff_row[1],
            "code": aff_row[2],
            "email": aff_row[3],
            "commission_rate": aff_row[4],
            "total_earned": round(aff_row[5], 2),
            "created_at": aff_row[6],
            "signup_link": f"https://stacksniper.com/signup?aff={aff_row[2]}",
            "total_signups": total_signups,
            "conversions": conversions,
            "conversion_rate": conversion_rate,
            "pending_commissions": round(pending_commissions, 2),
            "paid_commissions": round(paid_commissions, 2),
            "recent_commissions": recent_commissions,
        }


affiliate_system = AffiliateSystem()
