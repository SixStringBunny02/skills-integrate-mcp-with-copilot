"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Request, Response, Depends, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
import secrets
from typing import List
from fastapi import Security

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Allow CORS for frontend JS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory user database (for demo only)
users = {
    "admin@mergington.edu": {"password": "adminpass", "role": "admin", "name": "Admin User"},
    "teacher@mergington.edu": {"password": "teachpass", "role": "staff", "name": "Teacher T."},
    "student@mergington.edu": {"password": "studpass", "role": "student", "name": "Student S."},
}

# In-memory session store: session_token -> user_email
sessions = {}

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


# Dependency to get current user from session cookie
def get_current_user(session_token: str = Cookie(None)):
    if not session_token or session_token not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = sessions[session_token]
    user = users.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return {"email": email, **user}


@app.post("/login")
def login(data: dict, response: Response):
    email = data.get("email")
    password = data.get("password")
    user = users.get(email)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Create session
    session_token = secrets.token_urlsafe(16)
    sessions[session_token] = email
    response.set_cookie(key="session_token", value=session_token, httponly=True)
    return {"message": "Login successful", "role": user["role"], "name": user["name"]}


@app.post("/logout")
def logout(response: Response, session_token: str = Cookie(None)):
    if session_token in sessions:
        del sessions[session_token]
    response.delete_cookie("session_token")
    return {"message": "Logged out"}


@app.get("/me")
def get_me(user=Depends(get_current_user)):
    return {"email": user["email"], "role": user["role"], "name": user["name"]}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, user=Depends(get_current_user)):
    """Sign up a student for an activity. Only staff or the student themselves can sign up."""
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    activity = activities[activity_name]
    # Only staff or the student themselves can sign up
    if user["role"] == "student" and user["email"] != email:
        raise HTTPException(status_code=403, detail="Students can only sign up themselves")
    if email in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student is already signed up")
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, user=Depends(get_current_user)):
    """Unregister a student from an activity. Only staff or the student themselves can unregister."""
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    activity = activities[activity_name]
    if user["role"] == "student" and user["email"] != email:
        raise HTTPException(status_code=403, detail="Students can only unregister themselves")
    if email not in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}


# Utility: role-based dependency
def require_roles(roles: List[str]):
    def role_checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker


@app.post("/users/create")
def create_user(data: dict, user=Depends(require_roles(["admin", "staff"]))):
    """Create a new user (admin or staff only)."""
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")
    name = data.get("name")
    if not email or not password or not role or not name:
        raise HTTPException(status_code=400, detail="Missing user fields")
    if email in users:
        raise HTTPException(status_code=400, detail="User already exists")
    if role not in ["admin", "staff", "student"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    users[email] = {"password": password, "role": role, "name": name}
    return {"message": f"User {email} created with role {role}"}


@app.delete("/users/{email}")
def delete_user(email: str, user=Depends(require_roles(["admin"]))):
    """Delete a user (admin only)."""
    if email not in users:
        raise HTTPException(status_code=404, detail="User not found")
    if users[email]["role"] == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete another admin")
    del users[email]
    return {"message": f"User {email} deleted"}


@app.get("/users")
def list_users(user=Depends(require_roles(["admin", "staff"]))):
    """List all users (admin or staff only)."""
    return {email: {k: v for k, v in info.items() if k != "password"} for email, info in users.items()}
