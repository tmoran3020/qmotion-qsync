"""Module for controlling Qmotion blinds through a Qsync controller."""
__version__ = "0.0.1"

import socket
from socket import timeout
import logging

from .position import Position

from .const import DEFAULT_TIMEOUT
from .const import TCP_PORT
from .const import BROADCAST_ADDRESS
from .const import UDP_PORT
from .exceptions import InputError, QmotionConnectionError, Timeout, UnexpectedDataError

def discover_qsync(socket_timeout = DEFAULT_TIMEOUT):
    """
    Search for Qsync device on the local network.

    Note: uses UDP

    Returns Qsync object populatd with groups and scenes associated with this qsync device
    """
    # Single 00 byte
    message = bytes(1)
    address = (BROADCAST_ADDRESS, UDP_PORT)

    socket_udp = None
    try:
        socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_udp.settimeout(socket_timeout)
        socket_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        socket_udp.sendto(message, address)

        (data, (host, _port)) = socket_udp.recvfrom(1024)
        data_in_hex = bytes_to_hex(data)
        name_in_hex = data_in_hex[:30]
        name = bytes.fromhex(name_in_hex).decode().rstrip('\x00').strip()

        mac_address = data_in_hex[32:44]
        logging.debug('Qsync: found qsync at [%s], name [%s], mac [%s]', host, name,
                      mac_address)

        retval = Qsync(host)

        retval.name = name
        retval.mac_address = mac_address

        groups_scenes = retval.get_groups_and_scenes()

        retval.group_list = groups_scenes.group_list
        retval.scene_list = groups_scenes.scene_list

        return retval

    except Exception:
        error_message = "Could not connect to qysnc"
        logging.debug(error_message)
        raise QmotionConnectionError(error_message) from Exception

    finally:
        if socket_udp is not None:
            socket_udp.close()

def int_to_hex(input_int):
    """ Convert integer to hex string"""
    return '{:02x}'.format(input_int)

def bytes_to_hex(input_bytes):
    """ Convert bytes to hex string"""
    return ''.join('{:02x}'.format(x) for x in input_bytes)

def is_header(data_in_hex):
    """
    Check if input is a header line.

    A header is a control character string from Qsync. This is important to know if you are
    correctly at the start of the conversation or if you're picking it up midway.
    """
    return data_in_hex[:4] == '1604'

def is_group(data_in_hex):
    """
    Check if input is a group line.

    A group is one or more blinds that will all simultaneously react to group commands. Note that
    group membership is not stored on Qsync. Instead, each blind is manually programmed to groups
    and only the blinds themselves know which groups they belong to.
    """
    return data_in_hex[:4] == '162c'

def is_scene(data_in_hex):
    """
    Check if input is a scene line.

    A scene is between one and eight groups, and each group has a defined position. Not that scenes
    are not implemented like groups - the blinds do not understand scenes. Instead, the Qsync stores
    the scene <-> group relationship and then calls for each group to move in a single command.
    Therefore, there is nothing that can be done in a scene that could not be accomplished directly
    sending a list of group and positions.
    """
    return data_in_hex[:4] == '163b'

def parse_group(data_in_hex):
    """Parse a group entity from the group list returned by Qsync"""
    name_in_hex = data_in_hex[52:]
    name = bytes.fromhex(name_in_hex).decode().rstrip('\x00')
    code = data_in_hex[48:52]
    channel_in_hex = data_in_hex[6:8]
    channel = int(channel_in_hex, 16)
    # No particular point to this data, neglecting
    # mac_address = data_in_hex[22:34]
    logging.debug('Qsync: Group name [%s], channel [%d], code [%s]', name, channel, code)

    return ShadeGroup(channel, name, code)

