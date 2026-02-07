
import unittest
from agents.overseer import determine_alert_metadata, ACTION_REQUIRED_TYPES

class TestOverseerLogic(unittest.TestCase):
    def test_action_required_mapping(self):
        """Test that action required types are correctly mapped."""
        self.assertTrue(ACTION_REQUIRED_TYPES["RESTOCK_NOW"])
        self.assertTrue(ACTION_REQUIRED_TYPES["SCHEDULE_CHANGE"])
        self.assertTrue(ACTION_REQUIRED_TYPES["SUPPLY_CHAIN_RISK"])
        self.assertFalse(ACTION_REQUIRED_TYPES["SHORTAGE_WARNING"])
        self.assertFalse(ACTION_REQUIRED_TYPES["SUBSTITUTE_RECOMMENDED"])

    def test_determine_alert_metadata_inventory(self):
        """Test metadata for inventory-only evidence."""
        alert_type = "RESTOCK_NOW"
        evidence = [
            {
                "source_type": "INVENTORY",
                "description": "Low stock",
                "source_url": None
            }
        ]
        metadata = determine_alert_metadata(alert_type, evidence)
        self.assertTrue(metadata["action_required"])
        self.assertEqual(metadata["source"], "Stock")

    def test_determine_alert_metadata_external(self):
        """Test metadata for external source evidence."""
        alert_type = "SHORTAGE_WARNING"
        url = "https://fda.gov/shortage"
        evidence = [
            {
                "source_type": "INVENTORY",
                "description": "Low stock",
                "source_url": None
            },
            {
                "source_type": "FDA",
                "description": "FDA Report",
                "source_url": url
            }
        ]
        metadata = determine_alert_metadata(alert_type, evidence)
        self.assertFalse(metadata["action_required"])
        self.assertEqual(metadata["source"], url)

    def test_determine_alert_metadata_mixed_priority(self):
        """Test that external URL takes priority over 'Stock'."""
        alert_type = "SUPPLY_CHAIN_RISK"
        url = "https://news.com/supply-issue"
        evidence = [
            {
                "source_type": "INVENTORY",
                "source_url": None
            },
            {
                "source_type": "NEWS",
                "source_url": url
            }
        ]
        metadata = determine_alert_metadata(alert_type, evidence)
        self.assertTrue(metadata["action_required"])
        self.assertEqual(metadata["source"], url)

    def test_determine_alert_metadata_no_evidence(self):
        """Test metadata with no evidence."""
        metadata = determine_alert_metadata("RESTOCK_NOW", [])
        self.assertTrue(metadata["action_required"])
        self.assertIsNone(metadata["source"])

if __name__ == '__main__':
    unittest.main()
