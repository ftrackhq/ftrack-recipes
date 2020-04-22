# :coding: utf-8
# :copyright: Copyright (c) 2014-2020 ftrack


import os
from lucidity import Template


def register():
    '''Register templates.'''
    projectBase = '{project.name}/CG/A_PROJ/{shot.name}'
    separator = os.path.sep

    return [
        Template('project-base-ae', separator.join([projectBase, 'AE'])),
        Template('project-base-c4d', separator.join([projectBase, 'C4D'])),
        Template('project-base-maya', separator.join([projectBase, 'MAYA'])),
        Template('project-base-nuke', separator.join([projectBase, 'NUKE'])),
        Template('project-cg-media-reference', '{project.name}/CG/B_MEDIA/REFERENCE'),
        Template('project-cg-media-stills-raster-fromclient', '{project.name}/CG/B_MEDIA/STILLS/RASTER'),
        Template('project-cg-media-stills-vector-fromclient', '{project.name}/CG/B_MEDIA/STILLS/VECTOR'),
        Template('project-cg-media-video-forcomp-3dassets', '{project.name}/CG/B_MEDIA/VIDEO/FOR_COMP/3D_ASSETS'),
        Template('project-cg-media-video-forcomp-c4dimages', '{project.name}/CG/B_MEDIA/VIDEO/FOR_COMP/C4D_IMAGES'),
        Template('project-cg-media-video-forcomp-fromedit', '{project.name}/CG/B_MEDIA/VIDEO/FOR_COMP/FROM_EDIT'),
        Template('project-cg-media-video-forcomp-mayaimages', '{project.name}/CG/B_MEDIA/VIDEO/FOR_COMP/MAYA_IMAGES'),
        Template('project-cg-media-video-forcomp-prerender', '{project.name}/CG/B_MEDIA/VIDEO/FOR_COMP/PRERENDER'),
        Template('project-cg-media-video-forcomp-stock', '{project.name}/CG/B_MEDIA/VIDEO/FOR_COMP/STOCK'),
        Template('project-cg-media-video-renders', '{project.name}/CG/B_MEDIA/VIDEO/RENDERS'),
        Template('project-shared-dailies', '{project.name}/SHARED/DAILIES'),
        Template('project-shared-forcg', '{project.name}/SHARED/FOR_CG'),
        Template('project-shared-foredit', '{project.name}/SHARED/FOR_EDIT'),
        Template('project-shared-prjdocs-boards', '{project.name}/SHARED/PRJ_DOCS/BOARDS'),
        Template('project-shared-prjdocs-brief', '{project.name}/SHARED/PRJ_DOCS/BRIEF'),
        Template('project-shared-prjdocs-fonts', '{project.name}/SHARED/PRJ_DOCS/FONTS'),
        Template('project-shared-prjdocs-fromclient', '{project.name}/SHARED/PRJ_DOCS/FROM_CLIENT'),
        Template('project-shared-prjdocs-reviewnotes', '{project.name}/SHARED/PRJ_DOCS/REVIEW_NOTES'),
        Template('project-shared-prjdocs-script', '{project.name}/SHARED/PRJ_DOCS/SCRIPT')
    ]
