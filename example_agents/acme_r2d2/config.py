#  Writes out an example config file for this component's local and global
#  settings

import configparser
import json


config = configparser.ConfigParser()

config.add_section("local")
config.set("local", "epsilon", ".99")
config.add_section("global")
config.set("global", "store_lstm_state", "True")

print("Writing settings.ini")
with open("settings.ini", "w") as fout:  # save
    config.write(fout)


d = {
    "local": {"epsilon": 0.99},
    "global": {"store_lstm_state": True},
}
# Use JSON because of types
print("Writing settings.json")
with open("settings.json", "w") as fout:
    fout.write(json.dumps(d, sort_keys=True, indent=4))


with open("settings.json") as fin:
    data = json.loads(fin.read())

assert isinstance(data["local"]["epsilon"], float)
assert isinstance(data["global"]["store_lstm_state"], bool)
print("Success!")
