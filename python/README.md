# ftrack python recipes

Note

The code examples are targeting python 3.X+

In this repository, you'll be able to find working example code
regarding action, events and python api and plugins usage in general.

## ftrack Api documentation

The main
[ftrack_api](http://ftrack-python-api.rtd.ftrack.com/en/stable/)
documentation is available online, and it should be used side by side
with this code base.

## Running code examples

For simplicity, and to ensure the code can be tested without affecting
production code, most of these examples are setup to be run as
standalone from within a virtual environment, so there won't be any need
of ftrack-connect running.

### Virtualenv

To ensure a sandboxed experience, we suggest to use **virtualenv**. Here
few links on how to install and activate it.

-   [install
    virtualenv](https://virtualenv.pypa.io/en/latest/installation.html)
-   [activate
    virtualenv](https://virtualenv.pypa.io/en/latest/user_guide.html)

### Dependencies

Each example (plugins apart) comes with a **requirements.txt** text file
which contains all the required dependencies. This file can be used to
install all the requirements with the following command:

``` bash
$ pip install -r requirements.txt --force
```

### Environment variables

As the code will have to connect to your ftrack server, in order to
work, we do expect, to be able to find some basic [environment
variable](http://ftrack-python-api.rtd.ftrack.com/en/stable/environment_variables.html?highlight=environment)
set.

-   FTRACK_SERVER : the address of your ftrack server
-   FTRACK_API_USER: the username to be used to authenticate to the
    server
-   FTRACK_API_KEY: user's api key to authenticate to the server

### Run as standalone

Runnin the code as standalone is easy as typing:\|

``` bash
$ python hook/<action_or_event>.py
```

### Run from connect

> [!CAUTION]
> Not all the actions and events can be run from ftrack-connect as it depends on the actions and events dependencies.
> Running actions from connect is not suggested for production use.


Copy the whole folder within the actions or events with name ending with -0.0.0, in the ftrack-connect plugin folder and restart connect.


### Running code in production environments

When in production the actions and events should be monitored in order to ensure they are restarted in case something goes wrong. This can be done in different ways, depending on the type of infrastructure.

## Docker 

A cross platform option is to use our [ftrack-service-example](https://github.com/ftrackhq/ftrack-service-example) to run and monitor them through the container's healthcheck.

## Supervisor

On *NIX platforms is possible to use [supervisor to run these as system daemons](https://arcwiki.rs.gsu.edu/en/ThingsBoard/system-service).