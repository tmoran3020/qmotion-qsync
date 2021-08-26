""" Exceptions thrown by module
"""


class QmotionError(Exception):
    """ Base exception class for this module. """
    def __init__(self, *args, **kwargs):
        response = kwargs.pop('response', None)
        self.response = response
        self.request = kwargs.pop('request', None)
        if (response is not None and not self.request and
                hasattr(response, 'request')):
            self.request = self.response.request
        super().__init__(*args, **kwargs)

class QmotionConnectionError(QmotionError):
    """A connection error occurred."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class Timeout(QmotionError):
    """The request timed out."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class InputError(QmotionError):
    """The input was invalid."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class UnexpectedDataError(QmotionError):
    """The data from the socket is unexpected"""
    def __init__(self, message):
        super().__init__(message)
        self.message = message
