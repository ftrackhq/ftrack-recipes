# :coding: utf-8
# :copyright: Copyright (c) 2024 Backlight

import logging
import threading
import os
import sys

logger = logging.getLogger()

DEPENDENCIES_DIRECTORY = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '../dependencies'
    )
)
sys.path.append(DEPENDENCIES_DIRECTORY)

RESOURCE_DIRECTORY = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '../resource'
    )
)
sys.path.append(RESOURCE_DIRECTORY)

import ftrack_api
import waitress

from app import app


def start_server():
    waitress.serve(app, port=8080)

def start_wsgi_server_thread():
    logger.info('Starting server...')
    thread = threading.Thread(target=start_server)
    thread.daemon = True
    thread.start()

def register(session, **kw):
    if not isinstance(session, ftrack_api.session.Session):
        return
    
    try:
        start_wsgi_server_thread()
    except Exception as e:
        logger.error('Failed to start server.')
