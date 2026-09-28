import json
import os
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

STORES = {
    "🇺🇸 USA": "https://store.taylorswift.com",
    "🇨🇦 Canada": "https://storeca.taylorswift.com",
}

KEYWORDS = ("vinyl", "lp", "2lp", "3lp")
INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))

CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "886079574")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

STATE_FILE = Path("state.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 TaylorSwiftVinylWatch/1.0"
}


def get_vinyls(store):
    url = store.rstrip("/") + "/products.json?limit=250"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    products = response.json().get("products", [])
    vinyls = {}

    for product in products:

        text = " ".join([
            str(product.get("title", "")),
            str(product.get("product_type", "")),
            " ".join(product.get("tags", []) or [])
        ]).lower()

        if any(keyword in text for keyword in KEYWORDS):

            handle = product.get("handle")

            if not handle:
                continue

            variants = product.get("variants") or []

            price = (
                variants[0].get("price")
                if variants
                else None
            )

            product_id = str(
                product.get("id") or handle
            )

            vinyls[product_id] = {
                "title": product.get(
                    "title",
                    "Taylor Swift Vinyl"
                ),
                "price": price,
                "url": urljoin(
                    store,
                    "/products/" + handle
                )
            }

    return vinyls


def send_alert(market, item):

    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing"
        )

    price = ""

    if item.get("price"):
        price = f"\n💰 {item['price']}"

    message = (
        "🚨 NOUVEAU VINYLE TAYLOR SWIFT 🚨\n\n"
        f"{market}\n"
        f"💿 {item['title']}"
        f"{price}\n\n"
        "🛒 ACHETER MAINTENANT\n"
        f"{item['url']}"
    )

    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    response.raise_for_status()


def load_state():

    if STATE_FILE.exists():

        try:
            return json.loads(
                STATE_FILE.read_text()
            )

        except Exception:
            pass

    return {}


def save_state(state):

    STATE_FILE.write_text(
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False
        )
    )


def check_stores():

    state = load_state()

    first_run = not bool(state)

    updated_state = dict(state)

    for market, store in STORES.items():

        try:

            current = get_vinyls(store)

            previous = state.get(
                market,
                {}
            )

            if not first_run:

                for product_id, item in current.items():

                    if product_id not in previous:

                        send_alert(
                            market,
                            item
                        )

            updated_state[market] = current

        except Exception as error:

            print(
                f"{market}: {error}",
                flush=True
            )

    save_state(updated_state)

    if first_run:

        print(
            "Initial vinyl list created.",
            flush=True
        )


if __name__ == "__main__":

    print(
        "Taylor Swift Vinyl Watch started.",
        flush=True
    )

    while True:

        check_stores()

        time.sleep(INTERVAL)
