from flask import Blueprint, jsonify
import requests
from gpsdev_flask.api import api_login_required

address_lookup = Blueprint('address_lookup', __name__)


@address_lookup.route('<string:address>', methods=['GET'])
@api_login_required
def api_address_lookup(address):
    url = 'https://nominatim.openstreetmap.org/search'
    params = {'format': 'json',
              'q': address,
              }
    r = requests.get(url, params)
    r = r.json()
    r = [{
        'display_name': i['display_name'],
        'lat': i['lat'],
        'lon': i['lon']
    } for i in r]
    return jsonify(r), 200
