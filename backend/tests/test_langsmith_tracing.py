import os
from types import SimpleNamespace

from app.core.config import Settings, configure_langsmith_tracing
from app.services.case_generator import CaseGeneratorWorkflow


class RecordingGraph:
    def __init__(self):
        self.calls = []

    def invoke(self, payload, config):
        self.calls.append((payload, config))
        return {"report_markdown": ""}


def make_workflow() -> CaseGeneratorWorkflow:
    workflow = CaseGeneratorWorkflow.__new__(CaseGeneratorWorkflow)
    workflow.provider = "openai"
    workflow.model = "gpt-4o-mini"
    workflow.task_id = 42
    workflow.rag_enabled = True
    workflow.template_enabled = False
    workflow.graph = RecordingGraph()
    return workflow


def test_configure_langsmith_disables_tracing_without_key(monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    settings = Settings(
        langsmith_tracing=True,
        langsmith_api_key="",
        langsmith_project="test-case-generator-test",
        langsmith_hide_inputs=True,
        langsmith_hide_outputs=True,
    )

    enabled = configure_langsmith_tracing(settings)

    assert enabled is False
    assert os.environ["LANGSMITH_TRACING"] == "false"
    assert os.environ["LANGSMITH_HIDE_INPUTS"] == "true"
    assert os.environ["LANGSMITH_HIDE_OUTPUTS"] == "true"


def test_trace_config_contains_only_safe_correlation_metadata():
    workflow = make_workflow()

    config = workflow.get_trace_config("thread-123", "rag_topic_extraction")

    assert config["configurable"] == {"thread_id": "thread-123"}
    assert config["run_name"] == "case-generator-rag-topic-extraction"
    assert config["metadata"] == {
        "thread_id": "thread-123",
        "workflow_operation": "rag_topic_extraction",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "rag_enabled": True,
        "template_enabled": False,
        "workflow_version": "four-phase-v1",
        "task_id": "42",
    }


def test_start_and_resume_reuse_preallocated_thread_id():
    workflow = make_workflow()
    parsed_doc = SimpleNamespace(markdown="requirements", images=[], tables=[])

    thread_id, _ = workflow.start(parsed_doc, thread_id="thread-123")
    workflow.resume("thread-123", "clarification")

    assert thread_id == "thread-123"
    start_config = workflow.graph.calls[0][1]
    resume_config = workflow.graph.calls[1][1]
    assert start_config["configurable"] == {"thread_id": "thread-123"}
    assert resume_config["configurable"] == {"thread_id": "thread-123"}
    assert start_config["metadata"]["workflow_operation"] == "start"
    assert resume_config["metadata"]["workflow_operation"] == "resume"
