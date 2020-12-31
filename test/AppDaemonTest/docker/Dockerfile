FROM python:stretch

RUN pip3 install robotframework robotframework-pabot webtest jsonpointer jsonpatch sqlalchemy virtualenv pyyaml
RUN virtualenv /homeassistant && . /homeassistant/bin/activate && pip install homeassistant==0.114 aiohttp_cors==0.7.0 pyotp==2.3.0 PyQRCode==1.2.1 sqlalchemy==1.3.16
RUN virtualenv /appdaemon && . /appdaemon/bin/activate && pip install 'appdaemon<4.0.0' robotframework python-dateutil astral==1.7.1
