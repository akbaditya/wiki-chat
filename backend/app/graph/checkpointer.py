_saver = None


def set_saver(saver) -> None:
    global _saver
    _saver = saver


def get_saver():
    return _saver