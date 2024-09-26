FROM python:3.10
WORKDIR /app
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install folium==0.17.0

CMD ["python3", "run.py"]
