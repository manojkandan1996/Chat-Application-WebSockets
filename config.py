class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///chatapp.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
