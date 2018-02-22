# Machine Setup

- [X] CPU is fine and GPU is not necessary

- [X] Ubuntu System is preferred


# API interface

1. Start the game


URL: `/cv/game/start`

Methods: POST

Payload:
```
{
  "gameId": "test",
  "tableWidth": "1000",
  "tableHeight": 1000,
  "timeStamp":"test",
  "requestId": "test",
  "createdBy": "test",
  "firstShotPlayerId": "test",
  "playerIds": "test"
}
```


2. Stop the game

URL: `/cv/game/stop`

Methods: POST

Payload:
```
{

}
```

3. Send config

Change url in config/config.py