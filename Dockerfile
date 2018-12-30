FROM python:3-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN apk add --no-cache --virtual .pynacl_deps build-base python3-dev libffi-dev openssl-dev \
    libwebp-dev jpeg-dev openjpeg-dev tiff-dev tk-dev tcl-dev lcms2-dev freetype-dev zlib-dev \
    harfbuzz-dev fribidi-dev libjpeg-turbo-dev libpng-dev
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .

CMD ["python", "./main.py"]