import json
import unittest
from unittest.mock import MagicMock, patch
from selenium import webdriver
from ai_hawk.job_applier import AIHawkJobApplier
from selenium.webdriver.common.by import By
from job_portals.lever.application_page import LeverApplicationPage
from job_portals.base_job_portal import BaseJobPortal
from job import Job
from ai_hawk.llm.llm_manager import GPTAnswerer
from job_application_saver import ApplicationSaver
from job_portals.lever.job_page import LeverJobPage
from main import init_browser
from utils import browser_utils


class TestLeverJobPortalIntegration(unittest.TestCase):
    def setUp(self):
        # Initialize browser once per test
        self.driver = init_browser()
        browser_utils.set_default_driver(self.driver)

        # Configure base mocks
        self._setup_application_mocks()
        self._setup_gpt_mocks()

        # Initialize core test component
        self.job_applier = AIHawkJobApplier(
            job_portal=self.mock_job_portal,
            resume_dir=None,
            set_old_answers=[],
            gpt_answerer=self.mock_gpt_answerer,
            work_preferences={"keywords_whitelist": []},
            resume_generator_manager=MagicMock(),
        )

    def _setup_application_mocks(self):
        """Configure application page and job portal mocks"""
        self.mock_job_page = LeverJobPage(self.driver)
        self.mock_application_page = LeverApplicationPage(self.driver)

        self.mock_job_portal = MagicMock(spec=BaseJobPortal)
        self.mock_job_portal.application_page = self.mock_application_page
        self.mock_job_portal.job_page = self.mock_job_page
        self.mock_application_page._handle_location_input = MagicMock()

    def _setup_gpt_mocks(self):
        """Configure standard GPT response behavior"""
        self.mock_gpt_answerer = MagicMock(spec=GPTAnswerer)
        self.mock_gpt_answerer.answer_question_from_options.side_effect = (
            lambda q, o: o[0]
        )
        self.mock_gpt_answerer.answer_question_textual_wide_range.side_effect = (
            lambda q: "Sample answer"
        )
        self.mock_gpt_answerer.answer_question_numeric.side_effect = lambda q: "12345"
        self.mock_gpt_answerer.is_job_suitable.return_value = (
            True,
            0.9,
            "Suitable job",
        )

    def tearDown(self):
        self.driver.quit()

    @patch.object(ApplicationSaver, "save")
    def test_apply_flow(self, mock_save):
        job = Job(
            title="Software Engineer",
            company="Tech Corp",
            description="Python development position",
            link=self._local_url(
                "tests/resources/lever_application_pages/job1/https-:jobs.lever.co:nielsen:f221a3f5-4045-49f0-a443-62b0030dc56f.html"
            ),
        )

        # Mock application button click
        self.mock_job_page.click_apply_button = MagicMock(
            side_effect=lambda _: self.driver.get(
                self._local_url(
                    "tests/resources/lever_application_pages/job1/https-:jobs.lever.co:nielsen:f221a3f5-4045-49f0-a443-62b0030dc56f:apply.html"
                )
            )
        )

        # Execute and verify
        self.job_applier.apply_to_job(job)
        mock_save.assert_called_once()
        self.mock_gpt_answerer.is_job_suitable.assert_called_once()

    def _local_url(self, path):
        from pathlib import Path

        return Path(path).resolve().as_uri()