def parse_scene(data_in_hex):
    """Parse a scene entity from the group list returned by Qsync"""
    name_in_hex = data_in_hex[82:]
    name = bytes.fromhex(name_in_hex).decode().rstrip('\x00')
    groups_in_hex = data_in_hex[6:54]
    # No particular point to this data, neglecting
    # mac_address = data_in_hex[54:66]

    logging.debug('Qsync: Scene name [%s]', name)

    command_list = []
    groups_in_hex_list = [groups_in_hex[i:i+6] for i in range(0, len(groups_in_hex), 6)]
    for group_in_hex in groups_in_hex_list:
        if group_in_hex == '000000':
            break
        code = group_in_hex[:4]
        position_code = group_in_hex[4:]

        command = ShadeGroupCommand(ShadeGroup(channel=0, code=code), position_code=position_code)
        logging.debug('Qsync: ShadeGroupCommand scene [%s], code [%s], position_code [%s]', name,
                      code, position_code)

        command_list.append(command)

    return Scene(name=name, command_list=command_list)

def build_group_dict(groups):
    """Build a dict of groups, code -> group."""
    group_dict = {}
    for group in groups:
        group_dict[group.code] = group

    return group_dict

def hydrate_scene(scene, groups):
    """Expand scene entities with referenced groups"""
    for command in scene.command_list:
        command.group = groups[command.group.code]

def clear_socket(socket_tcp):
    """
    Read all data in the socket


    Qsync does not appear to honor closed tcp connctions - the connetion contineues at same
    location as prior conversation. This can cause havoc for the next call. This method will
    read and discard all unexpected data, leaving the socket ready to start over again.
    """

    # We're going to time out here, it's expected. Might as well make it a short timeout then.
    socket_tcp.settimeout(1)

    try:
        while True:
            data = socket_tcp.recv(2048)
            logging.debug('Qsync: clear socket [%s]', bytes_to_hex(data))
    except timeout:
        # Expected - we can't know where we were in the data so read until timeout
        logging.debug("Caught expected timeout after clearing socket")
        return

def send_header(socket_tcp):
    """ Send a header requst to Qsync"""
    command = '1600'
    socket_tcp.send(bytes.fromhex(command))
    logging.debug('Qsync: send [%s]', command)

    data = socket_tcp.recv(2048)
    data_in_hex = bytes_to_hex(data)
    logging.debug('Qsync: receive [%s]', data_in_hex)

    if not is_header(data_in_hex):
        raise UnexpectedDataError("Header not received as expected")

    # Not suree what happens here, sometimes qsync 'freaks out' and returns this
    # instead of the real data. Trying again seems to clear it out.
    if data_in_hex == '1604ffffffff':
        raise UnexpectedDataError("Header not received as expected")

    return data_in_hex

class ShadeGroup:
    """Class representing a shade group, previously created through the qsync application"""

    def __init__(self, channel, name="", code=""):
        self.channel = channel
        self.name = name
        self.code = code

class Scene:
    """Class representing a shade group, previously createed through the qsync application
    """

    def __init__(self, name, command_list):
        self.name = name
        self.command_list = command_list

class ShadeGroupCommand:
    """Class representing a command for a shade group - which shade and which position

    group: ShadeGroup to change position
    percentage: 0-100 percentage to close the group (0 = full open, 100 = full closed)
    position_code: internal position code string, specify either percentage or position_code
    """

    def __init__(self, group, percentage=-1, position_code=""):
        self.group = group
        self.percentage = percentage
        self.position_code = position_code

class GroupsAndScenes:
    """Class contains a list of groups and a list of scenes

    group_list: List of ShadeGroup
    scene_list: List of Scene
    """

    def __init__(self, group_list, scene_list):
        self.group_list = group_list
        self.scene_list = scene_list

