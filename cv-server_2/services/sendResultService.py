import requests
from datetime import datetime
import json
from config import config


def _api_payload_format(raw_data):
    print 'raw_data: ', raw_data
    location_data = [ {'x': 0, 'y': 0, 'status': 0} for _ in range(config.num_class)]
    for val in raw_data:
        index = int(val['class'])
        location_data[index]['x'] = (val['left'] + val['right']) / 2.0
        location_data[index]['y'] = (val['top'] + val['bottom']) / 2.0
        location_data[index]['status'] = 1
    return location_data


def send_result(raw_location_data, game_context):
    data = {
        'data': raw_location_data,
        'tableWidth': game_context['tableWidth'],
        'tableHeight': game_context['tableHeight'],
        'currentPlayerId': game_context['firstShotPlayerId'],
        'requestId': game_context['requestId'],
        'gameId': game_context['gameId'],
        'timeStamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    headers = {
        'Authorization': 'Bearer test'
    }
    try:
        print 'sending data...'
        print data
        response = requests.post(
            config.url,
            headers=headers,
            data=json.dumps(data)
        )
        if not response.status_code // 100 == 2:
            print 'Getting response ...'
    except requests.exceptions.RequestException as e:
        print 'Request wrong...'
