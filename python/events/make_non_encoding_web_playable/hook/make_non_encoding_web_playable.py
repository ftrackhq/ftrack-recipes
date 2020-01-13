# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

import json
import functools
import os.path
import logging
import tempfile
import subprocess
import ftrack_api.session

logger = logging.getLogger('ftrack.connect.publish.make-non-encode-web-playable')

#change these to match full path to the exact executables.
ffmpeg_cmd = 'ffmpeg'
ffprobe_cmd = 'ffprobe'


def exec_cmd(cmd):
    '''execute the provided *cmd*'''
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    (stdout, stderr) = process.communicate()

    if process.returncode:
        print 'Subprocess failed, dumping output:'
        print '--------------- %s -----------------' % cmd[0]
        print stderr
        print '--------------------------------------'
        raise EnvironmentError('Subprocess failed: %s' % cmd[0])

    return stdout


def generate_thumbnail(filepath):
    '''generate thumbnail from the given *filepath*'''
    destination = tempfile.NamedTemporaryFile(suffix='.jpg').name

    cmd = [
        ffmpeg_cmd, '-v', 'error', '-i', filepath, '-filter:v',
        'scale=300:-1', '-ss', '0', '-an', '-vframes', '1', '-vcodec',
        'mjpeg', '-f', 'image2', destination
    ]
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
        videoInfo = [
            stream for stream in streams if stream.get('codec_type') == 'video'
        ][0]
        formatInfo = result.get('format', {})

        frameRates = videoInfo.get('r_frame_rate', '0/0').split('/')
        frameRate = float(frameRates[0]) / float(frameRates[1])
    except Exception:
        frameRate = 0

    frameOut = int(videoInfo.get('nb_frames', 0))
    if not frameOut:
        duration = float(formatInfo.get('duration', 0))
        frameOut = int(duration * frameRate)

    meta = {
        'frameIn': 0,
        'frameOut': frameOut,
        'frameRate': frameRate,
    }

    return meta
    

def callback(event, session):
    '''Non encoding make-web-playable hook.
    '''
    # http://ftrack-python-api.rtd.ftrack.com/en/stable/example/web_review.html?highlight=reviewable

    # disable previous event
    event.stop()

    # run new event
    server_location = session.query(
        'Location where name is "ftrack.server"'
    ).one()

    versionId = event['data']['versionId']
    path = event['data']['path']

    version = session.get('AssetVersion', versionId)
    session.commit()

    # Validate that the path is an accessible file.
    if not os.path.isfile(path):
        raise ValueError(
            '"{0}" is not a valid filepath.'.format(path)
        )

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
