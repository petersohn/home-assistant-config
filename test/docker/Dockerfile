FROM python:3.11

COPY python_requirements/robot.txt /python_requirements/robot.txt
RUN pip3 install -r /python_requirements/robot.txt
COPY python_requirements/homeassistant.txt /python_requirements/homeassistant.txt
RUN virtualenv /homeassistant && . /homeassistant/bin/activate && pip install setuptools==70.0.0 wheel "Cython<3.0" poetry-core && pip install --no-deps homeassistant==2023.5.4 && pip install --no-build-isolation --only-binary=:all: -r /python_requirements/homeassistant.txt

COPY python_requirements/appdaemon.txt /python_requirements/appdaemon.txt
RUN virtualenv /appdaemon && . /appdaemon/bin/activate && pip install -r /python_requirements/appdaemon.txt

RUN rm -rf /python_requirements
