This is intended to use as server-to-server image upload. Image files uploaded are converted to WEBP format and resizing is supported with some predefined sizes. Caching of image requests is handled by Redis.

# Development
1. Copy .env-example to .env and make changes.
2. Add your domains that should be able to upload images to app/config.py

```
$ docker-compose build
$ docker-compose up
```

## URIs

### Pictiato
- GET: http://localhost/
- GET|POST: http://localhost/\<domain\>
- GET: http://localhost/\<domain\>/\<id\>/\<file\>?size=xs|sm|md|lg


### Adminer
- http://localhost:8080/

# Build
```
$ docker build -t pictiato .
```

# Create DB
```
$ docker exec CONTAINER_ID python /usr/src/app/create.py
```

# Example
Files are uploaded as multipart/form-data. Example below in Python.
```
import requests
requests.post('http://localhost/<domain>', files=dict(file=('myfile.jpeg', open('myfile.jpeg', 'rb'))), headers={'x-pictiato-secret': ''})
```