# :coding: utf-8
# :copyright: Copyright (c) 2024 Backlight

import logging
import os
import sys
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ftrack-connect-web-app-test-server')

DEPENDENCIES_DIRECTORY = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '../dependencies'
    )
)
sys.path.append(DEPENDENCIES_DIRECTORY)

from flask import Flask, send_from_directory
app = Flask(__name__)

@app.route("/webapps/<path:webapp>", defaults={'filename': 'index.html'})
@app.route("/webapps/<path:webapp>/<path:filename>")
def serve_static(webapp, filename):
    base_path = os.path.dirname(os.path.realpath(__file__))
    full_path = os.path.join(base_path, "static", webapp)
    unsanitized_path = re.sub('%2e', '.', full_path)
    return send_from_directory(unsanitized_path, filename)

@app.route("/")
def main_page():
    return "Main page"
