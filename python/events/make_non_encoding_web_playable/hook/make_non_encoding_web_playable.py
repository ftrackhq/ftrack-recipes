# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

import json
import functools
import os.path
import logging
import tempfile
import subprocess
import ftrack_api.session

logger = logging.getLogger('com.ftrack.recipes.make-non-encode-web-playable')


# Gathered from https://en.wikipedia.org/wiki/Video_file_format
ENCODING_SUPPORTED_EXTENSIONS_VIDEO = [
    '.3g2', '.3gp', '.asf', '.avi', '.drc', '.flv', '.m2v', '.m4p', '.m4v',
    '.m4v', '.mkv', '.mng', '.mov', '.mp2', '.mp4', '.mpe', '.mpeg', '.mpg',
    '.mpv', '.mxf', '.nsv', '.ogg', '.ogv', '.qt', '.rm', '.rmvb', '.roq',
    '.svi', '.vob','.webm', '.wmv', '.yuv'
]

#change these to match full path to the exact executables.
ffmpeg_cmd = 'ffmpeg'
ffprobe_cmd = 'ffprobe'


def exec_cmd(cmd):
    '''execute the provided *cmd*'''
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        (stdout, stderr) = process.communicate()
    except Exception:
        logger.exception(u'Failed to exectue command "{}"'.format(cmd[0]))
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
        raise EnvironmentError('Subprocess failed: %s' % cmd[0])

    return stdout


def generate_thumbnail(filepath):
    '''generate thumbnail from the given *filepath*'''
    destination = tempfile.NamedTemporaryFile(suffix='.jpg').name

    cmd = [ffmpeg_cmd]
    cmd += ['-v', 'error']
    cmd += ['-i', filepath]
    cmd += ['-ss', '0']
    cmd += ['-an', '-vframes', '1']
    cmd += ['-vcodec', 'mjpeg']
    cmd += ['-f', 'image2']
    cmd += [destination]

    exec_cmd(cmd)
    return destination


def get_info(filepath):
    '''get file information from the given *filepath*'''
    cmd = [ffprobe_cmd]
    cmd += ['-v', 'error']
    cmd += ['-print_format', 'json']
    cmd += ['-show_format']
    cmd += ['-show_streams']
    cmd += [filepath]
    result = exec_cmd(cmd)

    try:
        result = json.loads(result)
    except Exception:
        raise IOError('ffprobe failed')

    try:
        streams = result.get('streams', {})
        video_info = [
            stream for stream in streams if stream.get('codec_type') == 'video'
        ][0]
        format_info = result.get('format', {})

        frame_rates = video_info.get('r_frame_rate', '0/0').split('/')
        frame_rate = float(frame_rates[0]) / float(frame_rates[1])
    except Exception:
        frame_rate = 0

    frame_out = int(video_info.get('nb_frames', 0))
    if not frame_out:
        duration = float(format_info.get('duration', 0))
        frame_out = int(duration * frame_rate)

    meta = {
        'frameIn': 0,
        'frameOut': frame_out,
        'frameRate': frame_rate,
    }

    return meta
    

def callback(event, session):
    '''Non encoding make-web-playable hook.
    '''
    # http://ftrack-python-api.rtd.ftrack.com/en/stable/example/web_review.html?highlight=reviewable


    # run new event
    server_location = session.get(
        'Location',
        ftrack_api.symbol.SERVER_LOCATION_ID
    )

    version_id = event['data']['versionId']
    path = event['data']['path']

    version = session.get('AssetVersion', version_id)

    # Validate that the path is an accessible file.
    if not os.path.isfile(path):
        raise ValueError(
            '"{0}" is not a valid filepath.'.format(path)
        )

    # Validate file is of the supported format
    _, file_extension = os.path.splitext(path)
    if file_extension not in ENCODING_SUPPORTED_EXTENSIONS_VIDEO:
        logger.error(
            '"{0}" is not in a valid file format.'.format(path)
        )
        return
    
    # disable previous event if we are in any accepted format.
    event.stop()

    # publish the file for review without re encoding.
    component = version.create_component(
        path=path,
        data={
            'name': 'ftrackreview-mp4'
        },
        location=server_location
    )
    metadata = get_info(path)
    component['metadata']['ftr_meta'] = json.dumps(metadata)

    # generate and publish thumbnail
    thumbnail_path = generate_thumbnail(path)
    version.create_thumbnail(thumbnail_path)

    session.commit()
    logger.info('make-reviewable hook completed.')


def subscribe(session):
    '''Subscribe to events.'''
    topic = 'ftrack.connect.publish.make-web-playable'
    logger.info('Subscribing to event topic: {0!r}'.format(topic))
    # add new make web playable without encoding

    # Note, we are forcing the priority to a higher value (20)
    # than the default one (100) so we can intercept the old event
    # and stop it before it gets triggered, allowing us to override its behaviour.

    session.event_hub.subscribe(
        u'topic="{0}" and source.user.username="{1}"'.format(
            topic, session.api_user
        ),
        functools.partial(callback, session=session),
        priority=20
    )


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''
    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        logger.debug(
            'Not subscribing plugin as passed argument {0!r} is not an '
            'ftrack_api.Session instance.'.format(session)
        )
        return

    subscribe(session)
    logger.debug('Plugin registered')
