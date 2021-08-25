
# Protocol

From [exitexit](https://github.com/exitexit/qsync-control/blob/master/qsync_control.py) with small changes for Qsync disovery and mac address.

## Get Scenes And Groups

### Request
1600

### Response

Raw response
```
1604000c000d  # full message of the initial QSync response specifying blind group count and scene count
```

Breakdown
```
16..........  # messages from QSync start with 0x16, messages to QSync start with 0x1b
..04........  # indicating the message body is 4 bytes long
....000c000d  # body binaries with the specified length
....000c....  # number of blind groups in subsequent messages, in this case, 12 groups
........000d  # number of scenes in subsequent messages, in this case, 15 scenes
```

### Response - group description

Raw response
```
162c010b00000000000000123456789abc65b08c79b00000180024c6976696e6720526f6f6d000000000000000000  # full message of a blind group description
```

Breakdown
```
16..........................................................................................  # messages from QSync start with 0x16
..2c........................................................................................  # indicating the message body is 44 bytes long
......0b....................................................................................  # blind group code, for identifying this blind group when communicating with QSync
......................123456789abc..........................................................  # Mac address of Qsync device
................................................8002........................................  # blind group address, for identifying this blind group in a particular scene
....................................................4c6976696e6720526f6f6d000000000000000000  # ASCII spelling out the group name, in this case, "Living Room"
```

### Response - scene description

Raw response
```
163b02800202c00502000000000000000000000000000000000000123456789abc5e9b5d41000000084d6f766965205363656e65000000000000000000  # full message of a scene description
```

Breakdown
```
16........................................................................................................................  # messages from QSync start with 0x16
..3b......................................................................................................................  # indicating the message body is 59 bytes long
......800202c00502000000000000000000000000000000000000....................................................................  # 24 bytes of info, encoding up to 8 blind groups added to this scene
......................................................123456789abc........................................................  # Mac address of Qsync device
......8002................................................................................................................  # 1st group in this scene, with group address 0x8002
..........02..............................................................................................................  # 1st group's desired shade position, in this case, all the way down
............c005..........................................................................................................  # 2nd group in this scene, with group address 0xc005
................02........................................................................................................  # 2nd group's desired shade position, in this case, all the way down
..................................................................................4d6f766965205363656e65000000000000000000  # ASCII spelling out the scene name, in this case, "Movie Scene"
```

## Discovery

### Request

Single `00` byte to UDP broadcast

### Response

Raw response
```
5550535441495253205153594e432000123456789abc01000ba10000ffff
```

Breakdown
```
5550535441495253205153594e4320..............................  # ASCII spelling out of Qsync device name, in this case "UPSTAIRS QSYNC"
................................123456789abc................  # Mac address of this Qsync device
```

## Group/scene control

### Request

Raw request
```
1b050000000901  # full message of the request sent to QSync to set a blind group to a specified shade position
```

Breakdown
```
1b............  # messages to QSync start with 0x1b
..05..........  # indicating the message body is 5 bytes long
..........09..  # group code of the blind group to the controlled
............01  # desired shade position
```

Note: group can be repeated up to eight times, so for example:

### Request

Raw request
```
1b0a00000009010000001602  # full message of the request sent to QSync to execute a scene
```

Breakdown
```
1b......................  # messages to QSync start with 0x1b
..0a....................  # indicating the message body is 10 bytes long
..........09............  # 1st group in this scene, in this case, with group code 0x09
............01..........  # 1st group's desired shade position, in this case, all the way up
....................16..  # 2nd group in this scene, in this case, with group code 0x16
......................02  # 2nd group's desired shade position, in this case, all the way down
```

### Response

Same as request, typically. Ignored.

# Position codes

The following are supported shade positions and their associated code:

| Position | Code |
| -------- | ---- |
| 0        | 01   |
| 12.5     | 06   |
| 25       | 07   |
| 37.5     | 09   |
| 50       | 08   |
| 62.5     | 0b   |
| 75       | 0c   |
| 87.5     | 0e   |
| 100      | 02   |
