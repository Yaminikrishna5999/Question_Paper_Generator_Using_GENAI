import sqlite3
import os
import hashlib
import streamlit as st

DB_PATH = os.path.join("data", "users.db")

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT,
            designation TEXT,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'Active',
            subjects TEXT,
            last_login TIMESTAMP
        )
    """)
    
    # Create papers table for persistent storage
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            paper_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if admin exists, if not create default
    cursor.execute("SELECT * FROM users WHERE email = 'admin@gmail.com'")
    if not cursor.fetchone():
        hashed_pass = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users (full_name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, ("System Administrator", "admin@gmail.com", hashed_pass, "admin"))
    
    # Audit Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
             timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_email TEXT,
            action TEXT,
            details TEXT
        )
    """)
    
    # Announcements
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            message TEXT,
            type TEXT, -- Info, Warning, Update, Event
            target_type TEXT DEFAULT 'all', -- all, specific
            target_email TEXT,
            deadline TEXT,
            attachment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # System Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Seed default settings if empty
    cursor.execute("SELECT COUNT(*) FROM system_settings")
    if cursor.fetchone()[0] == 0:
        settings = [
            ("enable_ai", "true"),
            ("allow_uploads", "true"),
            ("max_questions", "30")
        ]
        cursor.executemany("INSERT INTO system_settings (key, value) VALUES (?, ?)", settings)
    
    # Migration: Add status column if not exists
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'Active'")
    except sqlite3.OperationalError:
        pass # Already exists
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN subjects TEXT")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    # --- Migration: Paper Approval Workflow ---
    try:
        cursor.execute("ALTER TABLE user_papers ADD COLUMN status TEXT DEFAULT 'Pending'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE user_papers ADD COLUMN admin_comments TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE user_papers ADD COLUMN is_downloaded BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE user_papers ADD COLUMN admin_downloaded BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE user_papers ADD COLUMN submission_format TEXT")
    except sqlite3.OperationalError:
        pass

    # --- Migration: Announcements Advanced ---
    try:
        cursor.execute("ALTER TABLE announcements ADD COLUMN target_type TEXT DEFAULT 'all'")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE announcements ADD COLUMN target_email TEXT")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE announcements ADD COLUMN deadline TEXT")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE announcements ADD COLUMN attachment TEXT")
    except sqlite3.OperationalError: pass

    try:
        cursor.execute("ALTER TABLE user_papers ADD COLUMN faculty_deleted BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE user_papers ADD COLUMN admin_deleted BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE announcements ADD COLUMN admin_deleted BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError: pass

    # --- Faculty Announcement Deletions ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty_announcement_deletions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            announcement_id INTEGER NOT NULL,
            UNIQUE(user_email, announcement_id)
        )
    """)

    # --- Notifications Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            message TEXT NOT NULL,
            paper_id INTEGER,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE user_papers ADD COLUMN recovery_requested BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE user_papers ADD COLUMN faculty_perm_deleted BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError: pass

    # --- Announcement Reads Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcement_reads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            announcement_id INTEGER NOT NULL,
            read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_email, announcement_id)
        )
    """)
    
    conn.commit()
    st.cache_data.clear()
    conn.close()

