#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2022 Walt Jones

import os
from os.path import normpath
import sys
import time
import logging
import shutil
import psutil
import glob
import re
import json

from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from watchdog.events import FileCreatedEvent

import ftrack_api


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("com.ftrack.recipes.tools.version_watchfolder")

# ftrack credentials
ftrack_server = os.environ.get("FTRACK_SERVER")
ftrack_api_key = os.environ.get("FTRACK_API_KEY")
ftrack_api_user = os.environ.get("FTRACK_API_USER")

# Folder to watch
watch_folder = os.environ.get("FTRACK_VERSION_WATCHFOLDER")

# Default regular expression, matches : TLW_306_016_010_v001 --> <project>_<shot>_<task>_v<version>

default_regex = os.environ.get(
    'FTRACK_VERSION_WATCHFOLDER_REGEX', 
    '(?P<project>[a-zA-Z0-9-].+)(?:[_])(?P<shot>[a-zA-Z0-9-].+)(?:[_])(?P<task>[a-zA-Z0-9-].+)(?:[_])(?:[v](?P<version>[\d].+))'
)

# Task status for upload
task_status = 'In Progress'

# Upload asset type
asset_type = "Upload"


if not any([ftrack_server, ftrack_api_key, ftrack_api_user]):
    msg = "Missing environment configuration for setting up ftrack session."
    logger.error(msg)
    raise ValueError(msg)

if not watch_folder:
    msg = "Missing environment FTRACK_VERSION_WATCHFOLDER for setting up watchfolder source path."
    logger.error(msg)
    raise ValueError(msg)


def has_handle(fpath):
    # Check if the file is open somewhere
    for proc in psutil.process_iter():
        try:
            for item in proc.open_files():
                if fpath == item.path:
                    return True
        except Exception:
            pass
    return False


class Watcher(object):
    watch_folder = None
    observer = PollingObserver()

    def __init__(self, watch_folder):
        self.watch_folder = normpath(watch_folder)
        logger.info(f'Set watchFolder to {self.watch_folder}')

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.watch_folder, recursive=True)
        self.observer.start()
        logger.info('Watcher started!')

        try:
            while True:
                time.sleep(5)
        except Exception as e:
            self.observer.stop()
            logger.error(f'Error: {e}')

        self.observer.join()

    def stop(self):
        self.observer.stop()

    def join(self):
        self.observer.join()


class Handler(FileSystemEventHandler):
    global watch_folder
    global task_status
    global asset_type

    @staticmethod
    def on_any_event(event):

        if event.is_directory:
            # Do nothing for new directories
            logger.debug(f'{event.src_path} is a folder, doing nothing')
            return None

        elif event.event_type == "modified":
            # Do nothing for modified files
            logger.debug(f'{event.src_path} has been modified, doing nothing')
            return None

        elif event.event_type == "created":
            # If this is a new file, process it
            file_path = event.src_path
            logger.debug(f'Event created {file_path}')

            done_path = os.path.join(watch_folder, "done")
            duplicate_path = os.path.join(watch_folder, "duplicates")

            if re.match(
                re.compile(
                    "(" + re.escape(done_path) + "|" + re.escape(duplicate_path) + ").*",
                    re.IGNORECASE,
                ),
                file_path,
            ):
                # Ignore stuff in done or duplicates folder
                logger.debug(f'Skipping done/dup file: {file_path}')
                return None

            try:
                # Filter to movie files only
                if re.match(re.compile(".*\.(mov|qt|mp4)$", re.IGNORECASE), file_path):
                    head, tail = os.path.split(file_path)
                    try:
                        os.makedirs(done_path)
                        os.makedirs(duplicate_path)
                    except:
                        pass
                    done_file = os.path.join(done_path, tail)
                    duplicate_file = os.path.join(duplicate_path, tail)

                    # Wait until the file has finished copying so we know for sure it's all there
                    while has_handle(file_path):
                        logger.debug(
                            f'Waiting for {file_path} to finish copying...'
                        )
                        time.sleep(3)

                    # Check if this file exists in done folder
                    if os.path.isfile(done_file):
                        logger.warning(
                            f'Skipping  {file_path} as this exists in done folder. Please delete there if uploading again.'
                        )

                        # Move file to duplicate directory
                        shutil.move(file_path, duplicate_file)

                        return

                    # Upload to ftrack
                    upload_to_ftrack(file_path)

                    # Move file to done directory
                    shutil.move(file_path, done_file)

            except Exception as e:
                # raise
                logger.error(f'Skipping {file_path} due to {e}')

