# coding=utf-8
"""
User query
"""
import sys


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    :param question: is a string that is presented to the user.
    :param default: is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    :return: The "answer" return value is True for "yes", False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt_str = " [y/n] "
    elif default == "yes":
        prompt_str = " [Y/n] "
    elif default == "no":
        prompt_str = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt_str)
        try:
            # noinspection PyUnresolvedReferences,PyCompatibility
            choice = raw_input().lower()
        except NameError:
            choice = input().lower()

        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def prompt(question, default=None):
    """
    Prompt the user with a question that can have a default value

    :param question: is a string that is presented to the user.
    :type question: str
    :param default: is the presumed answer if the user just hits <Enter>.
    :type default: str
    :return: The "answer" return value.
    :rtype: str|None
    """
    if default is None:
        prompt_str = " "
    else:
        prompt_str = " [{default}] ".format(default=str(default))

    sys.stdout.write(question + prompt_str)
    try:
        # noinspection PyUnresolvedReferences,PyCompatibility
        choice = raw_input()
    except NameError:
        choice = input()
    if choice == '':
        return default
    return choice
