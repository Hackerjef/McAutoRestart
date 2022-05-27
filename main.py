import yaml
import logging
import time
import humanize
from datetime import datetime, timedelta

from mctools import RCONClient
from mcstatus import JavaServer

with open("config.yaml") as file:
    config = yaml.load(file, yaml.SafeLoader)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)


def wait_for_login():
    rrcon = None

    def _login():
        _rcon = RCONClient(config['server_host'], port=config['server_rcon_port'])
        try:
            logging.info("Trying to rcon into server :)")
            _rcon.login(config['server_rcon_password'])
            return _rcon, True
        except:
            logging.info("Failed to login to server.. Trying again in 5s")
            return _rcon, False

    while True:
        rcon, status = _login()
        if status:
            logging.info("Got Rcon connection")
            rrcon = rcon
            break
        else:
            time.sleep(5)
    return rrcon


def sec_remaining(ttr):
    return (ttr - datetime.now()).total_seconds()


def restart_reminders(rcon, ttr):
    last_reminder = datetime.now()
    rcon.command(f"ebc &a (!) Restarting {humanize.naturaltime(ttr)}")
    while sec_remaining(ttr) >= 10:
        if sec_remaining(ttr) >= 60:
            # check if it has been a min
            if (datetime.now() - last_reminder).total_seconds() >= 60:
                remaining = humanize.naturaltime(ttr)
                logging.info(f"Sending reminder to server ({remaining})")
                rcon.command(f"ebc &a (!) Restarting {remaining}")
                last_reminder = datetime.now()
        else:
            time.sleep(1)
    logging.info("Under 10 sec remaining till shutdown, killing reminder loop and enabling whitelist")
    rcon.command("whitelist on")
    for i in range(10):
        rcon.command(f"ebc &a (!) Restarting in {10 - i}s")
        time.sleep(1)
    return


def get_status():
    server = JavaServer.lookup(f"{config['server_host']}:{config['server_port']}")
    return server.status()


def wait_for_online():
    while True:
        try:
            get_status()
            break
        except:
            logging.info("Server not alive yet, waiting..")
            pass
        time.sleep(5)


def Main():
    logging.info("Starting Main()")
    try:
        status = get_status()        
        logging.info(f"Server currently online with {status.players.online} players on")
    except:
        logging.info("cannot get server status, not restarting")
        exit(1)

    if status.players.online > 20:
        logging.info("server has more then 20 players connected")
        if config['dont_restart_if_players']:
            logging.info("rebooting anyway")
        else:
            logging.info("canceling reboot")
            exit(1)

    rcon = wait_for_login()
    ttr = datetime.now() + timedelta(minutes=config['restart_reminder_time'], seconds=5)
    logging.info(f"Restarting in {humanize.naturaltime(ttr)}")
    restart_reminders(rcon, ttr)
    logging.info("Restart in process!")
    rcon.command("ebc &a (!) Restarting now...")
    rcon.command("ekickall")
    rcon.command("save-all")
    logging.info("Waiting 5s for server to save world")
    time.sleep(5)
    logging.info("Stoping server")
    rcon.command("stop")
    logging.info("Waiting for server to restart (3min +)")
    time.sleep(180)
    wait_for_online()
    logging.info("Server is back online")
    rcon = wait_for_login()
    logging.info("Disabling whitelist")
    rcon.command("whitelist off")


if __name__ == '__main__':
    Main()
