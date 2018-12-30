import os

secrets = {
    'SQLALCHEMY_DATABASE_URI': 'mysql+pymysql://root:' + os.getenv('MYSQL_ROOT_PASSWORD', 'dev') + '@' + os.getenv('MYSQL_URI', 'db') + '/' + os.getenv('MYSQL_DATABASE', 'pictiato') + '?charset=utf8mb4',
    'SECRET_KEY': os.getenv('SECRET_KEY', 'h:3{3NryuT;nc)DrC`hK'),
    'SQLALCHEMY_TRACK_MODIFICATIONS': False
}

settings = {
    'debug': os.getenv('FLASK_ENV', 'production') == 'development',
    'collation': 'utf8mb4_swedish_ci',
    'uri': os.getenv('URI', 'http://localhost/')
}

sites = {
    'b08daaf0a631344a5a63dbb536bce0a71077b08a': 'fishd.club'
}