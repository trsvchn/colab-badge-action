FROM python:3.10
COPY ./src /cba/
ENTRYPOINT ["python", "/cba/action.py"]
