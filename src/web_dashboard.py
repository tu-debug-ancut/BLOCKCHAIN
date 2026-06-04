"""
Web Dashboard - Giao diện web thống kê + blockchain explorer
Flask + SSE cho real-time updates
"""

import json
import time
from flask import Flask, render_template, jsonify, Response, send_from_directory
import os


def create_app(ledger):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = "fatigue_guardian_2024"
    
    # Shared detector reference (set sau khi detector khởi động)
    app._ledger = ledger
    app._detector_ref = [None]  # Mutable container
    
    @app.route("/")
    def index():
        return render_template("dashboard.html")
    
    @app.route("/api/stats")
    def api_stats():
        stats = ledger.get_stats()
        live = {}
        if app._detector_ref[0]:
            live = app._detector_ref[0].get_live_stats()
        return jsonify({"blockchain": stats, "live": live})
    
    @app.route("/api/events")
    def api_events():
        events = ledger.get_recent_events(30)
        return jsonify(events)
    
    @app.route("/api/chain")
    def api_chain():
        chain = ledger.get_chain_json()
        return jsonify(chain)
    
    @app.route("/api/stream")
    def api_stream():
        """Server-Sent Events cho real-time updates"""
        def generate():
            while True:
                stats = ledger.get_stats()
                live = {}
                if app._detector_ref[0]:
                    live = app._detector_ref[0].get_live_stats()
                
                data = json.dumps({"blockchain": stats, "live": live})
                yield f"data: {data}\n\n"
                time.sleep(1.5)
        
        return Response(generate(), mimetype="text/event-stream",
                       headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    
    @app.route("/api/add_break", methods=["POST"])
    def add_break():
        ledger.add_event("BREAK_TAKEN", {"source": "manual_dashboard"})
        return jsonify({"ok": True})
    
    return app
