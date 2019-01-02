import os

secrets = {
    'SQLALCHEMY_DATABASE_URI': 'mysql+pymysql://root:' + os.getenv('MYSQL_ROOT_PASSWORD', 'dev') + '@' + os.getenv('MYSQL_URI', 'db') + '/' + os.getenv('MYSQL_DATABASE', 'pictiato') + '?charset=utf8mb4',
    'SECRET_KEY': os.getenv('SECRET_KEY', 'h:3{3NryuT;nc)DrC`hK'),
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    'CACHE_TYPE': 'redis'
}

settings = {
    'debug': os.getenv('FLASK_ENV', 'production') == 'development',
    'collation': 'utf8mb4_swedish_ci',
    'uri': os.getenv('URI', 'http://localhost/')
}

sites = {}

for k, v in [i.split(':') for i in os.getenv('SITES').split(' ')]:
    sites[k] = v