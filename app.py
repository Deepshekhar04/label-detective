"""
Label Detective Flask Application
Main web application for analyzing food ingredient labels with personalized health verdicts.
"""

import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from werkzeug.utils import secure_filename

from utils.logging_utils import setup_logger, create_trace_id
from utils import firestore_client as db
from orchestrator.orchestrator import LabelDetectiveOrchestrator
from orchestrator.agents.evaluator import EvaluatorAgent

# Load environment variables
load_dotenv()

# App & Service Initialization
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

logger = setup_logger(level=os.getenv("LOG_LEVEL", "INFO"))
db.initialize_db()
orchestrator = LabelDetectiveOrchestrator()

# Metrics
scan_requests_total = Counter("scan_requests_total", "Total scan requests")
scan_errors_total = Counter("scan_errors_total", "Total scan errors")
scan_latency = Histogram("scan_latency_ms", "Scan latency in milliseconds")
human_review_count = Counter("human_review_count", "Number of human reviews created")
judge_disagreement_count = Counter(
    "judge_disagreement_count", "Number of judge disagreements"
)

# Default user profile
DEFAULT_PROFILE = {
    "display_name": "Guest User",
    "allergies": [],
    "diet_tags": [],
    "sustainability_goals": [],
    "ingredient_blocklist": [],
    "explain_level": "detailed",
    "data_consent": False,
    "created_at": datetime.utcnow().isoformat(),
}


def get_or_create_user_id():
    """Get user_id from session or create new."""
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    return session["user_id"]


def get_user_profile(user_id: str):
    """Load user profile or return default."""
    profile = db.get_user(user_id)
    if not profile:
        profile = DEFAULT_PROFILE.copy()
        profile["user_id"] = user_id

        # Save default profile if consent given
        if profile.get("data_consent"):
            db.save_user(user_id, profile)

    return profile


@app.route("/")
def index():
    """Landing page with input forms."""
    user_id = get_or_create_user_id()
    return render_template("index.html", user_id=user_id)


@app.route("/scan", methods=["POST"])
def scan():
    """
    Process ingredient scan and generate personalized verdict.
    """
    trace_id = create_trace_id()
    user_id = get_or_create_user_id()

    scan_requests_total.inc()

    try:
        # Determine input type
        input_type = request.form.get("input_type", "text")

        if input_type == "text":
            raw_input = request.form.get("ingredient_text", "")
        elif input_type == "image":
            # Handle file upload
            if "ingredient_image" not in request.files:
                return render_template("error.html", error="No image uploaded"), 400

            file = request.files["ingredient_image"]
            if file.filename == "":
                return render_template("error.html", error="No image selected"), 400

            raw_input = file.read()
        else:
            return render_template("error.html", error="Invalid input type"), 400

        # Load user profile
        user_profile = get_user_profile(user_id)

        # Run orchestrator
        with scan_latency.time():
            result = orchestrator.run_scan(
                user_id,
                {
                    "input_type": input_type,
                    "raw_input": raw_input,
                    "user_profile": user_profile,
                },
            )

        # Check for errors
        if "error" in result:
            scan_errors_total.inc()
            return render_template("error.html", error=result["error"]), 500

        # Check if review required
        if result.get("requires_review"):
            human_review_count.inc()
            return render_template(
                "pending_review.html",
                review_id=result.get("review_id"),
                session_id=result.get("session_id"),
                verdict=result["final_verdict"],
            )

        # Render result
        return render_template(
            "result.html",
            verdict=result["final_verdict"],
            session_id=result["session_id"],
            trace_id=result["trace_id"],
            trace=result["trace"],
            extraction=result.get("extraction_result", {}),
            user_profile=user_profile,
        )

    except Exception as e:
        scan_errors_total.inc()
        logger.error(f"[{trace_id}] Scan endpoint failed: {e}", exc_info=True)
        return render_template("error.html", error=str(e)), 500


