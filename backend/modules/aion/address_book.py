# File: backend/modules/aion/address_book.py

import json
import os
from threading import Lock

ADDRESS_BOOK_PATH = "data/global_address_book.json"

class AddressBook:
    def __init__(self):
        self.addresses = {}
        self.lock = Lock()
        self._load()

    def _load(self):
        if os.path.exists(ADDRESS_BOOK_PATH):
            try:
                with open(ADDRESS_BOOK_PATH, "r") as f:
                    self.addresses = json.load(f)
            except Exception as e:
                print("Failed to load address book:", e)

    def _save(self):
        with open(ADDRESS_BOOK_PATH, "w") as f:
            json.dump(self.addresses, f, indent=2)

    def register_container(self, container: dict):
        with self.lock:
            self.addresses[container["id"]] = container
            self._save()

    def save_container(self, container: dict):
        self.register_container(container)  # alias

    def get_container(self, container_id: str):
        return self.addresses.get(container_id)

    def get_all(self):
        return list(self.addresses.values())

    def get_all_except(self, exclude_id: str):
        return [c for cid, c in self.addresses.items() if cid != exclude_id]

    def remove_container(self, container_id: str):
        with self.lock:
            if container_id in self.addresses:
                del self.addresses[container_id]
                self._save()