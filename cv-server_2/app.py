# coding=utf-8
import multiprocessing

from flask import Flask
from flask_restful import reqparse, Api, Resource

from billiardGame import Game

app = Flask(__name__)
api = Api(app)
parser = reqparse.RequestParser()
parser.add_argument('createdBy')
parser.add_argument('playerIds')
parser.add_argument('firstShotPlayerId')
parser.add_argument('timeStamp')
parser.add_argument('requestId')
parser.add_argument('gameId')
parser.add_argument('tableWidth')
parser.add_argument('tableHeight')

game = None


class ComputerVisionService(Resource):
    @staticmethod
    def get():
        return {'status': 'ok'}

    @staticmethod
    def post():
        args = parser.parse_args()
        start_game(args)
        return args


class GameResetService(Resource):
    @staticmethod
    def post():
        args = parser.parse_args()
        stop_game()
        return args


def start_game(game_context):
    global game
    game = Game(game_context=game_context)
    # game.enableDebugMode()
    game.set_camera_mode(mode='camera', video_path=0)
    game.start()


def stop_game():
    global game
    game.stop()


def test_mode():
    game_context = {
        "gameId": "test",
        "timeStamp": "test",
        "requestId": "test",
        "createdBy": "test",
        "firstShotPlayerId": "test",
        "playerIds": "test"
    }
    start_game(game_context)


def run():
    api.add_resource(ComputerVisionService, '/cv/game/start')
    api.add_resource(GameResetService, '/cv/game/stop')
    app.run(host='0.0.0.0')

if __name__ == '__main__':
    run()
