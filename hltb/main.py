from argparse import ArgumentParser
from typing import Dict, List, NamedTuple, Self

from requests import post
from tabulate import tabulate

BASE_URL = "https://howlongtobeat.com"


class Game(NamedTuple):
    title: str
    main: int
    extra: int
    complete: int

    @classmethod
    def from_dict(cls, game: Dict[str, str | int]) -> Self:
        title = str(game["game_name"])
        main = int(game["comp_main"])
        extra = int(game["comp_plus"])
        complete = int(game["comp_100"])

        return cls(title, main, extra, complete)


def get_cli_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="hltb", description="check howlongtobeat")
    parser.add_argument("game", metavar="GAME", type=str, help="Name of the Game")
    parser.add_argument(
        "--num",
        "-n",
        type=int,
        metavar="N",
        help="show top N games (max=20)",
        default=1,
    )
    return parser


def get_games(game: str) -> None | List[Game]:
    headers = {
        "Referer": BASE_URL,
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    }

    body = {
        "searchType": "games",
        "searchTerms": [game],
        "searchPage": 1,
        "size": 20,
    }

    resp = post(f"{BASE_URL}/api/search", json=body, headers=headers)

    if not resp.ok:
        print(f"error getting game details {resp.status_code}")
        return

    return [Game.from_dict(game) for game in resp.json()["data"]]


def _get_time_str(time: int) -> str:
    return f"{time // (60 * 60)} Hr {time % (60 * 60) // 60} Min"


def _tabulate_row(game: Game) -> List[str]:
    return [
        game.title,
        _get_time_str(game.main),
        _get_time_str(game.extra),
        _get_time_str(game.complete),
    ]


def main():
    args = get_cli_parser().parse_args()

    game = args.game
    n = 20 if args.num > 20 else args.num

    games = get_games(game)
    if not games:
        print("no games found")
        return

    games = games[:n]

    print(
        tabulate(
            map(_tabulate_row, games),
            headers=["title", "main", "main + extra", "completionist"],
        )
    )


if __name__ == "__main__":
    main()
