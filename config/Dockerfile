FROM python:3.10.10

WORKDIR /usr/src/app

COPY requirements.txt .

ENV FFMPEG_PATH /usr/bin/ffmpeg

RUN export PATH=$PATH:$FFMPEG_PATH

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]