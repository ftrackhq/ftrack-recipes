# :coding: utf-8
# :copyright: Copyright (c) 2020 ftrack

import functools
import json
import logging
import os
import subprocess
import tempfile
import threading

import clique
import ftrack_api

logger = logging.getLogger('com.ftrack.recipes.encode-image-sequence')

SUPPORTED_THUMBNAIL_EXTENSIONS = (
    '.bmp',
    '.gif',
    '.jpeg',
    '.jpg',
    '.png',
    '.tif',
    '.tiff',
)
# For best restults, change this to the full path of the desired executable.
ffmpeg_cmd = 'ffmpeg'
frame_rate = 30


def async(fn):
    '''Run *fn* asynchronously.'''

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()

    return wrapper


class SequenceEncoder(object):
    '''Process an image sequence into a video file for review in ftrack.

    Given a make-web-playable event from Connect, converts an image
    sequence to an mp4 and uploads it as a new Component on the
    appropriate AssetVersion.
    '''

    def __init__(self, event, session, ffmpeg_cmd=ffmpeg_cmd, frame_rate=frame_rate):
        self._collection = None
        self._ffmpeg_cmd = ffmpeg_cmd
        self._frame_rate = frame_rate
        self._identifier = event['data']['path']
        self._session = ftrack_api.Session(
            session.server_url,
            session.api_key,
            session.api_user,
            auto_connect_event_hub=True,
            plugin_paths='',
        )
        self._user = self._session.query(
            'select id from User where username is "{}"'.format(
                event['source']['user']['username']
            )
        ).one()
        self._version = self._session.query(
            'select link from AssetVersion where id is "{}"'.format(
                event['data']['versionId']
            )
        ).one()

        try:
            # ffmpeg will stop at the first missing frame due to our padding string.
            self._collection = clique.parse(self._identifier).separate()[0]
        except ValueError:
            logger.debug('Path seems invalid, skipping')

        self._destination = tempfile.NamedTemporaryFile(suffix='.mp4').name

    @async
    def encode_and_upload(self):
        '''Handle creating and publishing a web-reviewable video for our event.

        Also, create a Job to report potentially long-running operations,
        and separately display success and failure messages as popups in the
        ftrack web interface.
        '''
        self._create_job()
        try:
            self._encode()
            self._update_job(description='Uploading reviewable for {link}')
            self._upload()
            self._update_job(
                status='done', description='Image sequence reviewable for {link}'
            )
        except Exception:
            self._update_job(status='failed')
            raise

    def _encode(self):
        '''Generate and execute the ffmpeg command to encode a reviewable video.'''
        cmd = self._get_cmd()
        logger.info(cmd)
        self._exec_cmd(cmd)

    def _upload(self):
        '''Upload our presumptive video file, with thumbnail and metadata.'''
        server_location = self._session.get(
            'Location', ftrack_api.symbol.SERVER_LOCATION_ID
        )
        component = self._version.create_component(
            path=self._destination,
            data={'name': 'ftrackreview-mp4'},
            location=server_location,
        )
        metadata = self._get_info()
        component['metadata']['ftr_meta'] = json.dumps(metadata)
        self._session.populate(self._version, 'thumbnail')
        if not self._version['thumbnail']:
            thumbnail_path = self._generate_thumbnail()
            self._version.create_thumbnail(thumbnail_path)

        self._session.commit()
        self._send_message_to_user('Encoding completed successfully', success=True)

    def _exec_cmd(self, cmd):
        '''Execute the provided *cmd*.'''
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            (stdout, stderr) = process.communicate()
        except Exception:
            logger.exception('Failed to exectue command "{}"'.format(cmd[0]))
            raise

        if process.returncode:
            logger.error(
                (
                    'Subprocess failed, dumping output:\n'
                    '--------------- {0} -----------------\n'
                    '{1}'
                    '--------------------------------------'
                ).format(cmd[0], stderr)
            )
            self._send_message_to_user('Image sequence encoding failed.', success=False)
            raise EnvironmentError('Subprocess failed: %s' % cmd[0])

        # ffmpeg writes only to stderr.
        return stderr

    def _generate_thumbnail(self):
        '''Generate thumbnail from the given *filepath*.'''
        first_frame = next(iter(self._collection))
        _, ext = os.path.splitext(first_frame)
        if ext.lower() in SUPPORTED_THUMBNAIL_EXTENSIONS:
            return first_frame

        destination = tempfile.NamedTemporaryFile(suffix='.jpg').name
        cmd = [self._ffmpeg_cmd, '-v', 'error', '-i', first_frame, destination]

        self._exec_cmd(cmd)
        return destination

    def _get_cmd(self):
        '''Constructs and returns the full ffmpeg command.

        Settings here are borrowed from ftrack video transcoding settings.
        For further information see: https://trac.ffmpeg.org/wiki/Encode/VFX
        '''
        cmd = [
            self._ffmpeg_cmd,
            '-start_number',
            str(next(iter(self._collection.indexes))),
            '-i',
            self._collection.format('{head}{padding}{tail}'),
            '-vf',
            "scale='trunc((a*oh)/2)*2':'min(720,trunc((a*ih)/2)*2)'",
            '-framerate',
            str(self._frame_rate),
            '-c:v',
            'libx264',
            '-pix_fmt',
            'yuv420p',
            '-b:v',
            '2000k',
            '-vprofile',
            'high',
            '-bf',
            '0',
            '-strict',
            'experimental',
            '-f',
            'mp4',
            '-g',
            '30',  # Set to 1 for a very large file with frame-by-frame playback
            self._destination,
        ]
        return cmd

    def _get_info(self):
        '''Returns a dictionary representing the metadata necessary for playback.'''
        meta = {'frameIn': 0, 'frameOut': self._duration, 'frameRate': self._frame_rate}
        return meta

    def _create_job(self):
        '''Creates a Job to represent the local work done to encode and upload.

        As a side-effect, we commit the local Session.
        '''
        self._job = self._session.create(
            'Job',
            data={
                'data': json.dumps(
                    {
                        'description': 'Client is encoding {}'.format(
                            self._version_link_text
                        )
                    }
                ),
                'status': 'running',
                'type': 'api_job',
                'user': self._user,
            },
        )
        self._session.commit()

    def _update_job(self, status=None, description=None):
        '''Update the *status* and/or *description* and commit the Session.'''
        if status is not None:
            self._job['status'] = status
        if description is not None:
            # To avoid stale data, we could del and populate this attribute.
            job_data = json.loads(self._job['data'])
            job_data['description'] = description.format(link=self._version_link_text)
            self._job['data'] = json.dumps(job_data)
        self._session.commit()

    @property
    def _version_link_text(self):
        return ' / '.join([item['name'] for item in self._version['link']])

    def is_valid(self):
        '''Return True if we could parse the path as a sequence with no missing files.'''
        if self._collection is None:
            return False
        for file in self._missing_files:
            return False
        return True

    @property
    def _missing_files(self):
        for item in self._collection:
            if not os.path.isfile(item):
                yield item

    @property
    def _duration(self):
        return len(self._collection.indexes)

    def _send_message_to_user(self, message='', success=True):
        '''Publish a message in the ftrack web-ui for the appropriate user.'''
        send_message_to_user(self._session, self._user['id'], success, message)


