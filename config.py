# config.py - Configuration file for the application
# For production, use environment variables instead

import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Database Configuration
    MYSQL_HOST = os.environ.get('DB_HOST') or 'srv1128.hstgr.io'
    MYSQL_USER = os.environ.get('DB_USER') or 'u973091162_swizosoft_int'
    MYSQL_PASSWORD = os.environ.get('DB_PASSWORD') or 'Internship@Swizosoft1'
    MYSQL_DB = os.environ.get('DB_NAME') or 'u973091162_internship_swi'
    
    # Admin Credentials
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Requires HTTPS

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    MYSQL_DB = 'test_database'

# Select configuration based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """Get configuration for the specified environment"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
