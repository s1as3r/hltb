__version__ = "0.6.5"

from argparse import ArgumentParser
from threading import Event, Thread
from time import sleep, time
from typing import NamedTuple, Self

from requests import get, post
from tabulate import tabulate

BASE_URL = "https://howlongtobeat.com"
BASE_FIND_URL = f"{BASE_URL}/api/find"

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Content-Type": "application/json",
    "Referer": f"{BASE_URL}",
}

SPINNER_SLEEP_DURATION = 0.05


class CompletionTimes(NamedTuple):
    main: int
    extra: int
    complete: int


class Game(NamedTuple):
    title: str
    alias: str
    released: int
    times: CompletionTimes

    @classmethod
    def from_dict(cls, game: dict[str, str | int]) -> Self:
        title = str(game["game_name"])
        alias = str(game["game_alias"])
        release = int(game["release_world"])
        main = int(game["comp_main"])
        extra = int(game["comp_plus"])
        complete = int(game["comp_100"])

        return cls(title, alias, release, CompletionTimes(main, extra, complete))


def get_cli_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="hltb", description="check howlongtobeat")
    parser.add_argument("game", metavar="GAME", type=str, help="Name of the Game")
    parser.add_argument(
        "--num",
        "-n",
        type=int,
        metavar="N",
        help="show top N games",
        default=1,
    )
    parser.add_argument(
        "--alias", "-a", help="display game alias if avaiable", action="store_true"
    )

    parser.add_argument(
        "--released", "-r", help="display the game's release year", action="store_true"
    )
    parser.add_argument(
        "--version",
        "-v",
        help="show version",
        action="version",
        version="%(prog)s " + __version__,
    )
    return parser


def get_games(
    game: str, n: int, token: str, fpr_key: str, fpr_val: str
) -> None | list[Game]:
    headers = COMMON_HEADERS | {
        "x-auth-token": token,
        "x-hp-key": fpr_key,
        "x-hp-val": fpr_val,
    }

    body = {
        fpr_key: fpr_val,
        "searchType": "games",
        "searchTerms": [game],
        "searchPage": 1,
        "size": n,
        "searchOptions": {
            "games": {
                "userId": 0,
                "platform": "",
                "sortCategory": "popular",
                "rangeCategory": "main",
                "rangeTime": {"min": None, "max": None},
                "gameplay": {
                    "perspective": "",
                    "flow": "",
                    "genre": "",
                    "difficulty": "",
                },
                "rangeYear": {"min": "", "max": ""},
                "modifier": "",
            },
        },
    }

    resp = post(
        BASE_FIND_URL,
        json=body,
        headers=headers,
    )

    if not resp.ok:
        print(f"error getting game details {resp.status_code}")
        return

    return [Game.from_dict(game) for game in resp.json()["data"]]


def _get_auth_data() -> dict[str, str] | None:
    time_ms = int(time() * 1000)
    url = f"{BASE_FIND_URL}/init?t={time_ms}"
    resp = get(url, headers=COMMON_HEADERS)
    return resp.json()


def _get_time_str(time: int) -> str:
    return f"{time // (60 * 60)} Hr {time % (60 * 60) // 60} Min"


def get_table(games: list[Game]) -> dict[str, list[int | str]]:
    table = {
        "title": [],
        "alias": [],
        "released": [],
        "main": [],
        "main + extra": [],
        "completionist": [],
    }

    for game in games:
        table["title"].append(game.title)
        table["alias"].append(game.alias)
        table["released"].append(game.released)
        table["main"].append(_get_time_str(game.times.main))
        table["main + extra"].append(_get_time_str(game.times.extra))
        table["completionist"].append(_get_time_str(game.times.complete))

    return table


def spin(query: str, stop_event: Event) -> None:
    sprites = "\\|/-"
    n_sprites = len(sprites)
    idx = 0

    while not stop_event.is_set():
        print(f"looking for {query}", sprites[idx], end="\r")
        idx = (idx + 1) % n_sprites
        sleep(SPINNER_SLEEP_DURATION)


def main() -> None:
    args = get_cli_parser().parse_args()
    game = args.game

    spinner_stop_event = Event()
    spinner_thread = Thread(
        name="spinner",
        target=spin,
        args=(
            game,
            spinner_stop_event,
        ),
        daemon=True,
    )

    spinner_thread.start()
    token_fpr = _get_auth_data()
    if not token_fpr or any(
        key not in token_fpr for key in ("token", "hpKey", "hpVal")
    ):
        return

    games = get_games(
        game,
        args.num,
        token_fpr["token"],
        token_fpr["hpKey"],
        token_fpr["hpVal"],
    )
    if not games:
        spinner_stop_event.set()
        spinner_thread.join()
        print("\nno games found")
        return

    table = get_table(games)
    if not args.released:
        table.pop("released")
    if not args.alias:
        table.pop("alias")

    spinner_stop_event.set()
    spinner_thread.join()
    print("\r", tabulate(table, headers="keys"), sep="")


if __name__ == "__main__":
    main()