def upload_to_ftrack(upload_file):
    global watch_folder
    global task_status
    global asset_type

    file_path, file_name = os.path.split(upload_file)

    # Set up ftrack connection
    session = ftrack_api.Session()

    # Get all naming regex from ftrack and remove any duplicates for efficiency
    regex_list = []
    results = session.query(
        "select custom_attributes from Project where status is 'active'"
    ).all()
    for result in results:
        regex = None
        try:
            result["custom_attributes"]["ftrackRegEx"]
        except Exception as error:
            logger.error(f'{error}, using default regex : {default_regex}')
            regex = default_regex

        regex_list.append(regex)

    regex_list = list(dict.fromkeys(regex_list))

    shot_id = None
    # Try matching files against each regex until we succeed getting a matching shot in ftrack
    for regex in regex_list:
        shot_name = None
        task_name = None
        version = 0

        try:
            # Extract shot, task and version from filename using the current regex
            logger.debug(f'Trying regex {regex}')
            rx = re.compile(regex, re.IGNORECASE)
            match = rx.match(file_name)
            if match:
                result_dicts = match.groupdict()
                shot_name = result_dicts.get('shot')
                task_name = result_dicts.get('task')
                version = int(result_dicts.get('version'))
        except:
            # Couldn't match naming conventions, so try the next regex
            logger.debug('No match - passing')
            pass

        # Try getting matching shot in ftrack
        if shot_name is not None:
            logger.debug(f'shotName: {shot_name}.')
            try:
                # Get the shot ID for shotName in ftrack
                shot_id = session.query(
                    f'select id from Shot where name is "{shot_name}"'
                ).first()["id"]
                break
            except:
                # Unable to find shot, so try the next regex
                logger.debug(
                    f'No shot found in ftrack named: {shot_name} - passing.'
                )
                pass

    # If we get here and shotName hasn't been set, we failed to match all naming conventions
    if shot_name is None:
        raise Exception('Failed to match any naming conventions')

    # If we get here and shotID hasn't been set, we couldn't find a valid shot in ftrack
    if shot_id is None:
        raise Exception(
            f'Failed to find a matching shot {shot_name} in ftrack for {file_name}.'
            )

    logger.debug(f'shot id : {shot_id}')

    # Find matching task under that shot in ftrack
    try:
        task = session.query(
            f'Task where name is "{task_name}" and parent.id is "{shot_id}"'
        ).first()
    except Exception as e:
        raise Exception(
            f'Error looking for task {task_name} under shot {shot_name} in ftrack: {e}'
            )

    logger.debug(f'ftrack task : {task}')

    try:
        # Get task parent for linking
        asset_parent = task["parent"]
        asset_parent_id = asset_parent["id"]
    except:
        raise Exception(
            f'Unable to find task {task_name} under shot {shot_name} in ftrack'
        )

    logger.debug(f'asset parent : {asset_parent}')

    # Get asset
    assetName = re.sub(re.compile("\.(mov|qt|mp4)$", re.IGNORECASE), "", file_name)
    try:
        asset = session.query(
            f'Asset where parent.id is "{asset_parent_id}" and name is "{assetName}"'
        ).one()
        logger.debug(f'Using existing asset : {assetName}')

    except:
        # If asset doesn't exist, create it
        logger.debug(
            f'Creating new asset : {assetName} of type: {asset_type}'
        )

        # Get asset type entity
        ftrack_asset_type = session.query(f'AssetType where name is {asset_type}').one()

        logger.debug(f'assetType: {ftrack_asset_type}')

        asset = session.create(
            "Asset", {"name": assetName, "type": ftrack_asset_type, "parent": asset_parent}
        )
        logger.debug(f'Created new asset : {assetName} of type: {ftrack_asset_type}')

    try:
        # Try getting existing assetversion
        asset_version = session.query(
            f'AssetVersion where asset.id is "{asset["id"]}" and task.id is "{ task["id"]}" and version is "{version}"'
        ).one()
        logger.debug(f'Got existing assetversion: {asset_version}')

    except:
        # Create a new assetversion for this if one didn't already exist
        asset_version = session.create(
            "AssetVersion", {"asset": asset, "task": task, "version": version}
        )
        logger.debug(f'Created new assetversion: {asset_version}')

        session.commit()

    logger.info(f'Uploading {upload_file} to ftrack...')

    # Upload media
    job = asset_version.encode_media(upload_file, keep_original="True")
    logger.debug(f'Job: {job} ')

    job_data = json.loads(job["data"])
    logger.debug(f'Job Data: {job_data}')
    logger.debug(f'Source component id {job_data["source_component_id"]}')

    # Fix name on original component
    source_component = session.get(
        "Component", json.loads(job["data"])["source_component_id"]
    )
    source_component["name"] = assetName

    # Flip task status to QC Ready
    task_status = session.query(f'Status where name is "{task_status}"').first()
    task["status"] = task_status

    # Commit everything
    session.commit()

    logger.info(f'{upload_file}  uploaded to ftrack as {asset_version}')

    return True


if __name__ == "__main__":
    # Manually process any existing files first
    logger.info("Processing any existing files...")
    for file in glob.iglob(normpath(watch_folder) + "**/**", recursive=True):
        Handler().on_any_event(FileCreatedEvent(file))
    logger.info("Done processing existing files")

    # Create watcher for watchFolder
    watcher = Watcher(normpath(watch_folder))
    watcher.run()
