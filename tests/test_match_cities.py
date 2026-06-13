import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from match_cities import (
    Candidate,
    BRAND_NAME,
    alias_row_from_match,
    apply_manual_choice,
    colorize,
    default_config,
    interactive_review,
    load_config,
    match_one,
    normalize_city,
    render_matched_pairs,
    resolve_input_workbook,
    should_pause_on_exit,
    should_prompt_for_review,
)


class CityMatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates = [
            Candidate(1, "AE", "DUBAI", "DUBAI", "DUBAI"),
            Candidate(2, "AE", "SHARJAH", "SHARJAH", "SHARJAH"),
            Candidate(3, "IL", "PETAKH TIKVA", "PETAKH TIKVA", "PETAKH TIKVA"),
            Candidate(
                4,
                "AU",
                "BERKELEY VALE; WARNERVALE NSW",
                "WARNERVALE NSW",
                "WARNERVALE NSW",
            ),
            Candidate(5, "KW", "SAFAT", "SAFAT", "SAFAT"),
        ]

    def test_brand_name_is_andys_linematcher(self):
        self.assertEqual(BRAND_NAME, "Andy's LineMatcher")

    def test_colorize_can_be_disabled_for_plain_output(self):
        self.assertEqual(colorize("ok", "green", enabled=False), "ok")
        self.assertIn("\x1b[", colorize("ok", "green", enabled=True))

    def match_city(self, city: str, country: str):
        return match_one(
            delivery_city=city,
            arrival_country=country,
            candidates=self.candidates,
            aliases={},
            auto_threshold=90,
            review_threshold=75,
            min_margin=3,
            allow_cross_country=False,
        )

    def test_normalize_city_removes_country_suffix_when_city_has_more_tokens(self):
        self.assertEqual(normalize_city("Dubai, UAE", "AE"), "DUBAI")

    def test_matches_common_spelling_variants(self):
        self.assertEqual(self.match_city("Sharjach", "AE").destination_city, "SHARJAH")
        self.assertEqual(
            self.match_city("PETAH TIKVA", "IL").destination_city,
            "PETAKH TIKVA",
        )

    def test_matches_city_inside_multi_city_rate_card_cell(self):
        result = self.match_city("Warnervale", "AU")
        self.assertEqual(result.status, "auto_matched")
        self.assertEqual(
            result.destination_city,
            "BERKELEY VALE; WARNERVALE NSW",
        )

    def test_low_score_country_match_is_not_forced(self):
        result = self.match_city("KUWAIT", "KW")
        self.assertEqual(result.status, "unmatched")
        self.assertIsNone(result.destination_city)

    def test_manual_choice_promotes_candidate_to_manual_match(self):
        record = {
            "Delivery City": "KUWAIT",
            "Arrival Country": "KW",
            "normalized_delivery_city": "KUWAIT",
            "match_status": "unmatched",
            "candidate_1_country": "KW",
            "candidate_1_city": "SAFAT",
            "candidate_1_score": 36.4,
        }

        updated = apply_manual_choice(record, 1)

        self.assertEqual(updated["match_status"], "manual_matched")
        self.assertEqual(updated["match_method"], "manual")
        self.assertEqual(updated["matched_destination_country"], "KW")
        self.assertEqual(updated["matched_destination_city"], "SAFAT")

    def test_alias_row_uses_manual_match_fields(self):
        record = {
            "Delivery City": "Sharjach",
            "Arrival Country": "AE",
            "matched_destination_city": "SHARJAH",
            "matched_destination_country": "AE",
        }

        row = alias_row_from_match(record)

        self.assertEqual(
            row,
            {
                "shrep_city": "Sharjach",
                "arrival_country": "AE",
                "rc_city": "SHARJAH",
                "destination_country": "AE",
            },
        )

    def test_no_args_console_mode_prompts_for_review_when_needed(self):
        self.assertTrue(
            should_prompt_for_review(
                explicit_review=False,
                review_rows=[{"Delivery City": "KUWAIT"}],
                no_args_mode=True,
            )
        )

    def test_explicit_review_does_not_prompt_again(self):
        self.assertFalse(
            should_prompt_for_review(
                explicit_review=True,
                review_rows=[{"Delivery City": "KUWAIT"}],
                no_args_mode=True,
            )
        )

    def test_pause_on_exit_only_for_no_args_or_frozen_console_mode(self):
        self.assertTrue(should_pause_on_exit(no_args_mode=True, frozen=False))
        self.assertTrue(should_pause_on_exit(no_args_mode=False, frozen=True))
        self.assertFalse(should_pause_on_exit(no_args_mode=False, frozen=False))

    def test_q_skips_current_review_item_instead_of_exiting_all_review(self):
        city_map = [
            {
                "Arrival Country": "IL",
                "Delivery City": "Hagit",
                "normalized_delivery_city": "HAGIT",
                "match_status": "unmatched",
                "candidate_1_country": "IL",
                "candidate_1_city": "BEIT DAGAN",
                "candidate_1_score": 26.7,
            },
            {
                "Arrival Country": "KW",
                "Delivery City": "KUWAIT",
                "normalized_delivery_city": "KUWAIT",
                "match_status": "unmatched",
                "candidate_1_country": "KW",
                "candidate_1_city": "SAFAT",
                "candidate_1_score": 36.4,
            },
        ]
        answers = iter(["q", "1"])

        reviewed = interactive_review(
            city_map,
            input_func=lambda _: next(answers),
            output_func=lambda _: None,
        )

        self.assertEqual(reviewed[0]["match_status"], "unmatched")
        self.assertEqual(reviewed[1]["match_status"], "manual_matched")
        self.assertEqual(reviewed[1]["matched_destination_city"], "SAFAT")

    def test_render_matched_pairs_includes_method_and_score(self):
        city_map = [
            {
                "Arrival Country": "AE",
                "Delivery City": "Dubai",
                "match_status": "auto_matched",
                "match_method": "fuzzy",
                "match_score": 100.0,
                "matched_destination_country": "AE",
                "matched_destination_city": "DUBAI",
            },
            {
                "Arrival Country": "KW",
                "Delivery City": "KUWAIT",
                "match_status": "manual_matched",
                "match_method": "manual",
                "match_score": 36.4,
                "matched_destination_country": "KW",
                "matched_destination_city": "SAFAT",
            },
        ]

        lines = render_matched_pairs(city_map, enabled=False)

        self.assertEqual(len(lines), 2)
        self.assertIn("fuzzy", lines[0])
        self.assertIn("100.0", lines[0])
        self.assertIn("manual", lines[1])
        self.assertIn("36.4", lines[1])

    def test_load_config_reads_custom_workbook_and_columns(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "linematcher.config.json"
            path.write_text(
                """
{
  "input_filename": "custom.xlsx",
  "sheets": {"rc": "rate-card", "shrep": "shipment-report"},
  "columns": {
    "rc_city": "RC City",
    "rc_country": "RC Country",
    "shrep_city": "Ship City",
    "shrep_country": "Ship Country"
  }
}
""".strip(),
                encoding="utf-8",
            )

            config = load_config(path)

            self.assertEqual(config.input_filename, "custom.xlsx")
            self.assertEqual(config.rc_sheet, "rate-card")
            self.assertEqual(config.shrep_sheet, "shipment-report")
            self.assertEqual(config.rc_city_col, "RC City")
            self.assertEqual(config.rc_country_col, "RC Country")
            self.assertEqual(config.shrep_city_col, "Ship City")
            self.assertEqual(config.shrep_country_col, "Ship Country")

    def test_resolve_input_workbook_uses_single_xlsx_when_default_name_missing(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            workbook = base_dir / "anything.xlsx"
            workbook.write_bytes(b"fake")

            chosen = resolve_input_workbook(
                explicit_input=None,
                config=default_config(),
                base_dir=base_dir,
                input_func=lambda _: "1",
                output_func=lambda _: None,
            )

            self.assertEqual(chosen, workbook)

    def test_resolve_input_workbook_prompts_when_multiple_xlsx_exist(self):
        with TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            first = base_dir / "a.xlsx"
            second = base_dir / "b.xlsx"
            first.write_bytes(b"fake")
            second.write_bytes(b"fake")

            chosen = resolve_input_workbook(
                explicit_input=None,
                config=default_config(),
                base_dir=base_dir,
                input_func=lambda _: "2",
                output_func=lambda _: None,
            )

            self.assertEqual(chosen, second)


if __name__ == "__main__":
    unittest.main()
