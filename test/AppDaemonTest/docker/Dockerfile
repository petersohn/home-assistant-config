FROM python:3.11

COPY python_requirements /python_requirements
RUN pip3 install -r /python_requirements/robot.txt
RUN virtualenv /homeassistant && . /homeassistant/bin/activate && pip install -r /python_requirements/homeassistant.txt
RUN virtualenv /appdaemon && . /appdaemon/bin/activate && pip install -r /python_requirements/appdaemon.txt
RUN rm -rf /python_requirements

