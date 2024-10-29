# :coding: utf-8
# :copyright: Copyright (c) 2024 ftrack

import ftrack_api

session = ftrack_api.Session()

recipients_user_names = ['<username>']
message_content = 'Message body'

# Query author and recipients. Note that the message will not appear if the
# author and recipient is the same user.
author = session.query(f"User where username is {session.api_user}").one()
recipients = session.query(
    "User where username in ('{}')".format("','".join(recipients_user_names))
).all()

# Create note / "internal email"
note = session.create('Note', {
    'author': author,
    'content': message_content
})

# Add recipients
for user in recipients:
    recipient = session.create('Recipient', {
        'note_id': note['id'],
        'resource_id': user['id']
    })
    note['recipients'].append(recipient)

# Persist changes to database / send "internal email"
session.commit()