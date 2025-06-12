import os
import json
from functools import wraps
from flask import Blueprint, redirect, url_for, session, request, flash, current_app, render_template
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from app.models.pending_video import PendingVideo
from app import db
from datetime import datetime
from werkzeug.utils import secure_filename

# Allow insecure HTTP (not recommended for production)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

youtube_bp = Blueprint('youtube', __name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

CLIENT_CONFIG = {
    "web": {
        "client_id": "15177856373-sl0cm3l80bncbsov7551ptm6jr40qmru.apps.googleusercontent.com",
        "project_id": "trusty-coder-462513-h6",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": [
            "http://127.0.0.1:5000/youtube/oauth2callback",
            "http://localhost:5000/youtube/oauth2callback"
        ],
        "javascript_origins": [
            "http://127.0.0.1:5000",
            "http://localhost:5000"
        ]
    }
}

def refresh_credentials():
    try:
        if 'credentials' not in session:
            return None
        credentials = Credentials(**session['credentials'])
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            session['credentials'] = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
        return credentials
    except Exception as e:
        current_app.logger.error(f"Error refreshing credentials: {e}")
        return None

def get_youtube_service():
    try:
        credentials = refresh_credentials()
        if not credentials:
            return None
        return build('youtube', 'v3', credentials=credentials, cache_discovery=False)
    except Exception as e:
        current_app.logger.error(f"Failed to build YouTube service: {e}")
        return None

@youtube_bp.route('/authorize')
def authorize():
    try:
        flow = Flow.from_client_config(CLIENT_CONFIG, SCOPES)
        flow.redirect_uri = "http://127.0.0.1:5000/youtube/oauth2callback"
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        session['state'] = state
        return redirect(authorization_url)
    except Exception as e:
        current_app.logger.error(f"YouTube authorization error: {e}")
        flash("Unable to connect to YouTube. Try again.", "error")
        return redirect(url_for('auth.dashboard'))

@youtube_bp.route('/oauth2callback')
def oauth2callback():
    try:
        if 'state' not in session:
            raise ValueError("Authentication state missing")
        state = session['state']
        flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, state=state)
        flow.redirect_uri = "http://127.0.0.1:5000/youtube/oauth2callback"
        authorization_response = request.url
        if not authorization_response:
            raise ValueError("No authorization code received")
        try:
            flow.fetch_token(authorization_response=authorization_response)
        except Exception as e:
            raise ValueError(f"Failed to obtain access token: {str(e)}")
        credentials = flow.credentials
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        try:
            youtube = build('youtube', 'v3', credentials=credentials)
            response = youtube.channels().list(part='snippet', mine=True).execute()
            if response.get('items'):
                channel = response['items'][0]
                session['channel_info'] = {
                    'title': channel['snippet']['title'],
                    'id': channel['id']
                }
                flash(f"Connected to channel: {channel['snippet']['title']}", "success")
            else:
                raise ValueError("No YouTube channel found")
        except Exception as e:
            raise ValueError("Connected but failed to access YouTube API")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash("Authentication failed. Please try again.", "error")
    finally:
        session.pop('state', None)
    return redirect(url_for('auth.dashboard'))

@youtube_bp.route('/disconnect')
def disconnect():
    try:
        session.pop('credentials', None)
        session.pop('channel_info', None)
        flash("YouTube disconnected successfully.", "success")
    except Exception as e:
        current_app.logger.error(f"Disconnect error: {e}")
        flash("Error disconnecting YouTube.", "error")
    return redirect(url_for('auth.dashboard'))

@youtube_bp.route('/upload-video')
def upload_video():
    if 'credentials' not in session:
        flash("Connect your YouTube account to upload videos.", "warning")
        return redirect(url_for('auth.dashboard'))
    return render_template('upload_video.html')

@youtube_bp.route('/channel-settings')
def channel_settings():
    if 'credentials' not in session:
        flash("Connect your YouTube account first.", "warning")
        return redirect(url_for('auth.dashboard'))
    try:
        youtube = get_youtube_service()
        response = youtube.channels().list(part='snippet,statistics', mine=True).execute()
        return render_template('channel_settings.html', channel_info=response['items'][0])
    except HttpError as e:
        current_app.logger.error(f"YouTube API error: {e}")
        flash("Error loading channel settings.", "error")
        return redirect(url_for('auth.dashboard'))

@youtube_bp.route('/upload', methods=['POST'])
def upload_process():
    title = request.form['title']
    description = request.form['description']
    privacy = request.form['privacy']
    video_file = request.files['video_file']

    # Get uploader ID from session
    uploader_id = session.get('user_id')  # or use current_user.id if using Flask-Login

    if not uploader_id:
        flash("Please log in before uploading.", "danger")
        return redirect(url_for('auth.login'))

    # Save file to a directory
    filename = secure_filename(video_file.filename)
    upload_path = os.path.join('pending_uploads', filename)
    video_file.save(upload_path)

    # Create a new PendingVideo object
    new_video = PendingVideo(
        title=title,
        description=description,
        filename=filename,
        filepath=upload_path,
        privacy_status=privacy,
        uploader_id=uploader_id,
        creator_id=uploader_id,
        status='pending',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.session.add(new_video)
    db.session.commit()

    flash('Video uploaded and sent for approval.', 'success')
    return redirect(url_for('auth.dashboard'))



@youtube_bp.route('/approve/<int:video_id>')
def approve_video(video_id):
    video = PendingVideo.query.get(video_id)

    if not video:
        flash("Video not found.", "danger")
        return redirect(url_for('views.creator_dashboard'))

    video.status = 'approved'
    db.session.commit()

    flash("Video approved and ready to upload.", "success")
    return redirect(url_for('views.creator_dashboard'))


@youtube_bp.route('/reject/<int:video_id>')
def reject_video(video_id):
    # your logic here
    return f"Rejected video {video_id}"