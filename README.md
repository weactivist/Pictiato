# Development
```
$ docker-compose build
$ docker-compose up
```

# Build
```
$ docker build -t pictiato .
```

# Create DB
```
$ docker exec CONTAINER_ID python /usr/src/app/create.py
```