from flask import url_for

def url_for2(endpoint, **values):
    return url_for(endpoint, **values).lstrip('/')
