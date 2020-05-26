FROM python:stretch

RUN pip3 install robotframework webtest jsonpointer jsonpatch sqlalchemy virtualenv pyyaml
RUN virtualenv /homeassistant && . /homeassistant/bin/activate && pip install homeassistant
RUN virtualenv /appdaemon && . /appdaemon/bin/activate && pip install 'appdaemon<4.0.0' robotframework python-dateutil astral==1.7.1
