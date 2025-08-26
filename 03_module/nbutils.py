import urllib


def get_localtunnel_passwd():
    return urllib.request.urlopen("https://ipv4.icanhazip.com").read().decode("utf8").strip("\n")
