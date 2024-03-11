from argparse import ArgumentParser
from importlib.metadata import version
from typing import Dict, List, NamedTuple, Self

from requests import post
from tabulate import tabulate

BASE_URL = "https://howlongtobeat.com"


class Times(NamedTuple):
    main: int
    extra: int
    complete: int


class Game(NamedTuple):
    title: str
    alias: str
    released: int
    times: Times

    @classmethod
    def from_dict(cls, game: Dict[str, str | int]) -> Self:
        title = str(game["game_name"])
        alias = str(game["game_alias"])
        release = int(game["release_world"])
        main = int(game["comp_main"])
        extra = int(game["comp_plus"])
        complete = int(game["comp_100"])

        return cls(title, alias, release, Times(main, extra, complete))


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
        version="%(prog)s " + version("hltb"),
    )
    return parser


def get_games(game: str, n: int) -> None | List[Game]:
    headers = {
        "Referer": BASE_URL,
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    }

    body = {
        "searchType": "games",
        "searchTerms": [game],
        "searchPage": 1,
        "size": n,
    }

    resp = post(f"{BASE_URL}/api/search", json=body, headers=headers)

    if not resp.ok:
        print(f"error getting game details {resp.status_code}")
        return

    return [Game.from_dict(game) for game in resp.json()["data"]]


def _get_time_str(time: int) -> str:
    return f"{time // (60 * 60)} Hr {time % (60 * 60) // 60} Min"


def get_table(games: List[Game]) -> Dict[str, List[int | str]]:
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


def main():
    args = get_cli_parser().parse_args()

    game = args.game
    games = get_games(game, args.num)

    if not games:
        print("no games found")
        return

    table = get_table(games)
    if not args.released:
        table.pop("released")
    if not args.alias:
        table.pop("alias")

    print(tabulate(table, headers="keys"))


if __name__ == "__main__":
    main()
