# deck_loader.py
import csv
import random
from swu_engine.card import Card
from swu_engine.cardbundle import CardBundle


class CardDatabase:
    """Holds all card definitions loaded from cards.csv"""
    def __init__(self, csv_path: str):
        self.cards_by_id = {}
        self.load_cards(csv_path)

    def load_cards(self, csv_path: str):
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Unique ID already exists in CSV as "ID"
                card_id = row.get("ID") or f"{row['Set']}_{row['Number']}"
                card = Card(
                    name=row["Name"],
                    back_info=row.get("BackInfo", ""),
                    token_info=row.get("TokenInfo", ""),
                    card_type=row["Type"].lower(),
                    cost=int(row.get("Cost", 0) or 0),
                    arenas=[a.strip() for a in row.get("Arenas", "").split(";") if a.strip()],
                    attack=int(row.get("Power", 0) or 0),
                    health=int(row.get("HP", 0) or 0),
                    keywords=[k.strip() for k in row.get("Keywords", "").split(";") if k.strip()],
                )
                self.cards_by_id[card_id] = card

    def get_card(self, card_id: str) -> Card | None:
        return self.cards_by_id.get(card_id)


class Deck:
    """Wrapper for a player's deck (list of CardBundles)."""
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.cards: list[CardBundle] = []

    def add_card(self, card: Card):
        self.cards.append(CardBundle(primary_card=card, owner_id=self.player_id))

    def add_cards(self, card: Card, count: int):
        for _ in range(count):
            self.add_card(card)

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self, n: int = 1):
        drawn = []
        for _ in range(min(n, len(self.cards))):
            drawn.append(self.cards.pop(0))
        return drawn

    def mulligan(self, hand: list[CardBundle]):
        """Shuffle hand back into deck, draw new hand of same size."""
        self.cards.extend(hand)
        self.shuffle()
        return self.draw(len(hand))

    def summary(self):
        counts = {}
        for bundle in self.cards:
            name = bundle.primary_card.name
            counts[name] = counts.get(name, 0) + 1
        return counts

    def validate(self):
        """
        Validate deck against SWU rules:
        - 1 leader, 1 base
        - min 50 cards (excluding leader/base)
        - max 3 copies of any card (non-leader, non-base)
        - no tokens in deck
        """
        counts = {}
        leaders = 0
        bases = 0
        main_deck_count = 0

        for bundle in self.cards:
            card = bundle.primary_card
            ctype = card.card_type.lower()
            counts[card.name] = counts.get(card.name, 0) + 1

            if ctype == "leader":
                leaders += 1
            elif ctype == "base":
                bases += 1
            elif ctype == "token":
                raise ValueError(f"Illegal card in deck: token '{card.name}'")
            else:
                main_deck_count += 1

        if leaders != 1:
            raise ValueError(f"Deck must include exactly 1 leader (found {leaders}).")
        if bases != 1:
            raise ValueError(f"Deck must include exactly 1 base (found {bases}).")
        if main_deck_count < 50:
            raise ValueError(f"Deck must have at least 50 cards (excluding leader/base). Found {main_deck_count}.")

        for name, count in counts.items():
            if count > 3:
                # Leaders and Bases are exempt
                first_bundle = next(b for b in self.cards if b.primary_card.name == name)
                ctype = first_bundle.primary_card.card_type.lower()
                if ctype not in ("leader", "base"):
                    raise ValueError(f"Too many copies of {name}: {count} (max 3 allowed).")

        return True

    def __len__(self):
        return len(self.cards)

    def __iter__(self):
        return iter(self.cards)

    def load_deck_from_list(player, db: CardDatabase, decklist: dict[str, int]) -> Deck:
        deck = Deck(player.get_player_id())
        for card_id, count in decklist.items():
            base_card = db.get_card(card_id)
            if not base_card:
                raise ValueError(f"Card ID {card_id} not found in database.")
            deck.add_cards(base_card, count)
        deck.validate()
        return deck

    def load_deck_from_file(player, db: CardDatabase, deck_file: str) -> Deck:
        decklist = {}
        with open(deck_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) != 2:
                    raise ValueError(f"Invalid line in deck file: {line}")
                card_id, count = parts[0].strip(), int(parts[1].strip())
                decklist[card_id] = decklist.get(card_id, 0) + count

        return load_deck_from_list(player, db, decklist)
