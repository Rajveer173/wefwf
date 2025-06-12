from flask import Blueprint, render_template, session, redirect, url_for, flash
from app.models.user import User
from app.models.pending_video import PendingVideo
from app import db

views = Blueprint('views', __name__)

# Creator Dashboard - sees videos pending their approval or uploaded by them
@views.route('/creator')
def creator_dashboard():
    if 'user_id' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('auth.login'))

    # Fetch pending videos where the user is the assigned creator
    pending_videos = PendingVideo.query.filter_by(creator_id=user.id, status='pending').all()

    return render_template('creator_dashboard.html', user=user, pending_videos=pending_videos)


# Editor Dashboard - manages YouTube uploads
@views.route('/editor')
def editor_dashboard():
    if 'user_id' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('auth.login'))

    # If YouTube is not connected, redirect to connect
    if 'credentials' not in session:
        flash("Please connect your YouTube account to proceed.", "warning")
        return redirect(url_for('youtube.authorize'))

    return render_template('editor_dashboard.html', user=user)
