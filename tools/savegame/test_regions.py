#!/usr/bin/env python3
"""GameCube save regions accepted by gc2hd.py: USA, Japan and Europe share the packed save layout."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gc2hd  # noqa: E402
import wwsave as W  # noqa: E402


def used_slot(name=b"Link", rupees=191):
    g = bytearray(W.GAMEDATA_SIZE)
    W.put(g, W.GC_FIELDS, "info.player_name", name.ljust(17, b"\0"))
    W.put(g, W.GC_FIELDS, "status_a.rupee", struct.pack(">H", rupees))
    return bytes(g)


def with_card_save_count(gci, value):
    """PAL writes the language index into card_savedata.save_count (mDoMemCdRWm_Store)."""
    out = bytearray(gci)
    for k in (1, 2):
        block = W.GCI_HEADER + k * W.CARD_BLOCK
        struct.pack_into(">I", out, block, value)
        sav = out[block:block + W.CARD_BLOCK]
        struct.pack_into(">I", out, block + 0x1FFC, W.gc_checksum_card(sav))
    return bytes(out)


class Regions(unittest.TestCase):
    def setUp(self):
        self.slots = [used_slot(), bytes(W.GAMEDATA_SIZE), bytes(W.GAMEDATA_SIZE)]

    def convert(self, code, card_save_count=None):
        gci = W.write_gci(code, self.slots)
        if card_save_count is not None:
            gci = with_card_save_count(gci, card_save_count)
        return gc2hd.convert_gci(gci)

    def test_europe_converts_like_usa(self):
        _, usa, _ = self.convert(b"GZLE01")
        code, eur, report = self.convert(b"GZLP01")
        self.assertEqual(code, b"GZLP01")
        self.assertEqual(eur, usa)
        self.assertEqual(report[0][2:4], ("Link", "Link"))

    def test_europe_language_in_card_header_is_ignored(self):
        _, english, _ = self.convert(b"GZLP01", card_save_count=0)
        for language in (1, 2, 3, 4):
            with self.subTest(language=language):
                self.assertEqual(self.convert(b"GZLP01", card_save_count=language)[1], english)

    def test_europe_accented_name_is_kept(self):
        self.slots[0] = used_slot(name="Zoë".encode("latin-1"))
        _, sav, _ = self.convert(b"GZLP01")
        _, extras, _ = W.read_hd(sav)
        self.assertEqual(W.hd_name(extras[0]), "Zoë")

    def test_other_games_are_rejected(self):
        gci = bytearray(W.write_gci(b"GZLE01", self.slots))
        gci[0:6] = b"GALE01"
        with self.assertRaises(W.GciError):
            gc2hd.convert_gci(bytes(gci))


if __name__ == "__main__":
    unittest.main()
