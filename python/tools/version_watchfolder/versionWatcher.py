#!/usr/bin/env python
# :coding: utf-8
# :copyright: Copyright (c) 2022 Walt Jones

import os
import sys
import time
import logging
import tempfile
import ntpath
import shutil
import psutil
import glob
import re
from os.path import normpath
import ftrack_api
import json
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from watchdog.events import FileCreatedEvent


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
watchFolder = os.environ.get("FTRACK_VERSION_WATCHFOLDER")

# Task status for upload
task_status = 'QC Ready'

if not any([ftrack_server, ftrack_api_key, ftrack_api_user]):
    msg = "Missing environment configuration for setting up ftrack session."
    logger.error(msg)
    raise ValueError(msg)

if not watchFolder:
    msg = "Missing environment FTRACK_VERSION_WATCHFOLDER for setting up watchfolder source path."
    logger.error(msg)
    raise ValueError(msg)


def hasHandle(fpath):
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
    watchFolder = None
    observer = PollingObserver()

    def __init__(self, watchFolder):
        self.watchFolder = normpath(watchFolder)
        logger.info(f'Set watchFolder to {self.watchFolder}')

    def run(self):
        eventHandler = Handler()
        self.observer.schedule(eventHandler, self.watchFolder, recursive=True)
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
    global watchFolder

    @staticmethod
    def on_any_event(event):

        if event.is_directory:
            # Do nothing for new directories
            logger.debug(f'{event.src_path} is a folder, doing nothing')
            return None

        elif event.event_type == "modified":
            # Do nothing for modified files
            logger.debug(f'{event.src_path}  has been modified, doing nothing')
            return None

        elif event.event_type == "created":
            # If this is a new file, process it
            filePath = event.src_path
            logger.debug(f'Event created {filePath}')

            donePath = os.path.join(watchFolder, "done")
            duplicatePath = os.path.join(watchFolder, "duplicates")

            if re.match(
                re.compile(
                    "(" + re.escape(donePath) + "|" + re.escape(duplicatePath) + ").*",
                    re.IGNORECASE,
                ),
                filePath,
            ):

                # old version below
                # if re.match(re.compile("(" + donePath + "|" + duplicatePath + ").*", re.IGNORECASE), filePath):
                # Ignore stuff in done or duplicates folder
                logger.debug(f'Skipping done/dup file: {filePath}')
                return None

            try:
                # Filter to movie files only
                if re.match(re.compile(".*\.(mov|qt|mp4)$", re.IGNORECASE), filePath):
                    head, tail = os.path.split(filePath)
                    try:
                        os.makedirs(donePath)
                        os.makedirs(duplicatePath)
                    except:
                        pass
                    doneFile = os.path.join(donePath, tail)
                    duplicateFile = os.path.join(duplicatePath, tail)

                    # Wait until the file has finished copying so we know for sure it's all there
                    while hasHandle(filePath):
                        logger.debug(
                            f'Waiting for {filePath} to finish copying...'
                        )
                        time.sleep(3)

                    # Check if this file exists in done folder
                    if os.path.isfile(doneFile):
                        logger.warning(
                            f'Skipping  {filePath} as this exists in done folder. Please delete there if uploading again.'
                        )

                        # Move file to duplicate directory
                        shutil.move(filePath, duplicateFile)

                        return

                    # Upload to ftrack
                    uploadToFtrack(filePath)

                    # Move file to done directory
                    shutil.move(filePath, doneFile)

            except Exception as e:
                # raise
                logger.error(f'Skipping {filePath} due to {e}')


