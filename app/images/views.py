from flask import Blueprint, jsonify, request, send_file, make_response
from datetime import datetime
from app.images.models import Image
from app import db, config, cache
import os, io, time, hashlib
from PIL import Image as PILImage
from functools import wraps

mod = Blueprint('images', __name__)


sizes = {
    'thumbnail': (100, 100),
    'xs': (576, 576),
    'sm': (768, 768),
    'ms': (992, 992),
    'lg': (1200, 1200)
}


class _Image(PILImage.Image):

    def crop_to_aspect(self, aspect, divisor=1, alignx=0.5, aligny=0.5):
        """Crops an image to a given aspect ratio.
        Args:
            aspect (float): The desired aspect ratio.
            divisor (float): Optional divisor. Allows passing in (w, h) pair as the first two arguments.
            alignx (float): Horizontal crop alignment from 0 (left) to 1 (right)
            aligny (float): Vertical crop alignment from 0 (left) to 1 (right)
        Returns:
            Image: The cropped Image object.
        """
        if self.width / self.height > aspect / divisor:
            newwidth = int(self.height * (aspect / divisor))
            newheight = self.height
        else:
            newwidth = self.width
            newheight = int(self.width / (aspect / divisor))
        img = self.crop((alignx * (self.width - newwidth),
                         aligny * (self.height - newheight),
                         alignx * (self.width - newwidth) + newwidth,
                         aligny * (self.height - newheight) + newheight))
        return img


PILImage.Image.crop_to_aspect = _Image.crop_to_aspect


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

    return filename + '-' + str(time.time()) + '.png', file.content_type, file.stream


# One week
DEFAULT_CACHE_TIMEOUT = 604800


def cache_timeout(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        image = Image.query.filter_by(id=kwargs.get('id')).first()

        if not image:
            return f(*args, **kwargs)

        cache_timeout = DEFAULT_CACHE_TIMEOUT

        if image.expires:
            cache_timeout = (image.expires - datetime.now()).seconds

        if cache_timeout < 0:
            cache_timeout = DEFAULT_CACHE_TIMEOUT

        f.cache_timeout = cache_timeout
        return f(*args, **kwargs)
    return decorated_function


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
        pil_image.save(path + filename, 'PNG')
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


@mod.route('/<domain>/<id>/<file>', methods=['GET'])
@cache_timeout
@cache.cached(query_string=True)
def view_image(domain, id, file):
    def get_temp_file(pil_image):
        img_io = io.BytesIO()
        pil_image.save(img_io, 'PNG')
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
    crop = bool(request.args.get('crop'))

    cache_timeout = DEFAULT_CACHE_TIMEOUT

    if image.expires:
        cache_timeout = (image.expires - datetime.now()).seconds

    try:
        pil_image = PILImage.open(image.get_path())
    except FileNotFoundError:
        return jsonify({
            'status': 404,
            'message': 'No image found.'
        }), 404

    if crop:
        pil_image = pil_image.crop_to_aspect(sizes.get(size)[0], sizes.get(size)[1])

    if size in sizes:
        pil_image.thumbnail(sizes.get(size))

    temp_file = get_temp_file(pil_image)

    response = make_response(send_file(temp_file, mimetype='image/png', cache_timeout=cache_timeout))

    if image.expires:
        response.headers['Expires'] = image.expires.strftime('%a, %d %b %Y %H:%M:%S GMT')

    return response


@mod.route('/<domain>/<id>/<file>', methods=['DELETE'])
def delete(domain, id, file):
    def _make_cache_key_query_string(args):
        args_as_sorted_tuple = tuple()

        if args:
            args_as_sorted_tuple = tuple(
                sorted(
                    (pair for pair in args.items())
                )
            )

        args_as_bytes = str(args_as_sorted_tuple).encode()
        hashed_args = str(hashlib.md5(args_as_bytes).hexdigest())
        cache_key = request.path + hashed_args

        return cache_key

    if domain not in config.sites.values():
        return jsonify({
            'status': 400,
            'message': 'Domain is not available.'
        }), 400

    secret = get_secret(request.headers)

    if config.sites.get(secret) != domain:
        return jsonify({
            'status': 400,
            'message': 'You do not have access to this domain.'
        }), 400

    image = Image.query.filter_by(domain=domain).filter_by(id=id).filter_by(filename=file).first()

    if not image:
        return jsonify({
            'status': 404,
            'message': 'No image found.'
        }), 404

    os.remove(image.get_path())

    db.session.delete(image)
    db.session.commit()

    for size in sizes:
        cache.delete(_make_cache_key_query_string({'size': size}))
        cache.delete(_make_cache_key_query_string({'size': size, 'crop': 'true'}))

    cache.delete(_make_cache_key_query_string(dict()))

    return jsonify({"msg": "OK"}), 200
