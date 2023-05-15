allowed_alphabet = "abcdefghijklmnopqrstuvwxyz1234567890"
allowed_alphabet += allowed_alphabet.upper()


def name(given):
    """
    Clean a given name so that it can be used inside of JCI.
    """
    return "".join(l if l in allowed_alphabet else "-" for l in given)
