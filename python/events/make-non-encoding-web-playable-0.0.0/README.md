# Make non encoding web playable

This event replace and override the default make_web_playable event hook
provided with ftrack-connect, to make able the users to upload as
playable any video already correctly encoded.

## Scope

-   Override default hook

## Install and setup

1.  Make the required executables available on the system path
2.  Copy the plugin to the connect plugin directory

## Dependencies

-   Require FFMPEG and FFPROBE available on the filesystem path.