FROM python:3

ADD ./src/run.py /run.py
ADD ./src/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
