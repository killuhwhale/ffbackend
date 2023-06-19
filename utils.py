from instafitAPI.settings import env
import os


def get_env(key):
    if env(key):
        return env(key)
    return os.getenv(key, None)
