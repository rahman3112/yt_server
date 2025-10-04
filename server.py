from flask import send_file, Flask, request, jsonify, after_this_request, Response
from flask_cors import CORS
import subprocess
import os
import glob
import tempfile
import re
import json


app = Flask(__name__)
CORS(app)


# --- Your Existing Endpoints (Unchanged) ---

@app.route("/download", methods=["GET"])
def download_video():
    url = request.args.get("url")
    quality = request.args.get("q", "best")

    process = subprocess.Popen(
        ["yt-dlp", "-f", quality, "-o", "-", url],
        stdout=subprocess.PIPE
    )

    return Response(
        process.stdout,
        mimetype="video/mp4",
        headers={"Content-Disposition": "attachment; filename=video.mp4"}
    )

@app.route("/audio", methods=["GET"])
def download_audio():
    url = request.args.get("url")
    audio_format = request.args.get("format", "mp3")

    process = subprocess.Popen(
        [
            "yt-dlp",
            "-x",
            "--audio-format", audio_format,
            "-o", "-",
            url
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return Response(
        process.stdout,
        mimetype=f"audio/{audio_format}",
        headers={"Content-Disposition": f"attachment; filename=audio.{audio_format}"}
    )

@app.route("/get_transcript", methods=["GET"])
def get_transcript():
    url = request.args.get("url")
    tmpdir = tempfile.mkdtemp()
    output_template = os.path.join(tmpdir, "transcript.%(ext)s")

    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--skip-download",
        "-o", output_template,
        url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return f"Error downloading transcript:\n{result.stderr}", 500

    vtt_files = glob.glob(os.path.join(tmpdir, "*.vtt"))
    if not vtt_files:
        return "Transcript not found", 404

    transcript_file = vtt_files[0]

    @after_this_request
    def cleanup(response):
        try:
            os.remove(transcript_file)
            os.rmdir(tmpdir)
        except Exception as e:
            print("Cleanup failed:", e)
        return response

    return send_file(
        transcript_file,
        as_attachment=True,
        download_name="transcript.vtt",
        mimetype="text/vtt"
    )

if __name__ == "__main__":
    # Pre-load the LLM on server startup to avoid a long delay on the first request
    app.run(debug=True,host='0.0.0.0', port=5000, use_reloader=False)