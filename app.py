# app.py
import os
import re
import math
import requests
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import date, datetime

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv(".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Optional Slack webhooks for write-up system
SLACK_ALERT_WEBHOOK_URL = os.getenv("SLACK_ALERT_WEBHOOK_URL", "").strip()
SLACK_WRITEUP_WEBHOOK_URL = os.getenv("SLACK_WRITEUP_WEBHOOK_URL", "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing SUPABASE_URL or SUPABASE_KEY in your .env file.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# Streamlit config
# -----------------------------
st.set_page_config(
    page_title="Chick-fil-A Staten Island Mall",
    layout="centered"
)

# -----------------------------
# Master Director Login
# -----------------------------
MASTER_USERNAME = "Lauren.Cardieri"
MASTER_PASSWORD = "952426"

# -----------------------------
# Roles / labels
# -----------------------------
ROLE_LABELS = {
    "team_member": "Team Member",
    "trainer": "Trainer",
    "shift_lead": "Shift Lead",
    "supervisor": "Supervisor",
    "director": "Director"
}

ROLE_HIERARCHY = {
    "team_member": 1,
    "trainer": 2,
    "shift_lead": 3,
    "supervisor": 4,
    "director": 5
}

ALL_ROLES = ["team_member", "trainer", "shift_lead", "supervisor", "director"]

# -----------------------------
# Categories
# -----------------------------
CATEGORIES = [
    "Customer Experience",
    "Drive-Thru",
    "Training Department",
    "Sales & Brand Growth",
    "Food Safety/Food Quality",
    "Human Resources",
    "Maintenance",
    "Leadership Homepage"
]

GOOGLE_CALENDAR_EMBED_URL = (
    "https://calendar.google.com/calendar/embed?"
    "src=d757b8e25bc807bd91d044deb502bd0aa1dc012048b1a11803faa64fda03b4bc%40group.calendar.google.com"
    "&ctz=America%2FNew_York"
)

GOAL_STATUS_OPTIONS = [
    "Not Started",
    "In Progress",
    "On Track",
    "At Risk",
    "Completed"
]

# -----------------------------
# Write-Up System constants
# -----------------------------
BENCHMARKS = {
    "Good Standing": {"min": 0, "max": 9, "color": "#28a745"},
    "Borderline": {"min": 10, "max": 19, "color": "#ffc107"},
    "Suspension": {"min": 20, "max": 24, "color": "#fd7e14"},
    "Fired": {"min": 25, "max": 10**9, "color": "#dc3545"},
}
STANDING_ORDER = ["Good Standing", "Borderline", "Suspension", "Fired"]

HANDBOOK_BY_RULE = {
    "No Call No Show": (
        "Employees are expected to be punctual and regular in attendance. Employees are expected to report to work "
        "as scheduled, on time and prepared to start work at the beginning of their shifts and at the end of meal "
        "periods. Late arrival, early departure or other absences from scheduled hours are disruptive and should be avoided."
    ),
    "Late by 6 or more minutes": (
        "Employees are expected to be punctual and regular in attendance. Employees are expected to report to work "
        "as scheduled, on time and prepared to start work at the beginning of their shifts and at the end of meal "
        "periods. Late arrival, early departure or other absences from scheduled hours are disruptive and should be avoided."
    ),
    "Called out with less than 2 hour notice": (
        "If you will be absent from or tardy for work for any reason, you must call your supervisor as soon as possible, "
        "but at least two hours before the beginning of your scheduled shift, and advise of the reason for your absence "
        "or tardiness and when you expect to return to work. Obviously, if you know of a required absence from work in advance, "
        "you must inform your supervisor as far in advance as possible, so that Chick-fil-A at Staten Island Mall can adjust "
        "the work schedule accordingly. In certain instances, subject to applicable law, if an absence is to exceed one day, "
        "you may be required to provide your supervisor with an update at the beginning of each day of the absence, until a "
        "return to work date has been established.\n\n"
        "Chick-fil-A at Staten Island Mall reserves the right to discipline employees for unexcused absences (including late arrivals "
        "or early departures), up to and including termination of employment, in accordance with the Progressive Discipline Policy."
    ),
    "Called out without finding coverage": (
        "If you will be absent from or tardy for work for any reason, you must call your supervisor as soon as possible, "
        "but at least two hours before the beginning of your scheduled shift, and advise of the reason for your absence "
        "or tardiness and when you expect to return to work. Obviously, if you know of a required absence from work in advance, "
        "you must inform your supervisor as far in advance as possible, so that Chick-fil-A at Staten Island Mall can adjust "
        "the work schedule accordingly. In certain instances, subject to applicable law, if an absence is to exceed one day, "
        "you may be required to provide your supervisor with an update at the beginning of each day of the absence, until a "
        "return to work date has been established.\n\n"
        "Chick-fil-A at Staten Island Mall reserves the right to discipline employees for unexcused absences (including late arrivals "
        "or early departures), up to and including termination of employment, in accordance with the Progressive Discipline Policy."
    ),
    "Called out 4 times in one month": (
        "Chick-fil-A at Staten Island Mall reserves the right to discipline employees for unexcused absences (including late arrivals "
        "or early departures), up to and including termination of employment, in accordance with the Progressive Discipline Policy. "
        "Excessive absenteeism or tardiness."
    ),
    "Exceeded break time by 3 or more minutes": (
        "Employees also are expected to remain at work for their entire work schedule, except for meal periods or when required to leave "
        "on authorized Chick-fil-A at Staten Island Mall business."
    ),
    "Staying past scheduled time (5+ minutes)": (
        "Non-exempt employees are not permitted to work beyond their normal work schedule without the express written approval of their "
        "Director or the Owner/Operator."
    ),
    "Incomplete uniform": (
        "All uniforms items (including belts, outerwear, and caps) must be from Chick-fil-A team style collection. All garments should fit properly "
        "and be cleaned, pressed, (as applicable) and in good condition (i.e., no holes, fraying, stains, discoloring, etc.)."
    ),
    "Drawer short/over $10+": (
        "You are responsible for the cash and coupons that you process during your shift. It is necessary in our business that we take this "
        "Cash and Coupon Accountability Policy extremely seriously. Any action by an employee contrary to this policy will result in disciplinary action, "
        "up to and including termination of employment, in accordance with the Progressive Discipline Policy."
    ),
    "Drawer short/over $3+": (
        "You are responsible for the cash and coupons that you process during your shift. It is necessary in our business that we take this "
        "Cash and Coupon Accountability Policy extremely seriously. Any action by an employee contrary to this policy will result in disciplinary action, "
        "up to and including termination of employment, in accordance with the Progressive Discipline Policy."
    ),
    "Damaging equipment due to negligence": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Abuse, damage or deliberate destruction of Chick-fil-A at Staten Island Mall’s or a guest’s property or the property of Chick-fil-A at Staten Island Mall employees or vendors.
""",
    "Poor work performance": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Failure to maintain satisfactory productivity and quality of work.
""",
    "Breach of safety procedures": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Failing to properly report an injury or accident or falsely claiming injury.
- Violation of or disregard of the rules and regulations stated in this manual or in other Chick-fil-A at Staten Island Mall policy.
""",
    "Using cell phone for personal use": (
        "Unless otherwise authorized by a director or the Owner/Operator, cell phones and other personal electronic devices may not be visible or used while you are working. "
        "If you choose to bring a personal cell phone or similar device to work, it must be turned off or to “silent” mode so as not to be disruptive to the workplace.\n\n"
        "Chick-fil-A at Staten Island Mall prohibits employees from using any personal electronic device while driving during work time or while operating "
        "Chick-fil-A at Staten Island Mall vehicles, equipment or machinery. Violation of this policy may lead to disciplinary action, up to and including termination "
        "of employment, in accordance with the Progressive Discipline Policy."
    ),
    "Engaging in personal work while on the clock": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Outside employment or activities which interfere with regular working hours or productivity.
""",
    "Failure to fulfill job expectations": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Failure to maintain satisfactory productivity and quality of work.
""",
    "Harassment, bullying, or victimization": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Making false or disparaging statements or spreading rumors.
- Use of profanity or abusive language toward employees, guests, or vendors.
- Violence or threatening behavior.
- Disorderly conduct on company property.
""",
    "Disrespectful behavior": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Making false and disparaging statements or spreading rumors which might harm the reputation of our employees or guests.
- Use of profanity or abusive language toward employees, guests or other persons on Chick-fil-A at Staten Island Mall’s premises or while performing Chick-fil-A at Staten Island Mall work.
- Violence or threatening behavior.
- Disorderly conduct on Chick-fil-A at Staten Island Mall property, such as horseplay, threatening, insulting or abusing any employee, guest or vendor or fighting or attempting bodily injury of anyone.
""",
    "Refusal to obey management instructions": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Insubordination or refusal or failure to obey instructions.
""",
    "Use of profanity": (
        "Use of profanity or abusive language toward employees, guests or other persons on Chick-fil-A at Staten Island Mall’s premises "
        "or while performing Chick-fil-A at Staten Island Mall work."
    ),
    "Violent behavior": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Violence or threatening behavior.
- Disorderly conduct on Chick-fil-A at Staten Island Mall property, such as horseplay, threatening, insulting or abusing any employee, guest or vendor or fighting or attempting bodily injury of anyone.
""",
    "Theft or fraud": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Theft, misuse or unauthorized possession or removal of Chick-fil-A at Staten Island Mall, employee, vendor or guest property.
""",
    "Endangering health or safety": """
**Egregious Misconduct**

Includes criminal conduct or conduct that seriously harms or immediately threatens the health and safety of other employees or members of the public, including, without limitation:

- Disorderly conduct on Chick-fil-A at Staten Island Mall property, such as horseplay, threatening, insulting or abusing any employee, guest or vendor, or fighting or attempting bodily injury of anyone.
- Using, possessing, passing, or selling, or working or reporting to work under the influence of, alcoholic beverages or any drug, narcotic or other controlled substance on Chick-fil-A at Staten Island Mall premises at any time or while performing Chick-fil-A at Staten Island Mall work.
- Possession of dangerous weapons or firearms on Chick-fil-A at Staten Island Mall premises.
""",
    "Leaving workplace without permission": (
        "Employees are expected to be punctual and regular in attendance. Employees are expected to report to work as scheduled, on time and prepared to start work at the beginning "
        "of their shifts and at the end of meal periods. Late arrival, early departure or other absences from scheduled hours are disruptive and should be avoided."
    ),
}

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1100px;
        }

        .page-title {
            text-align: center;
            margin-bottom: 0.2rem;
        }

        .page-subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 1rem;
        }

        .link-meta {
            color: #666;
            font-size: 0.9rem;
            margin-top: 0.35rem;
            margin-bottom: 0.5rem;
        }

        .admin-panel {
            border: 1px solid #e8e8e8;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
            background: #fafafa;
        }

        hr.soft-divider {
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 1rem 0;
        }

        div[data-testid="stToggle"] {
            margin-top: 0.35rem;
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Session helpers
# -----------------------------
def init_session():
    defaults = {
        "logged_in": False,
        "profile": None,

        "pending_delete_writeup_id": None,
        "pending_delete_member_id": None,
        "pending_delete_category_id": None,
        "pending_delete_username": None,
        "search_name": "",
        "selected_member_id": None,

        "admin_browse_index": 0,
        "admin_browse_ids": [],
        "admin_browse_cache": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def logout_user():
    st.session_state.logged_in = False
    st.session_state.profile = None
    st.session_state.pending_delete_writeup_id = None
    st.session_state.pending_delete_member_id = None
    st.session_state.pending_delete_category_id = None
    st.session_state.pending_delete_username = None
    st.session_state.selected_member_id = None
    st.session_state.admin_browse_index = 0
    st.session_state.admin_browse_ids = []
    st.session_state.admin_browse_cache = []
    st.rerun()

def has_role(required_role: str) -> bool:
    profile = st.session_state.profile
    if not profile:
        return False
    user_role = profile.get("role", "")
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 999)

def get_current_role():
    profile = st.session_state.profile or {}
    return profile.get("role", "team_member")

def get_current_username():
    profile = st.session_state.profile or {}
    return profile.get("username", "unknown")

def get_current_category():
    profile = st.session_state.profile or {}
    return profile.get("category", "")

def get_current_full_name():
    profile = st.session_state.profile or {}
    return profile.get("full_name", "User")

# -----------------------------
# Permission helpers
# -----------------------------
def user_owns_category(category: str) -> bool:
    if get_current_role() == "director":
        return True
    return get_current_category() == category

def can_request_links_in_category(category: str) -> bool:
    return get_current_role() in ["trainer", "shift_lead"] and user_owns_category(category)

def can_post_directly_in_category(category: str) -> bool:
    if get_current_role() == "director":
        return True
    return get_current_role() == "supervisor" and user_owns_category(category)

def can_review_links_in_category(category: str) -> bool:
    if get_current_role() == "director":
        return True
    return get_current_role() == "supervisor" and user_owns_category(category)

def can_manage_links_in_category(category: str) -> bool:
    if get_current_role() == "director":
        return True
    return get_current_role() == "supervisor" and user_owns_category(category)

def can_enter_edit_mode(category: str) -> bool:
    return (
        can_request_links_in_category(category)
        or can_post_directly_in_category(category)
        or can_manage_links_in_category(category)
    )

def can_view_suggestions_tab() -> bool:
    return get_current_role() in ["supervisor", "director"]

def can_manage_goals() -> bool:
    return get_current_role() == "director"

def can_update_goal_status() -> bool:
    return get_current_role() in ["supervisor", "director"]

def can_enter_home_edit_mode() -> bool:
    return can_manage_goals() or can_update_goal_status()

# Write-up system permissions
def can_view_writeup_system() -> bool:
    return has_role("team_member")

def can_use_writeup_manager_mode() -> bool:
    return get_current_role() in ["shift_lead", "supervisor", "director"]

def can_use_writeup_admin_mode() -> bool:
    return get_current_role() == "director"

# -----------------------------
# Username generation helpers
# -----------------------------
def clean_name_for_username(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-zA-Z\s\-]", "", name)
    name = name.replace("-", " ")
    parts = [p for p in name.split() if p]

    if len(parts) == 0:
        return "user"
    if len(parts) == 1:
        return parts[0]

    return f"{parts[0]}.{parts[-1]}"

def username_exists(username: str) -> bool:
    try:
        result = (
            supabase.table("users")
            .select("id")
            .eq("username", username)
            .execute()
        )
        return len(result.data) > 0
    except Exception as e:
        st.error(f"Error checking username: {e}")
        return True

def generate_unique_username(full_name: str) -> str:
    base_username = clean_name_for_username(full_name)

    if not username_exists(base_username):
        return base_username

    counter = 2
    while True:
        candidate = f"{base_username}{counter}"
        if not username_exists(candidate):
            return candidate
        counter += 1

# -----------------------------
# User database helpers
# -----------------------------
def fetch_user_by_username(username: str):
    try:
        result = (
            supabase.table("users")
            .select("*")
            .ilike("username", username)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        st.error(f"Error loading user: {e}")
        return None

def login_with_username(username: str, password: str):
    if username.strip().lower() == MASTER_USERNAME.lower() and password == MASTER_PASSWORD:
        return {
            "full_name": "Lauren Cardieri",
            "username": MASTER_USERNAME,
            "role": "director",
            "category": "",
            "active": True
        }

    user = fetch_user_by_username(username.strip())

    if not user:
        return None

    if not user.get("active", True):
        st.error("This account is inactive.")
        return None

    if user.get("password") != password:
        return None

    return user

def create_user_account(full_name: str, password: str, role: str, category: str, active: bool = True):
    try:
        username = generate_unique_username(full_name)

        insert_data = {
            "username": username,
            "password": password,
            "full_name": full_name,
            "role": role,
            "category": "" if role in ["director", "team_member"] else category,
            "active": active
        }

        result = supabase.table("users").insert(insert_data).execute()
        if result.data:
            return True, username
        return False, None

    except Exception as e:
        st.error(f"Error creating user: {e}")
        return False, None

def get_all_users():
    try:
        result = (
            supabase.table("users")
            .select("id, username, full_name, role, category, active, created_at")
            .order("full_name")
            .execute()
        )
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return []

def update_user_details(user_id, role, category, active, new_password=None):
    try:
        update_data = {
            "role": role,
            "category": "" if role in ["director", "team_member"] else category,
            "active": active
        }

        if new_password and new_password.strip():
            update_data["password"] = new_password.strip()

        (
            supabase.table("users")
            .update(update_data)
            .eq("id", user_id)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"Error updating user details: {e}")
        return False

def delete_user_account(user_id):
    try:
        supabase.table("users").delete().eq("id", user_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        return False

# -----------------------------
# Link visibility helpers
# -----------------------------
def get_allowed_view_roles_for_poster(category: str):
    role = get_current_role()

    if role == "director":
        return ALL_ROLES
    if role == "supervisor" and user_owns_category(category):
        return ["team_member", "trainer", "shift_lead", "supervisor"]
    if role == "shift_lead" and user_owns_category(category):
        return ["team_member", "trainer", "shift_lead"]
    if role == "trainer" and user_owns_category(category):
        return ["team_member", "trainer"]

    return []

def can_user_view_link(link: dict) -> bool:
    current_role_level = ROLE_HIERARCHY.get(get_current_role(), 0)
    min_view_role = link.get("min_view_role", "team_member")
    min_view_level = ROLE_HIERARCHY.get(min_view_role, 1)
    return current_role_level >= min_view_level

# -----------------------------
# Resource link helpers
# -----------------------------
def get_links_for_category(category: str):
    try:
        result = (
            supabase.table("resource_links")
            .select("*")
            .eq("category", category)
            .eq("status", "approved")
            .eq("visible", True)
            .order("created_at", desc=True)
            .execute()
        )

        links = result.data if result.data else []
        visible_links = [link for link in links if can_user_view_link(link)]

        visible_links.sort(
            key=lambda link: (
                ROLE_HIERARCHY.get(link.get("min_view_role", "team_member"), 1),
                -(link.get("id", 0))
            )
        )
        return visible_links

    except Exception as e:
        st.error(f"Error loading links: {e}")
        return []

def get_suggestions_for_current_user():
    try:
        result = (
            supabase.table("resource_links")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=True)
            .execute()
        )

        links = result.data if result.data else []

        if get_current_role() == "director":
            return links

        if get_current_role() == "supervisor":
            return [link for link in links if link.get("category") == get_current_category()]

        return []

    except Exception as e:
        st.error(f"Error loading suggestions: {e}")
        return []

def create_link_submission(category: str, system_name: str, external_url: str, description: str, min_view_role: str):
    try:
        username = get_current_username()
        role = get_current_role()

        status = "pending"
        visible = False
        approved_by_username = None

        if role == "director":
            status = "approved"
            visible = True
            approved_by_username = username
        elif role == "supervisor" and user_owns_category(category):
            status = "approved"
            visible = True
            approved_by_username = username
        elif role in ["trainer", "shift_lead"] and user_owns_category(category):
            status = "pending"
            visible = False
        else:
            return False

        insert_data = {
            "category": category,
            "system_name": system_name.strip(),
            "external_url": external_url.strip(),
            "description": description.strip(),
            "submitted_by_username": username,
            "submitted_by_role": role,
            "status": status,
            "visible": visible,
            "approved_by_username": approved_by_username,
            "min_view_role": min_view_role
        }

        result = supabase.table("resource_links").insert(insert_data).execute()
        return bool(result.data)

    except Exception as e:
        st.error(f"Error creating link: {e}")
        return False

def approve_link(link_id: int):
    try:
        approver = get_current_username()
        (
            supabase.table("resource_links")
            .update({
                "status": "approved",
                "visible": True,
                "approved_by_username": approver
            })
            .eq("id", link_id)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"Error approving link: {e}")
        return False

def reject_link(link_id: int):
    try:
        (
            supabase.table("resource_links")
            .update({
                "status": "rejected",
                "visible": False
            })
            .eq("id", link_id)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"Error rejecting link: {e}")
        return False

def delete_link(link_id: int):
    try:
        supabase.table("resource_links").delete().eq("id", link_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting link: {e}")
        return False

def update_link(link_id: int, category: str, system_name: str, external_url: str, description: str, min_view_role: str):
    try:
        (
            supabase.table("resource_links")
            .update({
                "category": category,
                "system_name": system_name.strip(),
                "external_url": external_url.strip(),
                "description": description.strip(),
                "min_view_role": min_view_role
            })
            .eq("id", link_id)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"Error updating link: {e}")
        return False

# -----------------------------
# Goal helpers
# -----------------------------
def get_goals_by_type(goal_type: str):
    try:
        result = (
            supabase.table("store_goals")
            .select("*")
            .eq("goal_type", goal_type)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error loading goals: {e}")
        return []

def create_goal(goal_type: str, goal_title: str, goal_description: str):
    try:
        result = (
            supabase.table("store_goals")
            .insert({
                "goal_type": goal_type,
                "goal_title": goal_title.strip(),
                "goal_description": goal_description.strip(),
                "created_by_username": get_current_username()
            })
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        st.error(f"Error creating goal: {e}")
        return False

def update_goal(goal_id: int, goal_title: str, goal_description: str):
    try:
        (
            supabase.table("store_goals")
            .update({
                "goal_title": goal_title.strip(),
                "goal_description": goal_description.strip()
            })
            .eq("id", goal_id)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"Error updating goal: {e}")
        return False

def delete_goal(goal_id: int):
    try:
        (
            supabase.table("store_goals")
            .update({"is_active": False})
            .eq("id", goal_id)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"Error deleting goal: {e}")
        return False

def get_goal_updates(goal_id: int):
    try:
        result = (
            supabase.table("goal_updates")
            .select("*")
            .eq("goal_id", goal_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error loading goal updates: {e}")
        return []

def add_goal_update(goal_id: int, status_label: str, update_note: str):
    try:
        result = (
            supabase.table("goal_updates")
            .insert({
                "goal_id": goal_id,
                "status_label": status_label,
                "update_note": update_note.strip(),
                "updated_by_username": get_current_username()
            })
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        st.error(f"Error adding goal update: {e}")
        return False

# -----------------------------
# Write-Up helpers
# -----------------------------
def standing_label(points: int) -> str:
    p = int(points or 0)
    if p < 10:
        return "Good Standing"
    if 10 <= p <= 19:
        return "Borderline"
    if 20 <= p <= 24:
        return "Suspension"
    return "Fired"

def standing_color(label: str) -> str:
    return BENCHMARKS.get(label, {}).get("color", "#6c757d")

def standing_badge(label: str, points: int, caption: str = ""):
    color = standing_color(label)
    st.markdown(
        f"""
        <div style="
            padding: 12px 14px;
            border-radius: 10px;
            background: {color};
            color: white;
            font-weight: 800;
            display: inline-block;
            margin-bottom: 6px;
        ">
            {label} — {int(points or 0)} pts
        </div>
        """,
        unsafe_allow_html=True,
    )
    if caption:
        st.caption(caption)

def parse_iso_date(d):
    if not d:
        return None
    try:
        if isinstance(d, str):
            return datetime.fromisoformat(d.replace("Z", "+00:00")).date()
        if isinstance(d, datetime):
            return d.date()
        if isinstance(d, date):
            return d
    except Exception:
        return None
    return None

def quarter_key(d: date) -> str:
    q = (d.month - 1) // 3 + 1
    return f"{d.year} Q{q}"

def current_quarter_key(today: date = None) -> str:
    today = today or date.today()
    return quarter_key(today)

def build_quarter_totals(writeups: list) -> pd.DataFrame:
    bucket = {}
    for w in (writeups or []):
        d = parse_iso_date(w.get("incident_date"))
        if not d:
            continue
        k = quarter_key(d)
        bucket[k] = bucket.get(k, 0) + int(w.get("points") or 0)

    df = pd.DataFrame([{"quarter": k, "points": v} for k, v in bucket.items()])
    if df.empty:
        return df

    def _sort_key(qstr):
        y, q = qstr.split()
        return int(y), int(q.replace("Q", ""))

    df["sort"] = df["quarter"].apply(_sort_key)
    df = df.sort_values("sort").drop(columns=["sort"]).reset_index(drop=True)
    return df

def points_in_quarter(writeups: list, quarter_label: str) -> int:
    total = 0
    for w in (writeups or []):
        d = parse_iso_date(w.get("incident_date"))
        if not d:
            continue
        if quarter_key(d) == quarter_label:
            total += int(w.get("points") or 0)
    return total

def all_time_points(writeups: list) -> int:
    return sum(int(w.get("points") or 0) for w in (writeups or []))

def calc_late_points(minutes_late: int) -> int:
    if minutes_late is None:
        return 0
    m = int(minutes_late)
    if m < 6:
        return 0
    return 1 + (m - 5) // 10

def format_writeup_notes(
    reason: str,
    manager_notes: str,
    secondary_lead_witness: str,
    corrective_actions: str,
    team_member_comments: str,
    team_member_signature: str,
    leader_signature: str,
    secondary_leader_signature: str,
    signed_date: date,
) -> str:
    reason = (reason or "").strip()
    manager_notes = (manager_notes or "").strip()
    secondary_lead_witness = (secondary_lead_witness or "").strip()
    corrective_actions = (corrective_actions or "").strip()
    team_member_comments = (team_member_comments or "").strip()
    team_member_signature = (team_member_signature or "").strip()
    leader_signature = (leader_signature or "").strip()
    secondary_leader_signature = (secondary_leader_signature or "").strip()

    parts = []
    parts.append(f"Reason: {reason}")

    if manager_notes:
        parts.append("\nManager Notes:\n" + manager_notes)
    if secondary_lead_witness:
        parts.append("\nSecondary Lead Witnessing Write-Up:\n" + secondary_lead_witness)
    if corrective_actions:
        parts.append("\nCorrective Actions:\n" + corrective_actions)
    if team_member_comments:
        parts.append("\nTeam Member Comments:\n" + team_member_comments)

    parts.append("\nSignatures:")
    parts.append(f"- Team Member Signature: {team_member_signature if team_member_signature else '________________'}")
    parts.append(f"- Leader Signature: {leader_signature if leader_signature else '________________'}")
    parts.append(f"- Secondary Leader Signature: {secondary_leader_signature if secondary_leader_signature else '________________'}")
    parts.append(f"- Date Signed: {signed_date.isoformat() if signed_date else date.today().isoformat()}")

    return "\n".join(parts)

# -----------------------------
# Slack helpers
# -----------------------------
def slack_post(webhook_url: str, text: str):
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json={"text": text}, timeout=10)
    except Exception:
        pass

def extract_lead_names_from_notes(notes: str):
    if not notes:
        return "", ""
    leader = ""
    secondary = ""
    m1 = re.search(r"Leader Signature:\s*(.*)", notes)
    m2 = re.search(r"Secondary Leader Signature:\s*(.*)", notes)
    if m1:
        leader = (m1.group(1) or "").strip()
    if m2:
        secondary = (m2.group(1) or "").strip()
    return leader, secondary

def extract_reason_from_notes(notes: str):
    if not notes:
        return ""
    m = re.search(r"^Reason:\s*(.*)$", notes, flags=re.MULTILINE)
    return (m.group(1).strip() if m else "")

def post_writeup_to_slack(member_name: str, category_name: str, incident_date: str, notes: str):
    if not SLACK_WRITEUP_WEBHOOK_URL:
        return
    reason = extract_reason_from_notes(notes)
    leader, secondary = extract_lead_names_from_notes(notes)
    msg = (
        f"*New Write-Up Logged*\n"
        f"• Date: {incident_date}\n"
        f"• Team Member: {member_name}\n"
        f"• Category: {category_name}\n"
        f"• Reason: {reason if reason else '(not provided)'}\n"
        f"• Lead: {leader if leader else '(not provided)'}\n"
        f"• Secondary Lead: {secondary if secondary else '(not provided)'}"
    )
    slack_post(SLACK_WRITEUP_WEBHOOK_URL, msg)

def maybe_post_standing_alert(member_name: str, quarter_label: str, prev_label: str, new_label: str, q_points: int):
    if not SLACK_ALERT_WEBHOOK_URL:
        return
    watch = {"Borderline", "Suspension", "Fired"}
    if new_label in watch and new_label != prev_label:
        msg = (
            f"*Standing Alert*\n"
            f"• Team Member: {member_name}\n"
            f"• Quarter: {quarter_label}\n"
            f"• Standing: {prev_label} → *{new_label}*\n"
            f"• Quarter Points: {q_points}"
        )
        slack_post(SLACK_ALERT_WEBHOOK_URL, msg)

# -----------------------------
# Write-Up Supabase helpers
# -----------------------------
def fetch_team_members(search: str = "", include_inactive: bool = False):
    q = supabase.from_("users").select("id, full_name, active, created_at, role")

    if search.strip():
        s = search.strip()
        q = q.ilike("full_name", f"%{s}%")

    if not include_inactive:
        q = q.eq("active", True)

    q = q.order("full_name")
    return q.execute().data or []

def fetch_categories(include_inactive: bool = False):
    q = supabase.from_("writeup_categories").select("id, name, default_points, is_active").order("name")
    if not include_inactive:
        q = q.eq("is_active", True)
    return q.execute().data or []

def fetch_rules_for_category(category_id):
    return (
        supabase.from_("writeup_rules")
        .select("id, rule_name, base_points, is_incremental, increment_minutes, increment_points, notes")
        .eq("category_id", category_id)
        .order("rule_name")
        .execute()
        .data
        or []
    )

def fetch_writeups_for_member(member_id):
    res = (
        supabase.from_("writeups")
        .select("id, points, incident_date, notes, created_by, created_at, writeup_categories(name)")
        .eq("user_id", member_id)
        .order("incident_date", desc=True)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []

def add_writeup(member_id, category_id, points, incident_date, notes, created_by):
    payload = {
        "user_id": member_id,
        "category_id": category_id,
        "points": int(points),
        "incident_date": incident_date.isoformat(),
        "notes": notes.strip() if notes else None,
        "created_by": created_by,
    }
    return supabase.from_("writeups").insert(payload).execute().data

def delete_writeup(writeup_id):
    supabase.from_("writeups").delete().eq("id", writeup_id).execute()


def delete_team_member(member_id: str):
    supabase.from_("writeups").delete().eq("user_id", member_id).execute()
    supabase.from_("users").delete().eq("id", member_id).execute()

def fetch_all_writeups_chronological():
    return (
        supabase.from_("writeups")
        .select(
            "id, points, incident_date, notes, created_by, created_at, "
            "team_user:users!writeups_user_id_fkey(full_name), "
            "writeup_categories(name)"
        )
        .order("incident_date", desc=True)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
# -----------------------------
# UI helpers
# -----------------------------
def show_logo():
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 1rem;">
            <img
                src="https://image-handler.workstream.is/fit-in/512x512/production/uploads/brand/logo/25456/b5e811b29339f2735850dbe36c96462b.png"
                width="220"
            />
        </div>
        """,
        unsafe_allow_html=True
    )

def section_header(title: str, subtitle: str | None = None):
    st.markdown(f"<h2 class='page-title'>{title}</h2>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div class='page-subtitle'>{subtitle}</div>", unsafe_allow_html=True)

def render_edit_mode_toggle(category: str) -> bool:
    if not can_enter_edit_mode(category):
        return False

    col1, col2 = st.columns([1.2, 4.8])
    with col1:
        edit_mode = st.toggle("Edit Mode", key=f"edit_mode_{category}")
    with col2:
        if edit_mode:
            st.caption("Edit mode is on. Management tools are visible on this page.")
    return edit_mode

def render_home_edit_mode_toggle() -> bool:
    if not can_enter_home_edit_mode():
        return False

    col1, col2 = st.columns([1.2, 4.8])
    with col1:
        edit_mode = st.toggle("Edit Mode", key="edit_mode_home")
    with col2:
        if edit_mode:
            st.caption("Edit mode is on. Goal management tools are visible on this page.")
    return edit_mode

def show_login():
    show_logo()
    section_header("Chick-fil-A Staten Island Mall Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Log In", use_container_width=True)

    if submit:
        if not username or not password:
            st.error("Please enter both username and password.")
            return

        user = login_with_username(username, password)

        if user:
            st.session_state.logged_in = True
            st.session_state.profile = user
            st.success("Logged in successfully.")
            st.rerun()
        else:
            st.error("Invalid username or password.")

def render_sidebar():
    full_name = get_current_full_name()
    role = get_current_role()
    category = get_current_category()

    st.sidebar.success(f"Logged in as {full_name}")
    st.sidebar.write(f"Role: {ROLE_LABELS.get(role, role)}")
    if category:
        st.sidebar.write(f"Category: {category}")

    if st.sidebar.button("Log Out", use_container_width=True):
        logout_user()

    pages = ["Home"]

    shared_pages = [
        "Customer Experience",
        "Drive-Thru",
        "Training Department",
        "Sales & Brand Growth",
        "Food Safety/Food Quality",
        "Human Resources",
        "Maintenance",
        "Calendar"
    ]

    if has_role("team_member"):
        pages.extend(shared_pages)

    if has_role("team_member"):
        pages.append("Write-Up System")

    if has_role("shift_lead"):
        pages.append("Leadership Homepage")

    if can_view_suggestions_tab():
        pages.append("Suggestions Queue")

    if has_role("director"):
        pages.append("User Management")

    return st.sidebar.radio("Navigate", pages)

def show_link_card(link, show_actions=False):
    st.markdown(f"### {link['system_name']}")
    st.write(link.get("description") or "No description provided.")

    min_view_role = link.get("min_view_role", "team_member")
    st.markdown(
        f"<div class='link-meta'>Added by: {link.get('submitted_by_username', 'unknown')} | "
        f"Visible to: {ROLE_LABELS.get(min_view_role, min_view_role)} and above</div>",
        unsafe_allow_html=True
    )

    st.markdown(f"[Open Link]({link['external_url']})")

    if show_actions:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Edit Link", key=f"edit_link_btn_{link['id']}", use_container_width=True):
                current_state = st.session_state.get(f"editing_link_{link['id']}", False)
                st.session_state[f"editing_link_{link['id']}"] = not current_state

        with col2:
            if st.button("Delete Link", key=f"delete_link_{link['id']}", use_container_width=True):
                if delete_link(link["id"]):
                    st.success("Link deleted.")
                    st.rerun()

        if st.session_state.get(f"editing_link_{link['id']}", False):
            st.markdown("<hr class='soft-divider'>", unsafe_allow_html=True)

            with st.form(f"edit_link_form_{link['id']}"):
                if get_current_role() == "director":
                    editable_categories = CATEGORIES
                else:
                    editable_categories = [get_current_category()] if get_current_category() else [link["category"]]

                current_category = link.get("category", "")
                category_index = editable_categories.index(current_category) if current_category in editable_categories else 0

                new_category = st.selectbox(
                    "Category",
                    editable_categories,
                    index=category_index,
                    key=f"edit_category_{link['id']}"
                )

                new_system_name = st.text_input(
                    "System Name",
                    value=link.get("system_name", ""),
                    key=f"edit_system_name_{link['id']}"
                )

                new_external_url = st.text_input(
                    "External Link",
                    value=link.get("external_url", ""),
                    key=f"edit_external_url_{link['id']}"
                )

                new_description = st.text_area(
                    "Description",
                    value=link.get("description", ""),
                    key=f"edit_description_{link['id']}"
                )

                edit_view_roles = ALL_ROLES if get_current_role() == "director" else [
                    "team_member", "trainer", "shift_lead", "supervisor"
                ]

                current_min_role = link.get("min_view_role", "team_member")
                role_index = edit_view_roles.index(current_min_role) if current_min_role in edit_view_roles else 0

                new_min_view_role = st.selectbox(
                    "Who should be able to view this link?",
                    edit_view_roles,
                    index=role_index,
                    format_func=lambda x: f"{ROLE_LABELS[x]} and above",
                    key=f"edit_min_view_role_{link['id']}"
                )

                save_col, cancel_col = st.columns(2)
                with save_col:
                    save_changes = st.form_submit_button("Save Changes", use_container_width=True)
                with cancel_col:
                    cancel_changes = st.form_submit_button("Cancel", use_container_width=True)

            if save_changes:
                if not new_system_name.strip():
                    st.error("Please enter a system name.")
                elif not new_external_url.strip():
                    st.error("Please enter an external link.")
                else:
                    success = update_link(
                        link_id=link["id"],
                        category=new_category,
                        system_name=new_system_name,
                        external_url=new_external_url,
                        description=new_description,
                        min_view_role=new_min_view_role
                    )
                    if success:
                        st.session_state[f"editing_link_{link['id']}"] = False
                        st.success("Link updated successfully.")
                        st.rerun()

            if cancel_changes:
                st.session_state[f"editing_link_{link['id']}"] = False
                st.rerun()

    st.markdown("---")

def render_pending_card(link, prefix: str):
    st.markdown(f"### {link['system_name']}")
    st.write(f"Category: {link.get('category', '')}")
    st.write(link.get("description") or "No description provided.")

    st.markdown(
        f"<div class='link-meta'>Suggested by: {link.get('submitted_by_username', 'unknown')} "
        f"({ROLE_LABELS.get(link.get('submitted_by_role', ''), link.get('submitted_by_role', ''))}) | "
        f"Visible to: {ROLE_LABELS.get(link.get('min_view_role', 'team_member'), link.get('min_view_role', 'team_member'))} and above</div>",
        unsafe_allow_html=True
    )

    st.markdown(f"[Open Suggested Link]({link['external_url']})")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Approve", key=f"{prefix}_approve_{link['id']}", use_container_width=True):
            if approve_link(link["id"]):
                st.success("Suggestion approved.")
                st.rerun()
    with col2:
        if st.button("Reject", key=f"{prefix}_reject_{link['id']}", use_container_width=True):
            if reject_link(link["id"]):
                st.success("Suggestion rejected.")
                st.rerun()

    st.markdown("---")

def render_single_goal(goal: dict, prefix: str, edit_mode: bool = False):
    st.markdown(f"#### {goal['goal_title']}")

    if goal.get("goal_description"):
        st.write(goal["goal_description"])

    st.caption(f"Created by: {goal.get('created_by_username', 'unknown')}")

    updates = get_goal_updates(goal["id"])
    if updates:
        latest = updates[0]
        st.markdown(f"**Latest Status:** {latest['status_label']}")
        if latest.get("update_note"):
            st.write(latest["update_note"])
        st.caption(f"Updated by {latest.get('updated_by_username', 'unknown')}")
    else:
        st.write("**Latest Status:** No updates yet")

    if edit_mode and can_update_goal_status():
        with st.expander("Add Status Update"):
            with st.form(f"goal_update_form_{prefix}_{goal['id']}"):
                status_label = st.selectbox(
                    "Progress Status",
                    GOAL_STATUS_OPTIONS,
                    key=f"status_{prefix}_{goal['id']}"
                )
                update_note = st.text_area(
                    "Update Note",
                    key=f"note_{prefix}_{goal['id']}"
                )
                submit_update = st.form_submit_button("Save Update", use_container_width=True)

            if submit_update:
                success = add_goal_update(goal["id"], status_label, update_note)
                if success:
                    st.success("Goal update saved.")
                    st.rerun()
                else:
                    st.error("Unable to save update.")

    if edit_mode and can_manage_goals():
        with st.expander("Edit Goal"):
            with st.form(f"edit_goal_form_{prefix}_{goal['id']}"):
                new_title = st.text_input(
                    "Goal Title",
                    value=goal.get("goal_title", ""),
                    key=f"edit_title_{prefix}_{goal['id']}"
                )
                new_description = st.text_area(
                    "Goal Description",
                    value=goal.get("goal_description", ""),
                    key=f"edit_desc_{prefix}_{goal['id']}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    save_goal = st.form_submit_button("Save Goal", use_container_width=True)
                with col2:
                    remove_goal = st.form_submit_button("Remove Goal", use_container_width=True)

            if save_goal:
                if not new_title.strip():
                    st.error("Goal title is required.")
                else:
                    success = update_goal(goal["id"], new_title, new_description)
                    if success:
                        st.success("Goal updated.")
                        st.rerun()
                    else:
                        st.error("Unable to update goal.")

            if remove_goal:
                success = delete_goal(goal["id"])
                if success:
                    st.success("Goal removed.")
                    st.rerun()
                else:
                    st.error("Unable to remove goal.")

    st.markdown("---")

def render_goals_dashboard(edit_mode: bool = False):
    st.markdown("### Store Goals")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Yearly Goals")

        if edit_mode and can_manage_goals():
            with st.expander("Add Yearly Goal"):
                with st.form("add_yearly_goal_form"):
                    title = st.text_input("Goal Title", key="yearly_goal_title")
                    description = st.text_area("Goal Description", key="yearly_goal_desc")
                    submit = st.form_submit_button("Add Yearly Goal", use_container_width=True)

                if submit:
                    if not title.strip():
                        st.error("Goal title is required.")
                    else:
                        success = create_goal("yearly", title, description)
                        if success:
                            st.success("Yearly goal added.")
                            st.rerun()
                        else:
                            st.error("Unable to add yearly goal.")

        yearly_goals = get_goals_by_type("yearly")
        if yearly_goals:
            for goal in yearly_goals:
                render_single_goal(goal, "yearly", edit_mode=edit_mode)
        else:
            st.info("No yearly goals added yet.")

    with col2:
        st.markdown("#### Quarterly Goals")

        if edit_mode and can_manage_goals():
            with st.expander("Add Quarterly Goal"):
                with st.form("add_quarterly_goal_form"):
                    title = st.text_input("Goal Title", key="quarterly_goal_title")
                    description = st.text_area("Goal Description", key="quarterly_goal_desc")
                    submit = st.form_submit_button("Add Quarterly Goal", use_container_width=True)

                if submit:
                    if not title.strip():
                        st.error("Goal title is required.")
                    else:
                        success = create_goal("quarterly", title, description)
                        if success:
                            st.success("Quarterly goal added.")
                            st.rerun()
                        else:
                            st.error("Unable to add quarterly goal.")

        quarterly_goals = get_goals_by_type("quarterly")
        if quarterly_goals:
            for goal in quarterly_goals:
                render_single_goal(goal, "quarterly", edit_mode=edit_mode)
        else:
            st.info("No quarterly goals added yet.")

# -----------------------------
# Main links section
# -----------------------------
def render_links_section(category: str):
    edit_mode = render_edit_mode_toggle(category)

    st.markdown("### Resources")
    approved_links = get_links_for_category(category)
    can_manage_here = can_manage_links_in_category(category)

    if approved_links:
        for link in approved_links:
            show_link_card(link, show_actions=(edit_mode and can_manage_here))
    else:
        st.info("No links have been posted yet for this category.")

    can_submit_request = can_request_links_in_category(category)
    can_submit_direct = can_post_directly_in_category(category)

    if edit_mode and (can_submit_request or can_submit_direct):
        st.markdown("<div class='admin-panel'>", unsafe_allow_html=True)
        st.markdown("### Submit a Link")

        allowed_roles = get_allowed_view_roles_for_poster(category)

        with st.form(f"submit_link_form_{category}"):
            system_name = st.text_input("System Name")
            external_url = st.text_input("External Link")
            description = st.text_area("Description")

            min_view_role = st.selectbox(
                "Who should be able to view this link?",
                allowed_roles,
                format_func=lambda x: f"{ROLE_LABELS[x]} and above"
            )

            submit_link = st.form_submit_button("Submit Link", use_container_width=True)

        if submit_link:
            if not system_name.strip():
                st.error("Please enter a system name.")
            elif not external_url.strip():
                st.error("Please enter an external link.")
            else:
                success = create_link_submission(
                    category=category,
                    system_name=system_name,
                    external_url=external_url,
                    description=description,
                    min_view_role=min_view_role
                )

                if success:
                    st.success("Link posted successfully." if can_submit_direct else "Suggestion submitted for approval.")
                    st.rerun()
                else:
                    st.error("Unable to submit link.")
        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Website page rendering
# -----------------------------
def render_home():
    show_logo()
    subtitle = f"Welcome, {get_current_full_name()} ({ROLE_LABELS.get(get_current_role(), get_current_role())})"
    if get_current_category():
        subtitle += f" • {get_current_category()}"
    section_header("Chick-fil-A Staten Island Mall Website", subtitle)

    home_edit_mode = render_home_edit_mode_toggle()

    st.markdown(
        """
        <div class='admin-panel'>
            <h3 style='text-align:center; margin-top:0;'>Mission Statement</h3>
            <div style='text-align:center; max-width:700px; margin:0 auto; font-size:18px;'>
                To develop a team of people who dream, achieve, and succeed;
                while being a pillar of support for a community who relies upon our existence
                as much as we rely upon them.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    render_goals_dashboard(edit_mode=home_edit_mode)

def render_category_page(category: str):
    show_logo()
    section_header(category)
    render_links_section(category)

def render_calendar():
    show_logo()
    section_header("Store Calendar")
    st.caption("Use this calendar for store events, training, and operational planning.")

    components.iframe(
        GOOGLE_CALENDAR_EMBED_URL,
        height=760
    )

def render_suggestions_queue():
    show_logo()
    section_header("Suggestions Queue")

    if not can_view_suggestions_tab():
        st.error("You do not have access to this page.")
        return

    pending_links = get_suggestions_for_current_user()

    if not pending_links:
        st.info("No pending suggestions right now.")
        return

    if get_current_role() == "supervisor":
        st.caption(f"You are reviewing suggestions for: {get_current_category()}")
    else:
        st.caption("You can review suggestions from all categories.")

    for link in pending_links:
        render_pending_card(link, "queue")

def render_user_management():
    show_logo()
    section_header("User Management")

    if not has_role("director"):
        st.error("You do not have access to this page.")
        return

    st.markdown("<div class='admin-panel'>", unsafe_allow_html=True)
    st.markdown("### Create New Account")

    with st.form("create_user_form"):
        full_name = st.text_input("Full Name")
        password = st.text_input("Temporary Password", type="password")
        role = st.selectbox("Role", ALL_ROLES, format_func=lambda x: ROLE_LABELS[x])

        category_options = [""] + CATEGORIES
        category = st.selectbox(
            "Assigned Category",
            category_options,
            format_func=lambda x: "None / No Category" if x == "" else x
        )

        active = st.checkbox("Active", value=True)

        preview_username = clean_name_for_username(full_name) if full_name else ""
        if preview_username:
            st.caption(f"Generated username base: {preview_username}")

        submit_create = st.form_submit_button("Create Account", use_container_width=True)

    if submit_create:
        if not full_name.strip():
            st.error("Please enter a full name.")
        elif not password.strip():
            st.error("Please enter a password.")
        elif role not in ["director", "team_member"] and not category:
            st.error("Please assign a category for trainers, shift leads, and supervisors.")
        else:
            success, username = create_user_account(full_name, password, role, category, active)
            if success:
                st.success(f"Account created successfully. Username: {username}")
                st.rerun()
            else:
                st.error("Failed to create account.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Current Users")
    users = get_all_users()

    if users:
        st.dataframe(users, use_container_width=True)
    else:
        st.info("No users found.")

    st.markdown("---")
    st.markdown("<div class='admin-panel'>", unsafe_allow_html=True)
    st.markdown("### Edit User Details")

    editable_users = [u for u in users if u["username"].lower() != MASTER_USERNAME.lower()]

    if editable_users:
        edit_user_options = {
            f"{u['full_name']} ({u['username']}) - {ROLE_LABELS.get(u['role'], u['role'])} - {u.get('category', '')}": u
            for u in editable_users
        }

        selected_edit_label = st.selectbox(
            "Select user to edit",
            options=list(edit_user_options.keys()),
            key="edit_user_select"
        )
        selected_edit_user = edit_user_options[selected_edit_label]

        with st.form("edit_user_form"):
            new_role = st.selectbox(
                "Role",
                ALL_ROLES,
                index=ALL_ROLES.index(selected_edit_user["role"]) if selected_edit_user["role"] in ALL_ROLES else 0,
                format_func=lambda x: ROLE_LABELS[x]
            )

            category_options = [""] + CATEGORIES
            current_category = selected_edit_user.get("category", "")
            category_index = category_options.index(current_category) if current_category in category_options else 0

            new_category = st.selectbox(
                "Category",
                category_options,
                index=category_index,
                format_func=lambda x: "None / No Category" if x == "" else x
            )

            new_active = st.checkbox("Active", value=selected_edit_user.get("active", True))
            new_password = st.text_input("New Password (leave blank to keep current password)", type="password")

            save_user_changes = st.form_submit_button("Save User Changes", use_container_width=True)

        if save_user_changes:
            if new_role not in ["director", "team_member"] and not new_category:
                st.error("Trainers, shift leads, and supervisors must have an assigned category.")
            else:
                success = update_user_details(
                    user_id=selected_edit_user["id"],
                    role=new_role,
                    category=new_category,
                    active=new_active,
                    new_password=new_password
                )
                if success:
                    st.success(f"Updated user: {selected_edit_user['username']}")
                    st.rerun()
                else:
                    st.error("Failed to update user.")
    else:
        st.info("No editable users found.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div class='admin-panel'>", unsafe_allow_html=True)
    st.markdown("### Delete Account")

    if users:
        delete_options = {
            f"{u['full_name']} ({u['username']}) - {ROLE_LABELS.get(u['role'], u['role'])} - {u.get('category', '')}": u
            for u in users
        }

        selected_delete_label = st.selectbox(
            "Select account to delete",
            options=list(delete_options.keys())
        )
        selected_user = delete_options[selected_delete_label]

        if selected_user["username"].lower() == MASTER_USERNAME.lower():
            st.warning("The hardcoded Lauren director login cannot be deleted here.")
        elif selected_user["username"] == get_current_username():
            st.warning("You cannot delete the account you are currently logged into.")
        else:
            st.error("Warning: deleting an account permanently removes it from the system.")
            if st.button("Delete Selected Account", type="primary", use_container_width=True):
                success = delete_user_account(selected_user["id"])
                if success:
                    st.success(f"Deleted account: {selected_user['username']}")
                    st.rerun()
                else:
                    st.error("Failed to delete account.")
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Write-Up page rendering
# -----------------------------
def set_user_active_status(user_id, is_active: bool):
    return supabase.from_("users").update({"active": is_active}).eq("id", user_id).execute()

def render_writeup_system():
    show_logo()
    section_header("Write-Up System")

    if not can_view_writeup_system():
        st.error("You do not have access to this page.")
        return

    available_modes = ["Employee Mode"]

    if can_use_writeup_manager_mode():
        available_modes.append("Manager Mode")

    if can_use_writeup_admin_mode():
        available_modes.append("Admin Mode")

    selected_mode = st.selectbox("Select Mode", available_modes)

    if selected_mode == "Employee Mode":
        employee_mode()
    elif selected_mode == "Manager Mode":
        manager_mode()
    elif selected_mode == "Admin Mode":
        admin_mode()

def employee_mode():
    st.header("Employee Mode (Search + View History)")

    current_role = get_current_role()
    current_username = get_current_username()
    current_full_name = get_current_full_name()

    # -------------------------------------------------
    # TEAM MEMBERS + TRAINERS:
    # only allowed to see their own write-ups
    # -------------------------------------------------
    if current_role in ["team_member", "trainer"]:
        current_user = fetch_user_by_username(current_username)

        if not current_user:
            st.error("Could not find your user account.")
            return

        member_id = current_user["id"]
        writeups = fetch_writeups_for_member(member_id)

        st.subheader(f"Write-Up History for {current_full_name}")

        selected_quarter = current_quarter_key()
        q_total = points_in_quarter(writeups, selected_quarter)
        s_label = standing_label(q_total)
        a_total = all_time_points(writeups)

        standing_badge(
            s_label,
            q_total,
            caption=f"Standing is based on **{selected_quarter}** points (resets every quarter).",
        )

        c1, c2 = st.columns(2)
        c1.metric(f"Points in {selected_quarter}", q_total)
        c2.metric("All-Time Points", a_total)

        st.subheader("Points Over Time (by Quarter)")
        df_q = build_quarter_totals(writeups)
        if df_q.empty:
            st.info("No write-ups yet, so no quarter history to show.")
        else:
            st.dataframe(
                df_q.rename(columns={"quarter": "Quarter", "points": "Points"}),
                hide_index=True,
                use_container_width=True
            )

        st.subheader("Write-Up History (All Time)")
        if not writeups:
            st.warning("No write-ups found.")
            return

        rows = []
        for w in writeups:
            cat = w.get("writeup_categories") or {}
            cat_name = cat.get("name") if isinstance(cat, dict) else None
            d = parse_iso_date(w.get("incident_date"))

            rows.append(
                {
                    "Incident Date": w.get("incident_date"),
                    "Quarter": quarter_key(d) if d else None,
                    "Category": cat_name,
                    "Points": w.get("points"),
                    "Created By": w.get("created_by"),
                    "Created At": w.get("created_at"),
                    "Writeup ID": w.get("id"),
                }
            )

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        with st.expander("View Full Write-Up Details (including signatures)", expanded=False):
            ids = [w["id"] for w in writeups]
            chosen_id = st.selectbox("Select Writeup ID", ids, key="emp_view_own_writeup_id")
            chosen_w = next((w for w in writeups if w["id"] == chosen_id), None)
            if chosen_w:
                st.text_area("Full Write-Up Details", value=chosen_w.get("notes") or "", height=260)

        return

    # -------------------------------------------------
    # SHIFT LEADS + SUPERVISORS + DIRECTORS:
    # keep full search/view access
    # -------------------------------------------------
    members = fetch_team_members("", include_inactive=False)
    if not members:
        st.info("No active team members found.")
        return

    search_mode = st.radio("Search by", ["Name", "Standing"], horizontal=True)

    per_member_writeups = {}
    all_quarters = set([current_quarter_key()])

    for m in members:
        w = fetch_writeups_for_member(m["id"])
        per_member_writeups[m["id"]] = w
        df_q = build_quarter_totals(w)
        if not df_q.empty:
            all_quarters.update(df_q["quarter"].tolist())

    def _sort_q(qstr):
        y, q = qstr.split()
        return int(y), int(q.replace("Q", ""))

    quarter_options = sorted(list(all_quarters), key=_sort_q, reverse=True)
    selected_quarter = st.selectbox("Quarter to evaluate (points reset each quarter)", quarter_options)

    if search_mode == "Name":
        name_query = st.text_input("Search by name (active only)", value="")
        filtered = members
        if name_query.strip():
            nq = name_query.strip().lower()
            filtered = [m for m in members if nq in (m["full_name"] or "").lower()]

        if not filtered:
            st.info("No matching active team members.")
            return

        labels = [m["full_name"] for m in filtered]
        name_to_id = {m["full_name"]: m["id"] for m in filtered}
        chosen_name = st.selectbox("Select a team member", labels)
        member_id = name_to_id[chosen_name]
    else:
        standing_choice = st.selectbox("Standing (based on selected quarter points)", STANDING_ORDER)

        rows = []
        for m in members:
            w = per_member_writeups.get(m["id"], [])
            q_total = points_in_quarter(w, selected_quarter)
            s = standing_label(q_total)
            if s == standing_choice:
                rows.append({"id": m["id"], "name": m["full_name"], "quarter_points": q_total})

        if not rows:
            st.info(f"No active team members found in {standing_choice} for {selected_quarter}.")
            return

        rows.sort(key=lambda r: (-int(r["quarter_points"]), r["name"].lower()))
        labels = [f"{r['name']} ({r['quarter_points']} pts)" for r in rows]
        label_to_id = {labels[i]: rows[i]["id"] for i in range(len(labels))}
        chosen = st.selectbox("Select a team member", labels)
        member_id = label_to_id[chosen]

    writeups = per_member_writeups.get(member_id) or fetch_writeups_for_member(member_id)

    q_total = points_in_quarter(writeups, selected_quarter)
    s_label = standing_label(q_total)
    a_total = all_time_points(writeups)

    standing_badge(
        s_label,
        q_total,
        caption=f"Standing is based on **{selected_quarter}** points (resets every quarter).",
    )

    c1, c2 = st.columns(2)
    c1.metric(f"Points in {selected_quarter}", q_total)
    c2.metric("All-Time Points", a_total)

    st.subheader("Points Over Time (by Quarter)")
    df_q = build_quarter_totals(writeups)
    if df_q.empty:
        st.info("No write-ups yet, so no quarter history to show.")
    else:
        st.dataframe(
            df_q.rename(columns={"quarter": "Quarter", "points": "Points"}),
            hide_index=True,
            use_container_width=True
        )

    st.subheader("Write-Up History (All Time)")
    if not writeups:
        st.warning("No write-ups found.")
        return

    rows = []
    for w in writeups:
        cat = w.get("writeup_categories") or {}
        cat_name = cat.get("name") if isinstance(cat, dict) else None
        d = parse_iso_date(w.get("incident_date"))
        rows.append(
            {
                "Incident Date": w.get("incident_date"),
                "Quarter": quarter_key(d) if d else None,
                "Category": cat_name,
                "Points": w.get("points"),
                "Created By": w.get("created_by"),
                "Created At": w.get("created_at"),
                "Writeup ID": w.get("id"),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("View Full Write-Up Details (including signatures)", expanded=False):
        ids = [w["id"] for w in writeups]
        chosen_id = st.selectbox("Select Writeup ID", ids, key="emp_view_writeup_id")
        chosen_w = next((w for w in writeups if w["id"] == chosen_id), None)
        if chosen_w:
            st.text_area("Full Write-Up Details", value=chosen_w.get("notes") or "", height=260)

def manager_mode():
    st.header("Manager Mode (Add Write-Ups)")

    if not can_use_writeup_manager_mode():
        st.error("You do not have access to Manager Mode.")
        return

    st.subheader("Find Team Member")
    member_search = st.text_input("Search team member (active only)", value="")
    members = fetch_team_members(member_search, include_inactive=False)

    if not members:
        st.info("No active team members match that search.")
        return

    member_labels = [m["full_name"] for m in members]
    member_map = {m["full_name"]: m["id"] for m in members}

    member_name = st.selectbox("Select team member", member_labels)
    member_id = member_map[member_name]

    categories = fetch_categories(include_inactive=False)
    if not categories:
        st.error("No active categories found.")
        return

    cat_names = [c["name"] for c in categories]
    cat_map = {c["name"]: c for c in categories}

    st.markdown("---")
    st.subheader("Create Write-Up")

    chosen_cat_name = st.selectbox("Category", cat_names)
    chosen_cat = cat_map[chosen_cat_name]
    category_id = chosen_cat["id"]

    custom_reason = ""
    points_val_default = 0
    prev_quarter_label = ""
    new_quarter_label = ""
    quarter_points_after_save = 0

    if chosen_cat_name == "Documented Conversation":
        st.info("This is a documented conversation. No points will be assigned.")
        custom_reason = st.text_input("Conversation Topic / Reason")
        auto_points = 0
    else:
        rules = fetch_rules_for_category(category_id)
        if not rules:
            st.warning("No rules found for this category.")
            return

        rule_labels = [r["rule_name"] for r in rules]
        rule_map = {r["rule_name"]: r for r in rules}

        chosen_rule_name = st.selectbox("Reason / Rule", rule_labels)

        hb_text = HANDBOOK_BY_RULE.get(chosen_rule_name)
        if hb_text:
            st.markdown("#### Employee Handbook Code")
            st.info(hb_text)

        chosen_rule = rule_map[chosen_rule_name]
        auto_points = int(chosen_rule.get("base_points") or 0)

        if chosen_rule.get("is_incremental"):
            minutes_late = st.number_input("Minutes late", min_value=0, max_value=600, value=0, step=1)
            auto_points = calc_late_points(int(minutes_late))

            if minutes_late < 6:
                st.info("Under 6 minutes late → 0 points")
            else:
                extra = (minutes_late - 5) // 10
                st.info(f"Points = 1 + {extra} additional blocks = {auto_points}")

    with st.form("add_writeup_form", clear_on_submit=True):
        incident_dt = st.date_input("Incident Date", value=date.today())

        manager_notes = st.text_area("Manager Notes")
        secondary_lead_witness = st.text_input("Secondary Lead Witnessing Write-Up")
        corrective_actions = st.text_area("Corrective Actions")
        team_member_comments = st.text_area("Team Member's Comments")

        st.markdown("#### Signatures")
        team_member_signature = st.text_input("Team Member Signature")
        leader_signature = st.text_input("Leader Signature")
        secondary_leader_signature = st.text_input("Secondary Leader Signature")
        signed_dt = st.date_input("Date Signed", value=date.today())

        if chosen_cat_name == "Documented Conversation":
            points_val = 0
            st.caption("Points: 0 (Documented Conversation)")
        else:
            colA, colB = st.columns([1, 1])
            with colA:
                points_override = st.toggle("Override points manually?", value=False)
            with colB:
                points_val = st.number_input(
                    "Points",
                    value=int(auto_points),
                    step=1,
                    disabled=not points_override
                )

        submitted = st.form_submit_button("Save Write-Up")

    if submitted:
        try:
            existing_writeups = fetch_writeups_for_member(member_id)
            prev_quarter_label = quarter_key(incident_dt)
            prev_points = points_in_quarter(existing_writeups, prev_quarter_label)
            prev_standing = standing_label(prev_points)

            reason_value = custom_reason if chosen_cat_name == "Documented Conversation" else chosen_rule_name

            final_notes = format_writeup_notes(
                reason=reason_value,
                manager_notes=manager_notes,
                secondary_lead_witness=secondary_lead_witness,
                corrective_actions=corrective_actions,
                team_member_comments=team_member_comments,
                team_member_signature=team_member_signature,
                leader_signature=leader_signature,
                secondary_leader_signature=secondary_leader_signature,
                signed_date=signed_dt,
            )

            add_writeup(
                member_id=member_id,
                category_id=category_id,
                points=int(points_val),
                incident_date=incident_dt,
                notes=final_notes,
                created_by=get_current_username(),
            )

            post_writeup_to_slack(
                member_name=member_name,
                category_name=chosen_cat_name,
                incident_date=incident_dt.isoformat(),
                notes=final_notes,
            )

            updated_writeups = fetch_writeups_for_member(member_id)
            new_quarter_label = quarter_key(incident_dt)
            quarter_points_after_save = points_in_quarter(updated_writeups, new_quarter_label)
            new_standing = standing_label(quarter_points_after_save)

            maybe_post_standing_alert(
                member_name=member_name,
                quarter_label=new_quarter_label,
                prev_label=prev_standing,
                new_label=new_standing,
                q_points=quarter_points_after_save
            )

            st.success("Write-up saved.")
            st.rerun()

        except Exception as e:
            st.error(f"Failed to save write-up: {e}")

def admin_mode():
    st.header("Admin Mode")

    if not can_use_writeup_admin_mode():
        st.error("You do not have access to Admin Mode.")
        return

    st.write(f"Logged in as **{get_current_username()}** ({ROLE_LABELS.get(get_current_role(), get_current_role())})")

    st.markdown("---")
    st.subheader("Team Members")

    members_all = (
        supabase.from_("users")
        .select("id, full_name, active, created_at, role")
        .order("full_name")
        .execute()
        .data
        or []
    )

    df_all = pd.DataFrame(members_all)
    if not df_all.empty:
        df_all["status"] = df_all["active"].apply(lambda x: "active" if x else "inactive")
        st.dataframe(
            df_all[["id", "full_name", "role", "status", "created_at"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No users found.")

    st.markdown("### Add Team Member (always starts ACTIVE)")
    with st.form("add_member_form", clear_on_submit=True):
        nm = st.text_input("New team member name")
        if st.form_submit_button("Add Team Member"):
            if nm.strip():
                try:
                    add_team_member(nm)
                    st.success("Team member added as ACTIVE.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding member: {e}")
            else:
                st.warning("Enter a name.")

    st.markdown("---")
    st.subheader("Set Team Member Active / Inactive")

    if members_all:
        label_list = [
            f"{m['full_name']} — {'active' if m.get('active', True) else 'inactive'} ({m['id']})"
            for m in members_all
        ]
        chosen = st.selectbox("Select user", label_list, key="admin_member_status_pick")
        chosen_id = chosen.split("(")[-1].replace(")", "").strip()

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Mark ACTIVE"):
                set_user_active_status(chosen_id, True)
                st.success("User set to ACTIVE.")
                st.rerun()
        with c2:
            if st.button("Mark INACTIVE"):
                set_user_active_status(chosen_id, False)
                st.success("User set to INACTIVE.")
                st.rerun()

    st.markdown("---")
    st.subheader("Delete Team Member (and ALL write-ups)")
    if members_all:
        del_label = st.selectbox(
            "Select user to delete",
            [f"{m['full_name']} ({m['id']})" for m in members_all],
            key="admin_delete_member_pick",
        )
        del_id = del_label.split("(")[-1].replace(")", "").strip()

        if st.button("Delete Team Member + All Write-Ups", type="primary"):
            st.session_state.pending_delete_member_id = del_id

        if st.session_state.pending_delete_member_id:
            st.error(f"Confirm delete team member + ALL writeups: **{st.session_state.pending_delete_member_id}**")
            d1, d2 = st.columns(2)
            with d1:
                if st.button("YES — Delete Member"):
                    delete_team_member(st.session_state.pending_delete_member_id)
                    st.session_state.pending_delete_member_id = None
                    st.success("Deleted member + writeups.")
                    st.session_state.admin_browse_cache = []
                    st.session_state.admin_browse_ids = []
                    st.session_state.admin_browse_index = 0
                    st.rerun()
            with d2:
                if st.button("Cancel"):
                    st.session_state.pending_delete_member_id = None

    st.markdown("---")
    st.subheader("Browse Write-Ups Chronologically (Admin)")

    if st.button("Reload Write-Ups List"):
        st.session_state.admin_browse_cache = []
        st.session_state.admin_browse_ids = []
        st.session_state.admin_browse_index = 0
        st.rerun()

    if not st.session_state.admin_browse_cache:
        all_w = fetch_all_writeups_chronological()
        st.session_state.admin_browse_cache = all_w
        st.session_state.admin_browse_ids = [w["id"] for w in all_w]
        st.session_state.admin_browse_index = 0

    all_w = st.session_state.admin_browse_cache

    if not all_w:
        st.info("No write-ups exist yet.")
    else:
        idx = st.session_state.admin_browse_index
        idx = max(0, min(idx, len(all_w) - 1))
        st.session_state.admin_browse_index = idx

        w = all_w[idx]
        user_info = w.get("team_user") or {}
        name = user_info.get("full_name", "Unknown")
        cat = w.get("writeup_categories") or {}

        st.markdown(f"### {name} — {cat.get('name','Unknown')}")
        st.caption(f"Incident: {w.get('incident_date')} | Created: {w.get('created_at')} | ID: {w.get('id')}")
        st.metric("Points", w.get("points", 0))
        st.text_area("Full Notes (includes signatures)", value=w.get("notes") or "", height=260)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("⬅ Previous", key="admin_prev_w"):
                st.session_state.admin_browse_index = max(0, idx - 1)
                st.rerun()
        with c2:
            st.write(f"**{idx + 1} / {len(all_w)}**")
        with c3:
            if st.button("Next ➡", key="admin_next_w"):
                st.session_state.admin_browse_index = min(len(all_w) - 1, idx + 1)
                st.rerun()

        st.markdown("### Delete This Write-Up")
        if st.button("Delete this write-up", type="primary", key="admin_delete_this_writeup"):
            st.session_state.pending_delete_writeup_id = w["id"]

        if st.session_state.pending_delete_writeup_id:
            st.error(f"Confirm delete write-up: **{st.session_state.pending_delete_writeup_id}**")
            d1, d2 = st.columns(2)
            with d1:
                if st.button("YES — Delete permanently", key="admin_confirm_delete_writeup"):
                    delete_writeup(st.session_state.pending_delete_writeup_id)
                    st.session_state.admin_browse_cache = []
                    st.session_state.admin_browse_ids = []
                    st.session_state.admin_browse_index = max(0, idx - 1)
                    st.session_state.pending_delete_writeup_id = None
                    st.success("Write-up deleted.")
                    st.rerun()
            with d2:
                if st.button("Cancel", key="admin_cancel_delete_writeup"):
                    st.session_state.pending_delete_writeup_id = None

# -----------------------------
# Main app
# -----------------------------
init_session()

if not st.session_state.logged_in:
    show_login()
    st.stop()

page = render_sidebar()

if page == "Home":
    render_home()
elif page == "Customer Experience":
    render_category_page("Customer Experience")
elif page == "Drive-Thru":
    render_category_page("Drive-Thru")
elif page == "Training Department":
    render_category_page("Training Department")
elif page == "Sales & Brand Growth":
    render_category_page("Sales & Brand Growth")
elif page == "Food Safety/Food Quality":
    render_category_page("Food Safety/Food Quality")
elif page == "Human Resources":
    render_category_page("Human Resources")
elif page == "Maintenance":
    render_category_page("Maintenance")
elif page == "Leadership Homepage":
    render_category_page("Leadership Homepage")
elif page == "Calendar":
    render_calendar()
elif page == "Write-Up System":
    render_writeup_system()
elif page == "Suggestions Queue":
    render_suggestions_queue()
elif page == "User Management":
    render_user_management()