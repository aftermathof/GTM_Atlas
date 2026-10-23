"""Private object storage; local files remain a development/renderer workspace."""
import os
from urllib.parse import quote
from services.api import supabase


def enabled():
    return os.getenv('STORAGE_MODE', 'local') == 'supabase'


def path(key):
    if any(part in {'', '.', '..'} for part in key.split('/')):
        raise ValueError('Invalid object key')
    bucket = os.getenv('SUPABASE_STORAGE_BUCKET', 'gtm-private')
    return '/storage/v1/object/' + quote(bucket, safe='') + '/' + quote(key, safe='/')


def put_private(key, content, mime='application/octet-stream'):
    if enabled():
        supabase.call('POST', path(key), service=True, content=content, headers={'Content-Type': mime, 'x-upsert': 'true'})


def get_private(key):
    return supabase.call('GET', path(key), service=True).content


def delete_private(key):
    if enabled():
        path(key)  # Validate the object key before issuing a bucket-level remove.
        bucket = quote(os.getenv('SUPABASE_STORAGE_BUCKET', 'gtm-private'), safe='')
        supabase.call('DELETE', '/storage/v1/object/' + bucket, service=True, payload={'prefixes': [key]})