@app.route("/profile", methods=["GET", "POST"])
def profile():
    """User profile page."""
    user_id = get_or_create_user_id()

    if request.method == "POST":
        # Update profile
        profile_data = {
            "display_name": request.form.get("display_name", "Guest User"),
            "allergies": [],
            "diet_tags": request.form.getlist("diet_tags"),
            "sustainability_goals": request.form.getlist("sustainability_goals"),
            "ingredient_blocklist": request.form.get("ingredient_blocklist", "").split(
                ","
            ),
            "explain_level": request.form.get("explain_level", "detailed"),
            "data_consent": request.form.get("data_consent") == "on",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Parse allergies
        allergy_names = request.form.getlist("allergy_name")
        allergy_severities = request.form.getlist("allergy_severity")

        for name, severity in zip(allergy_names, allergy_severities):
            if name.strip():
                profile_data["allergies"].append(
                    {
                        "name": name.strip(),
                        "severity": severity,
                        "canonical_name": name.strip().lower(),
                    }
                )

        # Clean blocklist
        profile_data["ingredient_blocklist"] = [
            item.strip()
            for item in profile_data["ingredient_blocklist"]
            if item.strip()
        ]

        # Save profile
        db.save_user(user_id, profile_data)

        return redirect(url_for("profile"))

    # GET request
    profile_data = get_user_profile(user_id)
    return render_template("profile.html", profile=profile_data)


@app.route("/history")
def history():
    """Scan history page."""
    user_id = get_or_create_user_id()

    # Get filters from query params
    filters = {}
    if request.args.get("verdict"):
        filters["verdict"] = request.args.get("verdict")

    # Fetch history
    scan_history = db.get_scan_history(user_id, filters)

    return render_template("history.html", scans=scan_history, filters=filters)


@app.route("/review", methods=["POST"])
def review():
    """
    Handle pending review confirmation or rejection for high-severity allergen detections.
    """
    review_id = request.form.get("review_id")
    action = request.form.get("action")  # 'confirm' or 'reject'
    notes = request.form.get("notes", "")

    user_id = get_or_create_user_id()

    if action == "confirm":
        # Update review status
        db.update_review_status(review_id, "approved", notes)
        return redirect(url_for("history"))

    elif action == "reject":
        db.update_review_status(review_id, "rejected", notes)
        return redirect(url_for("history"))

    else:
        return render_template("error.html", error="Invalid action"), 400


@app.route("/admin/evaluate", methods=["GET", "POST"])
def admin_evaluate():
    """
    Admin evaluation page for testing with golden dataset.
    """
    if request.method == "POST":
        # Handle CSV upload
        if "golden_dataset" not in request.files:
            return render_template("admin.html", error="No file uploaded"), 400

        file = request.files["golden_dataset"]
        if file.filename == "":
            return render_template("admin.html", error="No file selected"), 400

        # Save file temporarily
        import tempfile
        import csv

        # Read CSV
        csv_content = file.read().decode("utf-8")
        csv_reader = csv.DictReader(csv_content.splitlines())

        # Run evaluation
        evaluator = EvaluatorAgent()
        results = []
        total_score = 0
        correct_verdicts = 0
        total_tests = 0

        for row in csv_reader:
            total_tests += 1

            # Create mock user profile for test
            test_profile = DEFAULT_PROFILE.copy()

            # Run scan
            try:
                scan_result = orchestrator.run_scan(
                    "evaluator",
                    {
                        "input_type": "text",
                        "raw_input": row.get("input_text_or_image_url", ""),
                        "user_profile": test_profile,
                    },
                )

                # Evaluate
                expected = {
                    "expected_verdict": row.get("expected_verdict"),
                    "expected_ingredient_flags": eval(
                        row.get("expected_ingredient_flags", "{}")
                    ),
                }

                eval_result = evaluator.evaluate(
                    scan_result.get("final_verdict", {}), expected
                )

                total_score += eval_result["score"]
                if (
                    scan_result.get("final_verdict", {}).get("verdict")
                    == expected["expected_verdict"]
                ):
                    correct_verdicts += 1

                results.append(
                    {
                        "id": row.get("id", total_tests),
                        "input": row.get("input_text_or_image_url", "")[:50] + "...",
                        "expected": expected["expected_verdict"],
                        "actual": scan_result.get("final_verdict", {}).get("verdict"),
                        "score": eval_result["score"],
                        "feedback": eval_result["feedback"],
                    }
                )

            except Exception as e:
                results.append(
                    {
                        "id": row.get("id", total_tests),
                        "input": row.get("input_text_or_image_url", "")[:50] + "...",
                        "expected": row.get("expected_verdict"),
                        "actual": "ERROR",
                        "score": 0,
                        "feedback": str(e),
                    }
                )

        # Calculate metrics
        avg_score = total_score / total_tests if total_tests > 0 else 0
        accuracy = correct_verdicts / total_tests if total_tests > 0 else 0

        metrics = {
            "total_tests": total_tests,
            "avg_score": round(avg_score, 2),
            "accuracy": round(accuracy * 100, 2),
            "correct_verdicts": correct_verdicts,
        }

        return render_template("admin.html", results=results, metrics=metrics)

    # GET request
    return render_template("admin.html")


@app.route("/metrics")
def metrics():
    """
    Prometheus metrics endpoint for monitoring application health.
    """
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/api/save_to_history", methods=["POST"])
def api_save_to_history():
    """API endpoint to save scan to history."""
    user_id = get_or_create_user_id()
    data = request.json

    scan_id = db.save_scan_history(user_id, data)

    return jsonify({"success": True, "scan_id": scan_id})


@app.route("/api/block_ingredient", methods=["POST"])
def api_block_ingredient():
    """API endpoint to add ingredient to blocklist."""
    user_id = get_or_create_user_id()
    ingredient = request.json.get("ingredient")

    profile = get_user_profile(user_id)
    if ingredient not in profile.get("ingredient_blocklist", []):
        profile.setdefault("ingredient_blocklist", []).append(ingredient)
        db.save_user(user_id, profile)

    return jsonify({"success": True})


@app.route("/api/accept_disclaimer", methods=["POST"])
def api_accept_disclaimer():
    """API endpoint to accept disclaimer."""
    session["disclaimer_accepted"] = True
    return jsonify({"success": True})


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", error="Page not found"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", error="Internal server error"), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"

    app.run(host="0.0.0.0", port=port, debug=debug)
