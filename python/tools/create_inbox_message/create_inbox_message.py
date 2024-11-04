# :coding: utf-8
# :copyright: Copyright (c) 2024 ftrack

import logging
import ftrack_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

session = ftrack_api.Session()

recipients_user_names = ['<username>']
message_content = 'Example message content from recipe'

# Query author and recipients. Note that the message will not appear if the
# author and recipient is the same user.
logger.info('Getting author and recipients...')
author = session.query(f"User where username is {session.api_user}").one()
recipients = session.query(
    f"""User where username in ('{"','".join(recipients_user_names)}')"""
).all()

# Create note / "internal email"
logger.info('Creating note/internal email...')
note = session.create('Note', {
    'author': author,
    'content': message_content
})

# Add recipients
logger.info('Creating recipients and adding to note/email...')
for user in recipients:
    recipient = session.create('Recipient', {
        'note_id': note['id'],
        'resource_id': user['id']
    })
    note['recipients'].append(recipient)

# Persist changes to database / send "internal email"
logger.info('Persisting to database/sending...')
session.commit()