def uploadToFtrack(uploadFile):
    filePath, filename = os.path.split(uploadFile)

    # Set up ftrack connection
    session = ftrack_api.Session()

    # Get all naming regex from ftrack and remove any duplicates for efficiency
    regexList = []
    results = session.query(
        "select custom_attributes from Project where status is 'active'"
    ).all()
    for result in results:
        regexList.append(result["custom_attributes"]["ftrackRegEx"])
    regexList = list(dict.fromkeys(regexList))

    shotID = None
    # Try matching files against each regex until we succeed getting a matching shot in ftrack
    for regex in regexList:
        shotName = None
        try:
            # Extract shot, task and version from filename using the current regex
            logger.debug(f'Trying regex {regex}')
            regexSearch = re.search(re.compile(regex, re.IGNORECASE), filename)
            shotName = regexSearch.group(1)
            taskName = regexSearch.group(2)
            version = int(regexSearch.group(3).replace("v", ""))
        except:
            # Couldn't match naming conventions, so try the next regex
            logger.debug('No match - passing')
            pass

        # Try getting matching shot in ftrack
        if shotName is not None:
            logger.debug(f'shotName: {shotName}.')
            try:
                # Get the shot ID for shotName in ftrack
                shotID = session.query(
                    f'select id from Shot where name is "{shotName}"'
                ).first()["id"]
                break
            except:
                # Unable to find shot, so try the next regex
                logger.debug(
                    f'No shot found in ftrack named: {shotName} - passing.'
                )
                pass

    # If we get here and shotName hasn't been set, we failed to match all naming conventions
    if shotName is None:
        raise Exception('Failed to match any naming conventions')

    # If we get here and shotID hasn't been set, we couldn't find a valid shot in ftrack
    if shotID is None:
        raise Exception(
            f'Failed to find a matching shot {shotName} in ftrack for {filename}.'
            )

    logger.debug(f'shot id : {shotID}')

    # Find matching task under that shot in ftrack
    try:
        task = session.query(
            f'Task where name is "{taskName}" and parent.id is "{shotID}"'
        ).first()
    except Exception as e:
        raise Exception(
            f'Error looking for task {taskName} under shot {shotName} in ftrack: {e}'
            )

    logger.debug(f'ftrack task : {task}')

    try:
        # Get task parent for linking
        logger.info('Getting ftrack links for {uploadFile} ...')
        assetParent = task["parent"]
        assetParentID = assetParent["id"]
    except:
        raise Exception(
            f'Unable to find task {taskName}  under shot {shotName} in ftrack'
        )

    logger.debug(f'asset parent : {assetParent}')

    # Get asset
    assetName = re.sub(re.compile("\.(mov|qt|mp4)$", re.IGNORECASE), "", filename)
    assetType = "Upload"
    try:
        asset = session.query(
            f'Asset where parent.id is "{assetParentID}" and name is "{assetName}"'
        ).one()
        logger.debug(f'Using existing asset : {assetName}')

    except:
        # If asset doesn't exist, create it
        logger.debug(
            f'Creating new asset : {assetName} of type: {assetType}'
        )

        # Get asset type entity
        assetType = session.query(f'AssetType where name is {assetType}').one()

        logger.debug(f'assetType: {assetType}')

        asset = session.create(
            "Asset", {"name": assetName, "type": assetType, "parent": assetParent}
        )
        logger.debug(f'Created new asset : {assetName} of type: {assetType}')

    try:
        # Try getting existing assetversion
        assetVersion = session.query(
            f'AssetVersion where asset.id is "{asset["id"]}" and task.id is "{ task["id"]}" and version is "{version}"'
        ).one()
        logger.debug(f'Got existing assetversion: {assetVersion}')

    except:
        # Create a new assetversion for this if one didn't already exist
        assetVersion = session.create(
            "AssetVersion", {"asset": asset, "task": task, "version": version}
        )
        logger.debug(f'Created new assetversion: {assetVersion}')

        session.commit()

    logger.info(f'Uploading {uploadFile} to ftrack...')

    # Upload media
    job = assetVersion.encode_media(uploadFile, keep_original="True")
    logger.debug(f'Job: {job} ')

    jobData = json.loads(job["data"])
    logger.debug(f'Job Data: {jobData}')
    logger.debug(f'Source component id {jobData["source_component_id"]}')

    # if DEBUG: print("Keeping original component = " + str(jobData["keep_original"]))
    # for output in jobData["output"]:
    #    print("Output component - id: {0} format: {1}".format(output["component_id"], output["format"]))

    # Fix name on original component
    sourceComponent = session.get(
        "Component", json.loads(job["data"])["source_component_id"]
    )
    sourceComponent["name"] = assetName

    # Flip task status to QC Ready
    taskStatus = session.query(f'Status where name is "{task_status}"').first()
    task["status"] = taskStatus

    # Commit everything
    session.commit()

    logger.info(f'{uploadFile}  uploaded to ftrack as {assetVersion}')

    return True


if __name__ == "__main__":
    # Manually process any existing files first
    logger.info("Processing any existing files...")
    for file in glob.iglob(normpath(watchFolder) + "**/**", recursive=True):
        Handler().on_any_event(FileCreatedEvent(file))
    logger.info("Done processing existing files")

    # Create watcher for watchFolder
    watcher = Watcher(normpath(watchFolder))
    watcher.run()