def add_user(full_name, email, department, designation, password, role="faculty", subjects=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    hashed_pass = hashlib.sha256(password.encode()).hexdigest()
    try:
        cursor.execute("""
            INSERT INTO users (full_name, email, department, designation, password, role, status, subjects)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (full_name, email, department, designation, hashed_pass, role, "Active", subjects))
        conn.commit()
    st.cache_data.clear()
        return True, "Registration successful"
    except sqlite3.IntegrityError:
        return False, "Email already registered"
    except Exception as e:
        return False, str(e)
    finally:
        st.cache_data.clear() # Clear all caches on new user
        conn.close()

def verify_user(email, password, role=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    hashed_pass = hashlib.sha256(password.encode()).hexdigest()
    
    cursor.execute("SELECT full_name, role, department, designation, email FROM users WHERE email = ? AND password = ?", (email, hashed_pass))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        db_role = user[1]
        db_email = user[4]
        
        # Role Enforcement
        if role:
            if role == "admin":
                # Strict check for the primary admin account
                if db_email != "admin@gmail.com" or db_role != "admin":
                    return False, "Unauthorized: This login is restricted to the primary Administrator account."
            elif role == "faculty":
                if db_role != "faculty":
                    return False, "Unauthorized: This login is restricted to Faculty accounts only."
            elif db_role != role:
                return False, f"Unauthorized: Role mismatch (expected {role})."

        return True, {
            "name": user[0], 
            "role": user[1],
            "dept": user[2],
            "desig": user[3],
            "email": user[4]
        }
    return False, "Invalid credentials"

import json
import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)

def save_paper(email, paper_dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_papers (user_email, paper_data)
        VALUES (?, ?)
    """, (email, json.dumps(paper_dict, cls=DateTimeEncoder)))
    
    # Retrieve the id we just inserted so we can track it in the frontend
    last_id = cursor.lastrowid
    st.cache_data.clear() # Clear papers cache
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return last_id

@st.cache_data(ttl=300)
def get_user_papers(email, include_deleted=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if include_deleted:
        # Get only papers that ARE deleted by faculty but NOT permanently
        cursor.execute("""
            SELECT id, paper_data, status, admin_comments, is_downloaded, recovery_requested 
            FROM user_papers 
            WHERE user_email = ? AND faculty_deleted = 1 AND (faculty_perm_deleted = 0 OR faculty_perm_deleted IS NULL)
            ORDER BY created_at DESC
        """, (email,))
    else:
        # Standard view: Not deleted
        cursor.execute("""
            SELECT id, paper_data, status, admin_comments, is_downloaded 
            FROM user_papers 
            WHERE user_email = ? AND (faculty_deleted = 0 OR faculty_deleted IS NULL)
            ORDER BY created_at DESC
        """, (email,))
    rows = cursor.fetchall()
    conn.close()
    
    papers = []
    for r in rows:
        try:
            p = json.loads(r[1])
            p["db_id"] = r[0]
            p["id"] = r[0]
            p["approval_status"] = r[2]
            p["admin_comments"] = r[3]
            p["is_downloaded"] = bool(r[4])
            if include_deleted:
                p["recovery_requested"] = bool(r[5])
            papers.append(p)
        except:
            pass
    return papers

def delete_paper(paper_id, email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_papers SET faculty_deleted = 1 WHERE id = ? AND user_email = ?", (paper_id, email))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def delete_paper_admin(paper_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_papers SET admin_deleted = 1 WHERE id = ?", (paper_id,))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def restore_paper(paper_id):
    """Restore a paper for the faculty member."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_papers SET faculty_deleted = 0, recovery_requested = 0 WHERE id = ?", (paper_id,))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def request_paper_recovery(paper_id):
    """Mark a paper as recovery requested."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_papers SET recovery_requested = 1 WHERE id = ?", (paper_id,))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def get_paper_owner_email(paper_id):
    """Return the user_email for the given paper_id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_email FROM user_papers WHERE id = ?", (paper_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def permanently_delete_paper_faculty(paper_id, email):
    """Faculty permanently remove a paper from their trash."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_papers SET faculty_perm_deleted = 1 WHERE id = ? AND user_email = ?", (paper_id, email))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.full_name, u.email, u.department, u.designation, u.role, u.status, u.subjects, u.last_login,
               (SELECT COUNT(*) FROM user_papers WHERE user_email = u.email) as paper_count
        FROM users u
    """)
    users = cursor.fetchall()
    conn.close()
    return [{"name": u[0], "email": u[1], "dept": u[2], "desig": u[3], "role": u[4], 
             "status": u[5], "subjects": u[6], "last_login": u[7], "paper_count": u[8]} for u in users]

def reset_password(email, new_password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    hashed_pass = hashlib.sha256(new_password.encode()).hexdigest()
    cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_pass, email))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def delete_user(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Delete papers first
    cursor.execute("DELETE FROM user_papers WHERE user_email = ?", (email,))
    # Delete logs
    cursor.execute("DELETE FROM audit_logs WHERE user_email = ?", (email,))
    # Delete user
    cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def update_last_login(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE users SET last_login = ? WHERE email = ?", (now, email))
    conn.commit()
    st.cache_data.clear()
    conn.close()

def update_user_status(email, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE email = ?", (status, email))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def update_user_details(email, name, dept, desig, subjects):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET full_name = ?, department = ?, designation = ?, subjects = ?
        WHERE email = ?
    """, (name, dept, desig, subjects, email))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def get_faculty_metrics():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'faculty'")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'faculty' AND status = 'Active'")
    active = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'faculty' AND status = 'Banned'")
    banned = cursor.fetchone()[0]
    conn.close()
    return {"total": total, "active": active, "banned": banned}

