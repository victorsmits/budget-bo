from django.test import SimpleTestCase, override_settings

from apps.jobs.enrich import _compute_enrichment_chunk_plan


class EnrichmentChunkPlanTests(SimpleTestCase):
    @override_settings(GEMINI_MAX_BATCH_SIZE=50, ENRICH_MAX_WORKERS=8, ENRICH_TARGET_API_CALLS_PER_JOB=2)
    def test_plan_uses_multiple_workers_for_large_backlog(self):
        workers, chunk_size = _compute_enrichment_chunk_plan(450)

        self.assertEqual(workers, 5)
        self.assertEqual(chunk_size, 100)

    @override_settings(GEMINI_MAX_BATCH_SIZE=50, ENRICH_MAX_WORKERS=8, ENRICH_TARGET_API_CALLS_PER_JOB=2)
    def test_plan_keeps_single_worker_for_small_backlog(self):
        workers, chunk_size = _compute_enrichment_chunk_plan(30)

        self.assertEqual(workers, 1)
        self.assertEqual(chunk_size, 30)
