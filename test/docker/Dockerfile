FROM python:3.11

COPY python_requirements/robot.txt /python_requirements/robot.txt
RUN pip3 install -r /python_requirements/robot.txt
COPY python_requirements/homeassistant.txt /python_requirements/homeassistant.txt
RUN virtualenv /homeassistant && . /homeassistant/bin/activate && pip install --no-deps -r /python_requirements/homeassistant.txt

COPY python_requirements/appdaemon.txt /python_requirements/appdaemon.txt
RUN virtualenv /appdaemon && . /appdaemon/bin/activate && pip install -r /python_requirements/appdaemon.txt

RUN rm -rf /python_requirements
