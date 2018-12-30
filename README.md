# Development
```
$ docker-compose build
$ docker-compose up
```

## URIs

### Pictiato
- GET: http://localhost/
- GET|POST: http://localhost/\<domain\>
- GET: http://localhost/i/\<domain\>/\<id\>/\<file\>?size=xs|sm|md|lg


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