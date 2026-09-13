"""
FitTrack AI - Smart Fitness & Wellness Tracker
Flask + MySQL backend.

Run with:  python app.py
"""

from datetime import date, datetime, timedelta
from functools import wraps

import mysql.connector
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash
)
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config

app = Flask(__name__)
app.config.from_object(Config)


# =========================================================
# DATABASE HELPERS
# =========================================================
def get_db_connection():
    """Create and return a new MySQL connection."""
    return mysql.connector.connect(
        host=app.config["MYSQL_HOST"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DATABASE"],
    )


def run_query(query, params=None, fetch=None, commit=False):
    """
    Small helper to reduce repeated boilerplate.
    fetch: None | "one" | "all"
    commit: True for INSERT/UPDATE/DELETE
    Returns: fetched rows/row, or lastrowid on commit-insert, or None.
    Raises mysql.connector.Error on failure (caught by caller).
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        result = None
        if fetch == "one":
            result = cursor.fetchone()
        elif fetch == "all":
            result = cursor.fetchall()
        if commit:
            conn.commit()
            result = cursor.lastrowid
        return result
    finally:
        cursor.close()
        conn.close()


# =========================================================
# AUTH DECORATOR
# =========================================================
def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped


# =========================================================
# SMALL CALCULATION HELPERS
# =========================================================
def calculate_bmi(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    height_m = float(height_cm) / 100
    if height_m <= 0:
        return None
    bmi = float(weight_kg) / (height_m ** 2)
    return round(bmi, 1)


def bmi_category(bmi):
    if bmi is None:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obesity"


def generate_insights(user_id, height):
    """Very simple rule-based 'AI Fitness Insights'."""
    insights = []
    today = date.today()

    # Weight trend (last 2 records)
    weights = run_query(
        "SELECT weight, record_date FROM weight_history "
        "WHERE user_id=%s ORDER BY record_date DESC LIMIT 2",
        (user_id,), fetch="all"
    )
    if weights and len(weights) == 2:
        latest, prev = weights[0]["weight"], weights[1]["weight"]
        if latest < prev:
            insights.append("Your weight is trending downward. Keep tracking your progress.")
        elif latest > prev:
            insights.append("Your weight has increased since your last entry. Review your habits if this isn't your goal.")

    # Steps today vs goal
    step_row = run_query(
        "SELECT steps FROM steps WHERE user_id=%s AND record_date=%s",
        (user_id, today), fetch="one"
    )
    today_steps = step_row["steps"] if step_row else 0
    if today_steps < app.config["DEFAULT_STEP_GOAL"]:
        insights.append("Try increasing your daily activity to reach your step goal.")

    # Calories vs target
    cal_row = run_query(
        "SELECT COALESCE(SUM(calories),0) AS total FROM meals "
        "WHERE user_id=%s AND meal_date=%s",
        (user_id, today), fetch="one"
    )
    consumed = cal_row["total"] if cal_row else 0
    if consumed > app.config["DEFAULT_CALORIE_TARGET"]:
        insights.append("Your calorie intake is above today's target.")

    # Workout frequency this week
    week_ago = today - timedelta(days=7)
    workout_count = run_query(
        "SELECT COUNT(*) AS cnt FROM workouts WHERE user_id=%s AND workout_date>=%s",
        (user_id, week_ago), fetch="one"
    )
    if workout_count and workout_count["cnt"] < 3:
        insights.append("Consider adding another workout session this week.")

    if not insights:
        insights.append("You're doing great! Keep up the consistent tracking.")

    return insights


# =========================================================
# PAGE ROUTES
# =========================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/auth")
def auth():
    return render_template("auth.html")

@app.route('/bmi')
@login_required
def bmi():
    user_id = session["user_id"]

    user = run_query("select * from users where id = %s",(user_id,), fetch="one")
    return render_template('bmi.html',user=user)


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    today = date.today()

    user = run_query("SELECT * FROM users WHERE id=%s", (user_id,), fetch="one")

    # Current & starting weight
    latest_weight_row = run_query(
        "SELECT weight FROM weight_history WHERE user_id=%s "
        "ORDER BY record_date DESC, id DESC LIMIT 1",
        (user_id,), fetch="one"
    )
    current_weight = float(latest_weight_row["weight"]) if latest_weight_row else float(user["initial_weight"])

    bmi = calculate_bmi(current_weight, user["height"])

    cal_row = run_query(
        "SELECT COALESCE(SUM(calories),0) AS total FROM meals WHERE user_id=%s AND meal_date=%s",
        (user_id, today), fetch="one"
    )
    calories_consumed = cal_row["total"] if cal_row else 0

    burned_row = run_query(
        "SELECT COALESCE(SUM(calories_burned),0) AS total FROM workouts WHERE user_id=%s AND workout_date=%s",
        (user_id, today), fetch="one"
    )
    calories_burned = burned_row["total"] if burned_row else 0

    step_row = run_query(
        "SELECT steps FROM steps WHERE user_id=%s AND record_date=%s",
        (user_id, today), fetch="one"
    )
    today_steps = step_row["steps"] if step_row else 0

    minutes_row = run_query(
        "SELECT COALESCE(SUM(duration),0) AS total FROM workouts WHERE user_id=%s AND workout_date=%s",
        (user_id, today), fetch="one"
    )
    workout_minutes = minutes_row["total"] if minutes_row else 0

    stats = {
        "current_weight": current_weight,
        "bmi": bmi,
        "bmi_category": bmi_category(bmi),
        "calories_consumed": calories_consumed,
        "calories_burned": calories_burned,
        "today_steps": today_steps,
        "workout_minutes": workout_minutes,
        "calorie_target": app.config["DEFAULT_CALORIE_TARGET"],
        "step_goal": app.config["DEFAULT_STEP_GOAL"],
    }

    recent_weight = run_query(
        "SELECT * FROM weight_history WHERE user_id=%s ORDER BY record_date DESC LIMIT 1",
        (user_id,), fetch="one"
    )
    recent_workout = run_query(
        "SELECT * FROM workouts WHERE user_id=%s ORDER BY workout_date DESC, id DESC LIMIT 1",
        (user_id,), fetch="one"
    )
    recent_meal = run_query(
        "SELECT * FROM meals WHERE user_id=%s ORDER BY meal_date DESC, id DESC LIMIT 1",
        (user_id,), fetch="one"
    )
    recent_steps = run_query(
        "SELECT * FROM steps WHERE user_id=%s ORDER BY record_date DESC, id DESC LIMIT 1",
        (user_id,), fetch="one"
    )

    insights = generate_insights(user_id, user["height"])

    return render_template(
        "dashboard.html",
        user=user,
        stats=stats,
        recent_weight=recent_weight,
        recent_workout=recent_workout,
        recent_meal=recent_meal,
        recent_steps=recent_steps,
        insights=insights,
    )


@app.route("/fitness")
@login_required
def fitness():
    user_id = session["user_id"]
    user = run_query("SELECT * FROM users WHERE id=%s", (user_id,), fetch="one")

    weights = run_query(
        "SELECT * FROM weight_history WHERE user_id=%s ORDER BY record_date DESC",
        (user_id,), fetch="all"
    )
    workouts = run_query(
        "SELECT * FROM workouts WHERE user_id=%s ORDER BY workout_date DESC",
        (user_id,), fetch="all"
    )
    steps = run_query(
        "SELECT * FROM steps WHERE user_id=%s ORDER BY record_date DESC",
        (user_id,), fetch="all"
    )
    goals = run_query(
        "SELECT * FROM fitness_goals WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,), fetch="all"
    )

    starting_weight = float(user["initial_weight"])
    current_weight = float(weights[0]["weight"]) if weights else starting_weight
    weight_change = round(current_weight - starting_weight, 1)

    today = date.today()
    today_steps_row = next((s for s in steps if s["record_date"] == today), None)
    today_steps = today_steps_row["steps"] if today_steps_row else 0

    week_ago = today - timedelta(days=7)
    weekly_steps = sum(s["steps"] for s in steps if s["record_date"] >= week_ago)
    total_steps = sum(s["steps"] for s in steps)

    for g in goals:
        target = float(g["target_value"]) or 1
        current = float(g["current_value"])
        pct = min(100, max(0, round((current / target) * 100))) if target else 0
        g["progress_pct"] = pct

    return render_template(
        "fitness.html",
        user=user,
        weights=weights,
        workouts=workouts,
        steps=steps,
        goals=goals,
        starting_weight=starting_weight,
        current_weight=current_weight,
        weight_change=weight_change,
        today_steps=today_steps,
        weekly_steps=weekly_steps,
        total_steps=total_steps,
        step_goal=app.config["DEFAULT_STEP_GOAL"],
    )


@app.route("/diet-profile")
@login_required
def diet_profile():
    user_id = session["user_id"]
    user = run_query("SELECT * FROM users WHERE id=%s", (user_id,), fetch="one")
    today = date.today()

    meals = run_query(
        "SELECT * FROM meals WHERE user_id=%s ORDER BY meal_date DESC, id DESC",
        (user_id,), fetch="all"
    )

    today_total = sum(m["calories"] for m in meals if m["meal_date"] == today)
    target = app.config["DEFAULT_CALORIE_TARGET"]
    remaining = max(0, target - today_total)

    return render_template(
        "diet-profile.html",
        user=user,
        meals=meals,
        today_total=today_total,
        target=target,
        remaining=remaining,
    )


# =========================================================
# AUTHENTICATION API
# =========================================================
@app.route("/signup", methods=["POST"])
def signup():
    data = request.form

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    age = data.get("age", "").strip()
    gender = data.get("gender", "").strip()
    height = data.get("height", "").strip()
    initial_weight = data.get("initial_weight", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    # Server-side validation (mirrors client-side JS validation)
    if not all([full_name, email, age, gender, height, initial_weight, password]):
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("auth"))

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("auth"))

    if len(password) < 6:
        flash("Password must be at least 6 characters long.", "error")
        return redirect(url_for("auth"))

    try:
        age = int(age)
        height = float(height)
        initial_weight = float(initial_weight)
    except ValueError:
        flash("Age, height and weight must be valid numbers.", "error")
        return redirect(url_for("auth"))

    if height <= 0 or initial_weight <= 0 or age <= 0:
        flash("Age, height and weight must be positive values.", "error")
        return redirect(url_for("auth"))

    existing = run_query("SELECT id FROM users WHERE email=%s", (email,), fetch="one")
    if existing:
        flash("An account with this email already exists.", "error")
        return redirect(url_for("auth"))

    hashed_password = generate_password_hash(password)

    try:
        user_id = run_query(
            "INSERT INTO users (full_name, email, phone, age, gender, height, "
            "initial_weight, password) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (full_name, email, phone, age, gender, height, initial_weight, hashed_password),
            commit=True,
        )
    except mysql.connector.Error:
        flash("Something went wrong creating your account. Please try again.", "error")
        return redirect(url_for("auth"))

    # Seed an initial weight history record so charts have data from day one
    run_query(
        "INSERT INTO weight_history (user_id, weight, record_date) VALUES (%s,%s,%s)",
        (user_id, initial_weight, date.today()), commit=True,
    )

    session["user_id"] = user_id
    session["user_name"] = full_name
    flash("Account created successfully!", "success")
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Please enter both email and password.", "error")
        return redirect(url_for("auth"))

    user = run_query("SELECT * FROM users WHERE email=%s", (email,), fetch="one")

    if not user or not check_password_hash(user["password"], password):
        flash("Invalid email or password.", "error")
        return redirect(url_for("auth"))

    session["user_id"] = user["id"]
    session["user_name"] = user["full_name"]
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    # Simple placeholder flow (no email service configured for this project).
    flash("If an account exists with that email, password reset instructions would be sent.", "success")
    return redirect(url_for("auth"))


# =========================================================
# WEIGHT ROUTES
# =========================================================
@app.route("/add-weight", methods=["POST"])
@login_required
def add_weight():
    user_id = session["user_id"]
    weight = request.form.get("weight", "").strip()
    record_date = request.form.get("record_date", "").strip() or str(date.today())

    try:
        weight = float(weight)
        if weight <= 0:
            raise ValueError
    except ValueError:
        flash("Please enter a valid weight.", "error")
        return redirect(url_for("fitness"))

    run_query(
        "INSERT INTO weight_history (user_id, weight, record_date) VALUES (%s,%s,%s)",
        (user_id, weight, record_date), commit=True,
    )
    flash("Weight entry added.", "success")
    return redirect(url_for("fitness"))


@app.route("/edit-weight/<int:record_id>", methods=["POST"])
@login_required
def edit_weight(record_id):
    user_id = session["user_id"]
    weight = request.form.get("weight", "").strip()
    record_date = request.form.get("record_date", "").strip()

    try:
        weight = float(weight)
        if weight <= 0:
            raise ValueError
    except ValueError:
        flash("Please enter a valid weight.", "error")
        return redirect(url_for("fitness"))

    run_query(
        "UPDATE weight_history SET weight=%s, record_date=%s WHERE id=%s AND user_id=%s",
        (weight, record_date, record_id, user_id), commit=True,
    )
    flash("Weight entry updated.", "success")
    return redirect(url_for("fitness"))


@app.route("/delete-weight/<int:record_id>", methods=["POST"])
@login_required
def delete_weight(record_id):
    user_id = session["user_id"]
    run_query(
        "DELETE FROM weight_history WHERE id=%s AND user_id=%s",
        (record_id, user_id), commit=True,
    )
    flash("Weight entry deleted.", "success")
    return redirect(url_for("fitness"))


# =========================================================
# WORKOUT ROUTES
# =========================================================
@app.route("/add-workout", methods=["POST"])
@login_required
def add_workout():
    user_id = session["user_id"]
    workout_type = request.form.get("workout_type", "").strip()
    duration = request.form.get("duration", "").strip()
    calories_burned = request.form.get("calories_burned", "").strip()
    workout_date = request.form.get("workout_date", "").strip() or str(date.today())

    try:
        duration = int(duration)
        calories_burned = int(calories_burned)
        if duration <= 0 or calories_burned < 0 or not workout_type:
            raise ValueError
    except ValueError:
        flash("Please enter valid workout details.", "error")
        return redirect(url_for("fitness"))

    run_query(
        "INSERT INTO workouts (user_id, workout_type, duration, calories_burned, workout_date) "
        "VALUES (%s,%s,%s,%s,%s)",
        (user_id, workout_type, duration, calories_burned, workout_date), commit=True,
    )
    flash("Workout added.", "success")
    return redirect(url_for("fitness"))


@app.route("/edit-workout/<int:record_id>", methods=["POST"])
@login_required
def edit_workout(record_id):
    user_id = session["user_id"]
    workout_type = request.form.get("workout_type", "").strip()
    duration = request.form.get("duration", "").strip()
    calories_burned = request.form.get("calories_burned", "").strip()
    workout_date = request.form.get("workout_date", "").strip()

    try:
        duration = int(duration)
        calories_burned = int(calories_burned)
    except ValueError:
        flash("Please enter valid workout details.", "error")
        return redirect(url_for("fitness"))

    run_query(
        "UPDATE workouts SET workout_type=%s, duration=%s, calories_burned=%s, workout_date=%s "
        "WHERE id=%s AND user_id=%s",
        (workout_type, duration, calories_burned, workout_date, record_id, user_id), commit=True,
    )
    flash("Workout updated.", "success")
    return redirect(url_for("fitness"))


@app.route("/delete-workout/<int:record_id>", methods=["POST"])
@login_required
def delete_workout(record_id):
    user_id = session["user_id"]
    run_query(
        "DELETE FROM workouts WHERE id=%s AND user_id=%s",
        (record_id, user_id), commit=True,
    )
    flash("Workout deleted.", "success")
    return redirect(url_for("fitness"))


# =========================================================
# STEP ROUTES
# =========================================================
@app.route("/add-steps", methods=["POST"])
@login_required
def add_steps():
    user_id = session["user_id"]
    steps = request.form.get("steps", "").strip()
    distance = request.form.get("distance", "0").strip() or "0"
    calories_burned = request.form.get("calories_burned", "0").strip() or "0"
    record_date = request.form.get("record_date", "").strip() or str(date.today())

    try:
        steps = int(steps)
        distance = float(distance)
        calories_burned = int(calories_burned)
        if steps < 0:
            raise ValueError
    except ValueError:
        flash("Please enter valid step details.", "error")
        return redirect(url_for("fitness"))

    existing = run_query(
        "SELECT id FROM steps WHERE user_id=%s AND record_date=%s",
        (user_id, record_date), fetch="one"
    )
    if existing:
        run_query(
            "UPDATE steps SET steps=%s, distance=%s, calories_burned=%s WHERE id=%s",
            (steps, distance, calories_burned, existing["id"]), commit=True,
        )
    else:
        run_query(
            "INSERT INTO steps (user_id, steps, distance, calories_burned, record_date) "
            "VALUES (%s,%s,%s,%s,%s)",
            (user_id, steps, distance, calories_burned, record_date), commit=True,
        )
    flash("Step entry saved.", "success")
    return redirect(url_for("fitness"))


@app.route("/edit-steps/<int:record_id>", methods=["POST"])
@login_required
def edit_steps(record_id):
    user_id = session["user_id"]
    steps = request.form.get("steps", "").strip()
    distance = request.form.get("distance", "0").strip() or "0"
    calories_burned = request.form.get("calories_burned", "0").strip() or "0"
    record_date = request.form.get("record_date", "").strip()

    try:
        steps = int(steps)
        distance = float(distance)
        calories_burned = int(calories_burned)
    except ValueError:
        flash("Please enter valid step details.", "error")
        return redirect(url_for("fitness"))

    run_query(
        "UPDATE steps SET steps=%s, distance=%s, calories_burned=%s, record_date=%s "
        "WHERE id=%s AND user_id=%s",
        (steps, distance, calories_burned, record_date, record_id, user_id), commit=True,
    )
    flash("Step entry updated.", "success")
    return redirect(url_for("fitness"))


@app.route("/delete-steps/<int:record_id>", methods=["POST"])
@login_required
def delete_steps(record_id):
    user_id = session["user_id"]
    run_query(
        "DELETE FROM steps WHERE id=%s AND user_id=%s",
        (record_id, user_id), commit=True,
    )
    flash("Step entry deleted.", "success")
    return redirect(url_for("fitness"))


# =========================================================
# GOAL ROUTES
# =========================================================
@app.route("/add-goal", methods=["POST"])
@login_required
def add_goal():
    user_id = session["user_id"]
    goal_type = request.form.get("goal_type", "").strip()
    target_value = request.form.get("target_value", "").strip()
    current_value = request.form.get("current_value", "0").strip() or "0"
    target_date = request.form.get("target_date", "").strip() or None

    try:
        target_value = float(target_value)
        current_value = float(current_value)
        if not goal_type or target_value <= 0:
            raise ValueError
    except ValueError:
        flash("Please enter valid goal details.", "error")
        return redirect(url_for("fitness"))

    run_query(
        "INSERT INTO fitness_goals (user_id, goal_type, target_value, current_value, target_date) "
        "VALUES (%s,%s,%s,%s,%s)",
        (user_id, goal_type, target_value, current_value, target_date), commit=True,
    )
    flash("Goal created.", "success")
    return redirect(url_for("fitness"))


@app.route("/edit-goal/<int:record_id>", methods=["POST"])
@login_required
def edit_goal(record_id):
    user_id = session["user_id"]
    current_value = request.form.get("current_value", "").strip()
    status = request.form.get("status", "Active").strip()

    try:
        current_value = float(current_value)
    except ValueError:
        flash("Please enter a valid value.", "error")
        return redirect(url_for("fitness"))

    run_query(
        "UPDATE fitness_goals SET current_value=%s, status=%s WHERE id=%s AND user_id=%s",
        (current_value, status, record_id, user_id), commit=True,
    )
    flash("Goal updated.", "success")
    return redirect(url_for("fitness"))


@app.route("/delete-goal/<int:record_id>", methods=["POST"])
@login_required
def delete_goal(record_id):
    user_id = session["user_id"]
    run_query(
        "DELETE FROM fitness_goals WHERE id=%s AND user_id=%s",
        (record_id, user_id), commit=True,
    )
    flash("Goal deleted.", "success")
    return redirect(url_for("fitness"))


# =========================================================
# MEAL ROUTES
# =========================================================
@app.route("/add-meal", methods=["POST"])
@login_required
def add_meal():
    user_id = session["user_id"]
    food_name = request.form.get("food_name", "").strip()
    calories = request.form.get("calories", "").strip()
    meal_type = request.form.get("meal_type", "").strip()
    meal_date = request.form.get("meal_date", "").strip() or str(date.today())

    try:
        calories = int(calories)
        if not food_name or not meal_type or calories < 0:
            raise ValueError
    except ValueError:
        flash("Please enter valid meal details.", "error")
        return redirect(url_for("diet_profile"))

    run_query(
        "INSERT INTO meals (user_id, food_name, calories, meal_type, meal_date) "
        "VALUES (%s,%s,%s,%s,%s)",
        (user_id, food_name, calories, meal_type, meal_date), commit=True,
    )
    flash("Meal added.", "success")
    return redirect(url_for("diet_profile"))


@app.route("/edit-meal/<int:record_id>", methods=["POST"])
@login_required
def edit_meal(record_id):
    user_id = session["user_id"]
    food_name = request.form.get("food_name", "").strip()
    calories = request.form.get("calories", "").strip()
    meal_type = request.form.get("meal_type", "").strip()
    meal_date = request.form.get("meal_date", "").strip()

    try:
        calories = int(calories)
    except ValueError:
        flash("Please enter valid meal details.", "error")
        return redirect(url_for("diet_profile"))

    run_query(
        "UPDATE meals SET food_name=%s, calories=%s, meal_type=%s, meal_date=%s "
        "WHERE id=%s AND user_id=%s",
        (food_name, calories, meal_type, meal_date, record_id, user_id), commit=True,
    )
    flash("Meal updated.", "success")
    return redirect(url_for("diet_profile"))


@app.route("/delete-meal/<int:record_id>", methods=["POST"])
@login_required
def delete_meal(record_id):
    user_id = session["user_id"]
    run_query(
        "DELETE FROM meals WHERE id=%s AND user_id=%s",
        (record_id, user_id), commit=True,
    )
    flash("Meal deleted.", "success")
    return redirect(url_for("diet_profile"))


# =========================================================
# PROFILE ROUTES
# =========================================================
@app.route("/profile")
@login_required
def profile():
    return redirect(url_for("diet_profile"))


@app.route("/update-profile", methods=["POST"])
@login_required
def update_profile():
    user_id = session["user_id"]
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()
    height = request.form.get("height", "").strip()

    try:
        age = int(age)
        height = float(height)
        if age <= 0 or height <= 0 or not full_name:
            raise ValueError
    except ValueError:
        flash("Please enter valid profile details.", "error")
        return redirect(url_for("diet_profile"))

    run_query(
        "UPDATE users SET full_name=%s, phone=%s, age=%s, gender=%s, height=%s WHERE id=%s",
        (full_name, phone, age, gender, height, user_id), commit=True,
    )
    session["user_name"] = full_name
    flash("Profile updated.", "success")
    return redirect(url_for("diet_profile"))


# =========================================================
# JSON API - used by dashboard charts (Chart.js)
# =========================================================
@app.route("/api/chart-data")
@login_required
def chart_data():
    user_id = session["user_id"]
    today = date.today()
    start = today - timedelta(days=13)  # last 14 days

    weights = run_query(
        "SELECT weight, record_date FROM weight_history "
        "WHERE user_id=%s AND record_date>=%s ORDER BY record_date ASC",
        (user_id, start), fetch="all"
    )
    workouts = run_query(
        "SELECT workout_date, duration, calories_burned FROM workouts "
        "WHERE user_id=%s AND workout_date>=%s",
        (user_id, start), fetch="all"
    )
    steps = run_query(
        "SELECT record_date, steps FROM steps WHERE user_id=%s AND record_date>=%s",
        (user_id, start), fetch="all"
    )
    meals = run_query(
        "SELECT meal_date, calories FROM meals WHERE user_id=%s AND meal_date>=%s",
        (user_id, start), fetch="all"
    )

    labels = [(start + timedelta(days=i)).isoformat() for i in range(14)]

    weight_map = {w["record_date"].isoformat(): float(w["weight"]) for w in weights}
    steps_map = {}
    for s in steps:
        d = s["record_date"].isoformat()
        steps_map[d] = steps_map.get(d, 0) + s["steps"]
    duration_map = {}
    burned_map = {}
    for w in workouts:
        d = w["workout_date"].isoformat()
        duration_map[d] = duration_map.get(d, 0) + w["duration"]
        burned_map[d] = burned_map.get(d, 0) + w["calories_burned"]
    calorie_map = {}
    for m in meals:
        d = m["meal_date"].isoformat()
        calorie_map[d] = calorie_map.get(d, 0) + m["calories"]

    return jsonify({
        "labels": labels,
        "weight": [weight_map.get(d) for d in labels],
        "steps": [steps_map.get(d, 0) for d in labels],
        "workout_minutes": [duration_map.get(d, 0) for d in labels],
        "calories_burned": [burned_map.get(d, 0) for d in labels],
        "calories_consumed": [calorie_map.get(d, 0) for d in labels],
        "calorie_target": app.config["DEFAULT_CALORIE_TARGET"],
    })


# =========================================================
# ERROR HANDLERS
# =========================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("index.html"), 404


@app.errorhandler(500)
def server_error(e):
    return "Something went wrong on our end. Please try again later.", 500


if __name__ == "__main__":
    app.run(debug=True)
