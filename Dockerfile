FROM python:3

COPY ./src /cba/
ENTRYPOINT ["python", "/cba/action.py"]
