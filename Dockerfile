FROM python:3.10
WORKDIR /app
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install --no-cache-dir git+https://github.com/zubsverlo/trajectory-report.git

CMD ["python3", "run.py"]