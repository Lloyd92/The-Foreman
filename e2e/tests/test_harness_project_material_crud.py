"""Backend-authoritative Project and material browser coverage."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.application import ForemanApplication
from foreman_e2e.base import BrowserE2ETestCase
from foreman_e2e.inventory import InventoryPage
from foreman_e2e.projects import ProjectsPage


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Project CRUD requires the disposable deployment runner.",
)
class ProjectMaterialCrudTests(BrowserE2ETestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app = ForemanApplication(
            self.driver,
            origin=self.config.origin,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.inventory = InventoryPage(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.projects = ProjectsPage(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )

    def test_project_and_material_persistence_workflow(self) -> None:
        inventory_item = {
            "name": "E2E Project Plywood",
            "category": "CNC Materials",
            "location": "E2E Material Rack",
            "quantity": 8,
            "unit": "sheets",
            "minimum": 2,
            "cost": 24.50,
            "supplier": "E2E Project Supplier",
            "notes": "Material dependency for Project E2E.",
        }
        created_project = {
            "name": "E2E CNC Organizer",
            "type": "prototype",
            "status": "active",
            "priority": "high",
            "progress": 25,
            "startDate": "2026-08-01",
            "targetDate": "2026-08-15",
            "estimatedCost": 125.50,
            "description": "Initial isolated Project workflow.",
            "notes": "Created by Firefox E2E.",
        }
        edited_project = {
            "name": "E2E CNC Wall Organizer",
            "type": "build",
            "status": "active",
            "priority": "urgent",
            "progress": 60,
            "startDate": "2026-08-02",
            "targetDate": "2026-08-22",
            "estimatedCost": 210,
            "description": "Updated backend-authoritative Project.",
            "notes": "Edited by Firefox E2E.",
        }

        self.app.open("inventory")
        self.inventory.wait_for_empty_state()
        self.inventory.create_item(inventory_item)

        self.app.open("projects")
        self.projects.wait_for_empty_state()
        self.assertEqual(self.projects.summary_total(), "0")

        self.projects.create_project(created_project)

        self.assertEqual(
            self.projects.card_values(created_project["name"]),
            {
                "name": "E2E CNC Organizer",
                "status": "Active",
                "priority": "HIGH PRIORITY",
                "type": "Prototype",
                "progress": "25%",
                "cost": "$125.50",
                "description": "Initial isolated Project workflow.",
                "readiness": "NOT APPLICABLE",
            },
        )

        self.projects.edit_project(
            created_project["name"],
            edited_project,
        )

        self.assertEqual(
            self.projects.card_values(edited_project["name"]),
            {
                "name": "E2E CNC Wall Organizer",
                "status": "Active",
                "priority": "URGENT PRIORITY",
                "type": "Build",
                "progress": "60%",
                "cost": "$210.00",
                "description": "Updated backend-authoritative Project.",
                "readiness": "NOT APPLICABLE",
            },
        )

        self.projects.open_materials(edited_project["name"])
        self.projects.add_material(
            inventory_item["name"],
            quantity=4,
            note="Enough material is available.",
        )

        self.assertEqual(self.projects.material_readiness(), "READY")
        self.assertEqual(
            self.projects.material_values(inventory_item["name"]),
            {
                "name": "E2E Project Plywood",
                "reference": "CNC Materials",
                "status": "SUFFICIENT",
                "available": "8 sheets",
                "required": "4 sheets",
                "shortage": "0 sheets",
                "note": "Enough material is available.",
            },
        )
        self.projects.close_materials()

        self.assertEqual(
            self.projects.card_values(
                edited_project["name"]
            )["readiness"],
            "READY",
        )

        self.projects.open_materials(edited_project["name"])
        self.projects.edit_material(
            inventory_item["name"],
            quantity=12,
            note="Additional sheets are required.",
        )

        self.assertEqual(
            self.projects.material_readiness(),
            "NEEDS MATERIALS",
        )
        self.assertEqual(
            self.projects.material_values(inventory_item["name"]),
            {
                "name": "E2E Project Plywood",
                "reference": "CNC Materials",
                "status": "INSUFFICIENT",
                "available": "8 sheets",
                "required": "12 sheets",
                "shortage": "4 sheets",
                "note": "Additional sheets are required.",
            },
        )
        self.projects.close_materials()

        # A fresh application load proves the Project and material
        # requirement were returned by HardHead.
        self.app.open("projects")

        self.assertEqual(
            self.projects.card_values(edited_project["name"]),
            {
                "name": "E2E CNC Wall Organizer",
                "status": "Active",
                "priority": "URGENT PRIORITY",
                "type": "Build",
                "progress": "60%",
                "cost": "$210.00",
                "description": "Updated backend-authoritative Project.",
                "readiness": "NEEDS MATERIALS",
            },
        )

        self.projects.open_materials(edited_project["name"])
        self.assertEqual(
            self.projects.material_values(inventory_item["name"])[
                "required"
            ],
            "12 sheets",
        )
        self.assertEqual(
            self.projects.material_values(inventory_item["name"])[
                "note"
            ],
            "Additional sheets are required.",
        )

        self.projects.remove_material(inventory_item["name"])
        self.projects.wait_for_materials_empty()
        self.assertEqual(
            self.projects.material_readiness(),
            "NOT APPLICABLE",
        )
        self.projects.close_materials()

        self.app.open("projects")
        self.projects.open_materials(edited_project["name"])
        self.projects.wait_for_materials_empty()
        self.projects.close_materials()

        self.projects.delete_project(edited_project["name"])
        self.projects.wait_for_empty_state()
        self.assertEqual(self.projects.summary_total(), "0")

        self.app.open("projects")
        self.projects.wait_for_empty_state()
        self.assertIsNone(
            self.projects.find_card(edited_project["name"]),
        )

        # Remove the dependency only after its Project reference is gone.
        self.app.open("inventory")
        self.inventory.delete_item(inventory_item["name"])
        self.inventory.wait_for_empty_state()

        self.app.open("inventory")
        self.inventory.wait_for_empty_state()
        self.assertIsNone(
            self.inventory.find_row(inventory_item["name"]),
        )


if __name__ == "__main__":
    unittest.main()
