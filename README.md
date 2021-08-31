# Qmotion-qsync

This package controls [Qmotion](https://www.legrand.us/qmotion) shades using a Qsync bridge device. 

The protocol is reverse engineered by inspecting network packets, with credit to [devbobo](https://github.com/devbobo/qmotion) and [exitexit](https://github.com/exitexit/qsync-control).	

Note that the Qsync must be installed and set up using the Qsync application before usage - this package provides no support for creating the groups and scenes involved in control.

Also note that there is no state in this system - all commands are fire and forget, with no returned data to see if the shade successfully received the command. Therefore, Qsync appears to retry commands multiple times in the hope that shades will (eventually) receive the command. This can make multiple serial commands problematic, see Groups below for more information. If you are having difficulty having shades respond to commands, look into Qsync physical location and possibly introduce Qrelay device(s). In my experience, problematic shades rarely respond better to repeated commands sent over this protocol.

## Usage

### Discovery
Qsync bridges can be discovered on the network using UDP broadcast:

```python
import qmotion_qsync

qsync = qmotion_qsync.discover_qsync()
```

If a Qsync device can be found on the network, a full-populated Qsync class will be returned.

Alternatively, you can not use discovery and define the Qsync device manually:

```python
from qmotion_qsync import Qsync

qsync = Qsync("192.168.1.2", set_groups_and_scenes=True)
```
Note that setting the groups and scenes will do a network call to the Qsync bridge. This is an optional step that sets those sub-objects into the Qsync object. For control of groups and scenes you do not need to do the `set_groups_and_scenes` call, assuming you already know your channel number or scene name.

### Group control
Qsync uses the concept of shade groups and are configured in the Qsync app. These groups can be a single shade (recommended for fine-grained control) or groups of shades. Note that a single shade can be in multiple groups, so you can have both fine grain control and bulk shade movement using groups effectively. The group -> shade mapping not stored in Qsync, and therefore this module has no knowledge of which shades are in which groups. Instead, shades "listen" for group numbers they are configured to be involved in and react accordingly. Up to eight shade groups can be controlled at the same time.

Repeated commands are problematic - the Qsync device appears to be fairly easily confused, plus commands appear to be repeated by the Qsync device and take a while to act upon. Therefore, I don't recommend individual controls of groups - it is better to use one command with a number of groups all at same time. That is, better to issue one request for eight commands than call this module eight times with individual commands.

```python
from qmotion_qsync import Qsync, ShadeGroup, ShadeGroupCommand

qsync = Qsync("192.168.1.2")
# Move shade group 20 to percent 25 (1/4 closed - so mostly open) and shade group 18 to half closed
qsync.set_group_position([ShadeGroupCommand(ShadeGroup(20), 25), 
	ShadeGroupCommand(ShadeGroup(18), 50)])
```

### Scene control
Qsync allows for scenes as well. A scene is the same as a group, in that it is up to eight shade groups that can be controlled at the same time to (possibly) different positions. The difference is the shade groups and percent for each group is pre-stored in the Qsync bridge. To call a scene, you use the text description of the scene, and the module will go look up what is stored for that scene and then set the shade groups appropriately.

```python
from qmotion_qsync import Qsync

qsync = Qsync("192.168.1.2")
qsync.set_scene("Family Room Down")
```
