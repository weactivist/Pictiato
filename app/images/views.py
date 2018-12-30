from flask import Blueprint, jsonify, request, send_file, make_response
from datetime import datetime
from app.images.models import Image
from app import db, config
import base64, os, re, io, sys
from PIL import Image as PILImage

mod = Blueprint('images', __name__)


content_types = {
    'image/gif': '.gif',
    'image/jpeg': '.jpeg',
    'image/png': '.png',
    'image/webp': '.webp'
}

sizes = {
    'xs': (576, 576),
    'sm': (768, 768),
    'ms': (992, 992),
    'lg': (1200, 1200)
}


def get_content_md5(headers):
    """
    :param headers: dict
    :return: string
    """
    content_md5 = headers.get('Content-MD5')

    return ''


def get_expires(headers):
    """
    :param headers: dict
    :return: datetime
    """
    expires = headers.get('Expires')

    if not expires:
        return None

    try:
        return datetime.strptime(expires, '%a, %d %b %Y %H:%M:%S GMT')
    except ValueError:
        raise ValueError('Incorrect Expires header date format. Should be RFC 1123 date format.')


def get_secret(headers):
    """
    :param headers: dict
    :return: string
    """
    secret = headers.get('x-pictiato-secret')

    if not secret:
        raise ValueError('Secret key header (x-pictiato-secret) is missing.')

    if len(secret) != 40:
        raise ValueError('Secret key header (x-pictiato-secret) is in wrong format (should be sha1).')

    if not config.sites.get(secret, False):
        raise ValueError('Secret key is invalid.')

    return str(secret)


def get_file(files):
    """
    :param form: dict
    :return: string
    """
    file = files.get('file')

    if not file:
        raise ValueError('File field is missing.')

    filename, file_extension = os.path.splitext(file.filename)

    return filename + '.webp', file.content_type, file.stream


@mod.route('/<domain>', methods=['GET'])
def missing(domain):
    return jsonify({
        'status': 404,
        'message': 'This route is missing. Use POST request.'
    }), 404


@mod.route('/<domain>', methods=['POST'])
def upload(domain):
    """
    HEADERS:
        Cache-Control (string):
            http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9
        Content-Length (int):
            https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13
        Content-MD5 (string):
            The base64-encoded 128-bit MD5 digest of the message (without the headers) according
            to RFC 1864. This header can be used as a message integrity check to verify that
            the data is the same data that was originally sent.
        Content-Type (string):
            https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.17
            Default: binary/octet-stream
        Expires (string):
            https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.21
        x-pictiato-secret (string):
            sha1 secret key to authenticate server-to-server
        Body (string):
            base64 encoded string
        Content-Disposition (string):
            https://www.w3.org/Protocols/rfc2616/rfc2616-sec19.html#sec19.5.1
    """

    if domain not in config.sites.values():
        return jsonify({
            'status': 400,
            'message': 'Domain is not available.'
        }), 400

    if not request.headers.get('Content-Type').startswith('multipart/form-data'):
        return jsonify({
            'status': 400,
            'message': 'Content-Type header should be multipart/form-data.'
        }), 400

    try:
        content_md5 = get_content_md5(request.headers)
        expires = get_expires(request.headers)
        secret = get_secret(request.headers)
        filename, content_type, body = get_file(request.files)
    except ValueError as e:
        return jsonify({
            'status': 400,
            'message': str(e)
        }), 400

    if config.sites.get(secret) != domain:
        return jsonify({
            'status': 400,
            'message': 'You do not have access to this domain.'
        }), 400

    path = '/bucket/' + config.sites.get(secret) + '/' + datetime.today().strftime('/%Y/%m/%d/')

    if not os.path.exists(path):
        os.makedirs(path)

    try:
        pil_image = PILImage.open(body)
        pil_image.save(path + filename, 'WEBP')
    except IOError:
        return jsonify({
            'status': 400,
            'message': 'Cannot save file.'
        }), 400

    image = Image(
        filename=filename,
        content_length=os.path.getsize(path + filename),
        expires=expires,
        domain=config.sites.get(secret)
    )

    db.session.add(image)
    db.session.commit()

    return jsonify(image.get_dict())


@mod.route('/<domain>', methods=['GET'])
def list_images(domain):
    if domain not in config.sites.values():
        return jsonify({
            'status': 400,
            'message': 'Domain is not available.'
        }), 400

    response = []

    for image in Image.query.filter_by(domain=domain).all():
        response.append(image.get_dict())

    return jsonify(response)


@mod.route('/i/<domain>/<id>/<file>', methods=['GET'])
def view_image(domain, id, file):
    def get_temp_file(pil_image):
        img_io = io.BytesIO()
        pil_image.save(img_io, 'WEBP')
        img_io.seek(0)

        return img_io

    if domain not in config.sites.values():
        return jsonify({
            'status': 400,
            'message': 'Domain is not available.'
        }), 400

    image = Image.query.filter_by(domain=domain).filter_by(id=id).filter_by(filename=file).first()

    if not image:
        return jsonify({
            'status': 404,
            'message': 'No image found.'
        }), 404

    size = request.args.get('size')

    cache_timeout = None

    if image.expires:
        cache_timeout = (image.expires - datetime.now()).seconds

    pil_image = PILImage.open(image.get_path())

    if size in sizes:
        pil_image.thumbnail(sizes.get(size))

    temp_file = get_temp_file(pil_image)

    response = make_response(send_file(temp_file, mimetype='image/webp', cache_timeout=cache_timeout))

    if image.expires:
        response.headers['Expires'] = image.expires.strftime('%a, %d %b %Y %H:%M:%S GMT')

    return response