class Qsync:
    """Class representing an Qsync controller

    host: hostname or ip address
    socket_timeout: optional socket timeout that will overwrite default
    group_list: list of ShadeGroup objects (only in fully populated Qsync object)
    scene_list: list of Scene objects (only in fully populated Qsync object)
    """

    def __init__(self, host, socket_timeout=DEFAULT_TIMEOUT):
        self.host = host
        self.socket_timeout = socket_timeout
        self.group_list = []
        self.scene_list = []
        # Will be defined during discovery, not used otherwise
        self.name = ""
        self.mac_address = ""

    def set_group_position(self, group_command):
        """Set position of a list of shade groups.

        group_command: List of ShadeGroupCommand objects to set. Note: you may only specify
        from 1 to 8 different shade group command objects in a list
        """

        if len(group_command) > 8:
            raise InputError("Cannot specify more than eight groups to control")

        # returned values can vary from input, so update for return
        response_list = []

        command_body = ''
        for command in group_command:
            channel_code = int_to_hex(command.group.channel)
            if command.position_code:
                position = Position.get_position_code(command.position_code)
            else:
                position = Position.get_position(command.percentage)
            command_code = position.command_code
            command_body += '000000' + channel_code + command_code
            response_list.append(
                ShadeGroupCommand(ShadeGroup(command.group), position.position_times_ten / 10))

        socket_tcp = None
        try:
            socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_tcp.settimeout(self.socket_timeout)
            logging.debug("Qsync: connect host [%s], port [%d]", self.host, TCP_PORT)
            socket_tcp.connect((self.host, TCP_PORT))

            command_body_length = int(len(command_body)/2)  # number of bytes

            # Example: '1b050000000901'
            command = '1b' + int_to_hex(command_body_length) + command_body

            socket_tcp.send(bytes.fromhex(command))
            logging.debug('Qsync: send [%s]', command)

            data = socket_tcp.recv(2048)
            logging.debug('Qsync: receive [%s]', bytes_to_hex(data))

            return response_list
        except socket.error:
            error_message = "Could not connect to qysnc host [{host}], port [{tcp_port}]".format(
                host=self.host, tcp_port=TCP_PORT)
            logging.debug(error_message)
            raise QmotionConnectionError(error_message) from socket.error

        finally:
            if socket_tcp is not None:
                socket_tcp.close()

    def set_scene(self, name):
        """
        Set a number of blinds into a previous-defined scene.

        name: Plain language name of the scene to set.
        """
        for scene in self.get_groups_and_scenes().scene_list:
            if name == scene.name:
                self.set_group_position(scene.command_list)

    def get_groups_and_scenes(self):
        """
        Get the list of groups and scenes defined within the qsync device.

        Returns a GroupsAndScenes object that hold all groups and scenes stord on this qsync.
        """
        socket_tcp = None
        try:
            socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logging.debug("Qsync: connect host [%s], port [%d]", self.host, TCP_PORT)
            socket_tcp.connect((self.host, TCP_PORT))
            socket_tcp.settimeout(self.socket_timeout)

            try:
                data_in_hex = send_header(socket_tcp)
            except UnexpectedDataError:
                # Qsync gets into a bad state, clear it out and try again
                clear_socket(socket_tcp)
                data_in_hex = send_header(socket_tcp)

            body = data_in_hex[4:]
            number_of_groups = int(body[2:4], 16)
            logging.debug('Qsync: number of groups [%s]', number_of_groups)
            number_of_scenes = int(body[6:8], 16)
            logging.debug('Qsync: number of scenes [%s]', number_of_scenes)

            # Parse groups and scenes
            groups = []
            scenes = []
            for _ in range(number_of_groups + number_of_scenes):
                # Qsync sometimes appends the first group/scene onto the header
                if is_header(data_in_hex) and len(data_in_hex) > 12:
                    data_in_hex = body[12:]
                else:
                    data = socket_tcp.recv(2048)
                    data_in_hex = bytes_to_hex(data)

                logging.debug('Qsync: receive [%s]', data_in_hex)

                if is_group(data_in_hex):
                    groups.append(parse_group(data_in_hex))

                if is_scene(data_in_hex):
                    scenes.append(parse_scene(data_in_hex))

            group_dict = build_group_dict(groups)
            for scene in scenes:
                hydrate_scene(scene=scene, groups=group_dict)

            return GroupsAndScenes(groups, scenes)

        except socket.error:
            error_message = "Could not connect to qysnc host [{host}], port [{tcp_port}]".format(
                host=self.host, tcp_port=TCP_PORT)
            logging.debug(error_message)
            raise QmotionConnectionError(error_message) from socket.error

        finally:
            if socket_tcp is not None:
                socket_tcp.close()

    