def callback(event, session):
    '''Supersedes the default Connect hook

    The hook callback accepts an *event*.

    event['data'] should contain:

        * versionId - The id of the version to make reviewable.
        * path - The path to the file to use as the component.

    Will raise :py:exc:`ValueError` if the provided path is not an accessible
    file.

    '''
    encoder = SequenceEncoder(event, session)

    if not encoder.is_valid():
        logger.debug('Cannot encode sequence from event: {}'.format(event))
        return

    event.stop()

    encoder.encode_and_upload()
    logger.info('make-reviewable hook completed.')


def send_message_to_user(session, user_id, message='', success=True):
    '''Send a success message to the active user.

    Use the event hub of *session* to pop up a message for the user with
    *user_id*.
    '''
    session.event_hub.publish(
        ftrack_api.event.base.Event(
            topic='ftrack.action.trigger-user-interface',
            data=dict(
                type='message',
                success=success,
                message='encode_image_sequence: {}'.format(message),
            ),
            target='applicationId=ftrack.client.web and user.id="{0}"'.format(user_id),
        ),
        on_error='ignore',
    )


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''
    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.Session):
        logger.debug(
            'Not subscribing plugin as passed argument {0!r} is not an '
            'ftrack_api.Session instance.'.format(session)
        )
        return

    topic = 'ftrack.connect.publish.make-web-playable'
    logger.info('Subscribing to event topic: {0!r}'.format(topic))
    session.event_hub.subscribe(
        'topic="{0}" and source.user.username="{1}"'.format(topic, session.api_user),
        functools.partial(callback, session=session),
        priority=50,  # The default is 100, so we'll beat the one bundled with Connect
    )
    logger.debug('Plugin registered')
