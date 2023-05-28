FROM python:3.8 as py38
FROM python:3.11

COPY --from=py38 /usr/local/bin/python3.8 /usr/local/bin/python3.8
COPY --from=py38 /usr/local/lib/python3.8 /usr/local/lib/python3.8
COPY --from=py38 /usr/local/lib/libpython3.8.so.1.0 /usr/local/lib/libpython3.8.so.1.0
COPY --from=py38 /usr/local/lib/libpython3.8.so /usr/local/lib/libpython3.8.so

COPY python_requirements/robot.txt /python_requirements/robot.txt
RUN pip3 install -r /python_requirements/robot.txt
COPY python_requirements/homeassistant.txt /python_requirements/homeassistant.txt
RUN virtualenv /homeassistant && . /homeassistant/bin/activate && pip install -r /python_requirements/homeassistant.txt

RUN python3.8 -m pip install virtualenv
COPY python_requirements/appdaemon.txt /python_requirements/appdaemon.txt
RUN python3.8 -m virtualenv /appdaemon && . /appdaemon/bin/activate && pip install -r /python_requirements/appdaemon.txt

RUN rm -rf /python_requirements

