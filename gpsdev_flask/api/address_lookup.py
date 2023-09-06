from flask import Blueprint, jsonify
import requests
from gpsdev_flask.api import api_login_required
from gpsdev_flask import config

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


@address_lookup.route('google/<string:address>', methods=['GET'])
@api_login_required
def api_address_google(address):
    url = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
    params = {'input': address,
              'language': 'RU',
              'key': config.TOKEN_GOOGLE_PLACES,
              'inputtype': 'textquery',
              'fields': 'formatted_address,geometry'
              }
    r = requests.get(url, params)
    result = [
        {
            'display_name': i.get('formatted_address'),
            'lat': i.get('geometry').get('location').get('lat'),
            'lon': i.get('geometry').get('location').get('lng'),
        }
        for i in r.json().get('candidates')]
    return jsonify(result)
