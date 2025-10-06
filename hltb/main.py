__version__ = "0.5.3"

import re
from argparse import ArgumentParser
from typing import NamedTuple, Self

from requests import get, post
from tabulate import tabulate

BASE_URL = "https://howlongtobeat.com"

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Content-Type": "application/json",
}


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


def get_games(game: str, n: int, ext: str) -> None | list[Game]:
    headers = COMMON_HEADERS | {"Referer": f"{BASE_URL}/?q={game}"}

    body = {
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

    url = f"{BASE_URL}/api/seek/{ext}"
    resp = post(
        url,
        json=body,
        headers=headers,
    )

    if not resp.ok:
        print(f"error getting game details {resp.status_code}")
        return

    return [Game.from_dict(game) for game in resp.json()["data"]]


def _get_ext_src_file_url() -> str | None:
    resp = get(BASE_URL, headers=COMMON_HEADERS)
    if not resp.ok:
        print(f"error getting index {resp.status_code}")
        return

    resp_content = resp.content.decode("utf-8")
    fname_re = re.compile(
        r'src="(/_next/static/chunks/pages/_app-.*?js)"', re.IGNORECASE
    )
    src_file_url_list = fname_re.findall(resp_content)
    if not src_file_url_list:
        print("error getting src file name")
        return

    return f"{BASE_URL}{src_file_url_list.pop()}"


def _get_api_ext() -> str | None:
    src_file_url = _get_ext_src_file_url()
    if not src_file_url:
        return None

    ext_resp = get(src_file_url, headers=COMMON_HEADERS)
    ext_resp_content = ext_resp.content.decode("utf-8")

    ext_regex = re.compile(
        r'/api/seek/[\'"]\.concat\([\'"](.*?)[\'"]\).concat\([\'"](.*?)[\'"]\)',
        re.IGNORECASE,
    )
    ext_parts_list = ext_regex.findall(ext_resp_content)
    if not ext_parts_list:
        print("error getting game ext: no parts")
        return

    (ext1, ext2) = ext_parts_list.pop()
    return ext1 + ext2


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


def main():
    args = get_cli_parser().parse_args()

    game = args.game
    ext = _get_api_ext()
    if not ext:
        return

    games = get_games(game, args.num, ext)

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
