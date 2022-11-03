copyright: Copyright (c) 2014-2022 ftrack

## Manage Project Schemas

A command line tools that export a single or all project schemas to JSON, with an option to restore schemas.

### Scope


* Backup project schema(s)
* Restore project schema(s), with rename.

### Running


Backing up a specific schema:

```cmd
     python manage_project_schemas.py backup --schema VFX --filename /tmp/test.json
```


Restoring:

```cmd
     python manage_project_schemas.py restore --schema VFX --destination VFX2 --filename /tmp/test.json
```


Help:

```cmd
    python manage_project_schemas.py --help
```

### Dependencies

* ftrack_api


### save roundtrip for schema crossdomain replication

#### suffcient rights on the current role and/or api key are expected

- backup
```cmd
set FTRACK_SERVER=olddomain
python manage_schemas.py backup --schema "SCHEMANAME" --filename c:\temp\schemaname.json
```
- verify with dry_run against other domain
```cmd
set FTRACK_SERVER=newdomain
python manage_schemas.py verify --dry_run --filename c:\temp\schemaname.json
```
- verify without dry run
- creates missing types, object types and status
```cmd
set FTRACK_SERVER=newdomain
python manage_schemas.py verify --filename c:\temp\schemaname.json
```
- restore with dry run
```cmd
set FTRACK_SERVER=newdomain
python manage_schemas.py restore --schema "schemaname" --destination "SCHEMANAME_OR_OTHERNAME" --dry_run --filename c:\temp\schemaname.json
```
- restore creates the schema
```cmd
set FTRACK_SERVER=newdomain
python manage_schemas.py restore --schema "schemaname" --destination "SCHEMANAME_OR_OTHERNAME" --filename c:\temp\schemaname.json
```