def get_distinct_departments():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT department FROM users WHERE department IS NOT NULL AND department != ''")
    depts = [r[0] for r in cursor.fetchall()]
    conn.close()
    return sorted(depts)

@st.cache_data(ttl=300)
def get_all_papers_admin():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_email, paper_data, created_at, status, admin_comments, is_downloaded, admin_downloaded
        FROM user_papers 
        WHERE (admin_deleted = 0 OR admin_deleted IS NULL)
        AND status != 'Pending'
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    papers = []
    for r in rows:
        try:
            p = json.loads(r[2])
            p["db_id"] = r[0]
            p["user_email"] = r[1]
            p["created_at_raw"] = r[3]
            p["approval_status"] = r[4]
            p["admin_comments"] = r[5]
            p["is_downloaded"] = bool(r[6])
            p["admin_downloaded"] = bool(r[7])
            papers.append(p)
        except:
            pass
    return papers

def update_paper_approval(paper_id, status, comments):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get paper info and faculty email for notification
    cursor.execute("SELECT user_email, paper_data FROM user_papers WHERE id = ?", (paper_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    faculty_email = row[0]
    paper_name = "Question Paper"
    try:
        paper_data = json.loads(row[1])
        paper_name = paper_data.get("name", "Question Paper")
    except:
        pass

    cursor.execute("""
        UPDATE user_papers 
        SET status = ?, admin_comments = ? 
        WHERE id = ?
    """, (status, comments, paper_id))
    
    # Create notification for faculty
    msg = f"📝 Your paper '**{paper_name}**' status has been updated to **{status}**."
    if comments:
        msg += f" Feedback: {comments}"
        
    cursor.execute("""
        INSERT INTO notifications (user_email, message, paper_id)
        VALUES (?, ?, ?)
    """, (faculty_email, msg, paper_id))

    # Audit log for paper approval
    cursor.execute("INSERT INTO audit_logs (user_email, action, details) VALUES (?, ?, ?)", 
                   ("admin@gmail.com", "Paper Status Updated", f"Paper {paper_name} ({paper_id}) set to {status}"))
    
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def mark_paper_downloaded(paper_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_papers SET is_downloaded = 1 WHERE id = ?", (paper_id,))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def mark_paper_downloaded_admin(paper_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_papers SET admin_downloaded = 1 WHERE id = ?", (paper_id,))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def submit_paper(paper_id, format_type):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_papers 
        SET status = 'Submitted', submission_format = ? 
        WHERE id = ?
    """, (format_type, paper_id))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def add_notification(email, message, paper_id=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notifications (user_email, message, paper_id)
        VALUES (?, ?, ?)
    """, (email, message, paper_id))
    st.cache_data.clear()
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

@st.cache_data(ttl=60)
def get_notifications(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, message, paper_id, created_at, is_read 
        FROM notifications 
        WHERE user_email = ? 
        ORDER BY created_at DESC
    """, (email,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "message": r[1], "paper_id": r[2], "time": r[3], "is_read": bool(r[4])} for r in rows]

def mark_notification_read(notif_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

def mark_all_notifications_read(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_email = ?", (email,))
    st.cache_data.clear()
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return True

@st.cache_data(ttl=60)
def get_unread_notification_count(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_email = ? AND is_read = 0", (email,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_admin_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Active papers only (not admin_deleted and not faculty_perm_deleted)
    # Filter: Only show submitted papers to admin (status != 'Pending')
    filter_sql = "WHERE (admin_deleted = 0 OR admin_deleted IS NULL) AND (faculty_perm_deleted = 0 OR faculty_perm_deleted IS NULL) AND status != 'Pending'"
    
    cursor.execute(f"SELECT COUNT(*) FROM users WHERE role = 'faculty'")
    total_faculty = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM user_papers {filter_sql}")
    total_papers = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM user_papers {filter_sql} AND date(created_at) = date('now')")
    today_papers = cursor.fetchone()[0]
    
    active_now = get_active_now_count()
    
    conn.close()
    return {
        "total_faculty": total_faculty,
        "total_papers": total_papers,
        "today_papers": today_papers,
        "active_now": active_now
    }

def get_active_now_count(minutes=15):
    """Calculate unique users active within the last X minutes based on audit logs."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # SQLite CURRENT_TIMESTAMP is UTC. 
    # We check for users who performed any action in the last X minutes.
    cursor.execute("""
        SELECT COUNT(DISTINCT user_email) 
        FROM audit_logs 
        WHERE timestamp >= datetime('now', ?)
    """, (f'-{minutes} minutes',))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count if count > 0 else 1 # Minimum 1 (the current user)

def add_audit_log(email, action, details):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_logs (user_email, action, details) VALUES (?, ?, ?)", (email, action, details))
    conn.commit()
    st.cache_data.clear()
    conn.close()

def clear_old_audit_logs(days_back):
    """Delete logs older than X days."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit_logs WHERE timestamp < datetime('now', ?)", (f'-{days_back} days',))
    deleted_count = cursor.rowcount
    conn.commit()
    st.cache_data.clear()
    conn.close()
    return deleted_count

def get_audit_logs(limit=50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, user_email, action, details FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    logs = cursor.fetchall()
    conn.close()
    return [{"time": l[0], "user": l[1], "action": l[2], "details": l[3]} for l in logs]

def delete_announcement(ann_id):
    """Admin soft-delete an announcement."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE announcements SET admin_deleted = 1 WHERE id = ?", (ann_id,))
        conn.commit()
    st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error deleting announcement: {e}")
        return False
    finally:
        conn.close()

def delete_announcement_faculty(email, ann_id):
    """Faculty hide an announcement from their view."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO faculty_announcement_deletions (user_email, announcement_id) VALUES (?, ?)", (email, ann_id))
        conn.commit()
    st.cache_data.clear()
        return True
    except:
        return False
    finally:
        conn.close()

def get_announcements(user_email=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if user_email:
        # Faculty View: Show all targeted announcements EXCEPT those deleted by the faculty
        cursor.execute("""
            SELECT a.id, a.title, a.message, a.type, a.target_type, a.target_email, a.deadline, a.attachment, a.created_at 
            FROM announcements a
            LEFT JOIN faculty_announcement_deletions d ON a.id = d.announcement_id AND d.user_email = ?
            WHERE (a.target_type = 'all' OR a.target_email = ?)
            AND d.id IS NULL
            ORDER BY a.created_at DESC
        """, (user_email, user_email))
    else:
        # Admin View: Show all announcements NOT deleted by admin
        cursor.execute("""
            SELECT id, title, message, type, target_type, target_email, deadline, attachment, created_at 
            FROM announcements 
            WHERE admin_deleted = 0 OR admin_deleted IS NULL
            ORDER BY created_at DESC
        """)
    anns = cursor.fetchall()
    conn.close()
    return [{"id": a[0], "title": a[1], "message": a[2], "type": a[3], 
             "target_type": a[4], "target_email": a[5], "deadline": a[6], 
             "attachment": a[7], "created_at": a[8]} for a in anns]

def mark_announcement_read(email, ann_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO announcement_reads (user_email, announcement_id) VALUES (?, ?)", (email, ann_id))
        conn.commit()
    st.cache_data.clear()
        return True
    except:
        return False
    finally:
        st.cache_data.clear()
        conn.close()

@st.cache_data(ttl=60)
def get_unread_announcement_count(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Announcements where target is 'all' or matches email, AND NOT in announcement_reads for this email
    cursor.execute("""
        SELECT COUNT(*) FROM announcements a
        WHERE (a.target_type = 'all' OR a.target_email = ?)
        AND NOT EXISTS (
            SELECT 1 FROM announcement_reads ar 
            WHERE ar.user_email = ? AND ar.announcement_id = a.id
        )
    """, (email, email))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def add_announcement(title, message, type, target_type='all', target_email=None, deadline=None, attachment=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO announcements (title, message, type, target_type, target_email, deadline, attachment) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, message, type, target_type, target_email, deadline, attachment))
    conn.commit()
    st.cache_data.clear()
    conn.close()

def get_system_settings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM system_settings")
    settings = dict(cursor.fetchall())
    conn.close()
    return settings

def update_system_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    st.cache_data.clear()
    conn.close()

def get_db_raw_data(table_name):
    """Utility to browse any table (Admin only use)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        cols = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        return cols, rows
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
