"""Performance tests for Phase 1 UX improvements."""

import pytest
import asyncio
import time
from unittest.mock import patch
from src.components.enhanced_errors import error_manager
from src.components.loading_states import loading_manager
from src.components.session_workflow import session_workflow_manager
from src.components.parameter_tooltips import tooltip_manager


class TestPerformanceBenchmarks:
    """Test performance impact of UX improvements."""

    def test_enhanced_errors_performance(self):
        """Test that enhanced error validation has minimal performance impact."""
        start_time = time.time()

        # Test multiple validations
        for _ in range(100):
            error_manager.validate_field_with_enhanced_errors("temperature", 1.5)
            error_manager.validate_field_with_enhanced_errors("agent_name", "TestAgent")
            error_manager.validate_field_with_enhanced_errors("top_p", 0.9)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 300 validations in under 0.1 seconds
        assert duration < 0.1, f"Enhanced error validation took {duration:.3f}s, expected < 0.1s"

    def test_tooltip_generation_performance(self):
        """Test that tooltip generation is fast."""
        start_time = time.time()

        # Generate tooltips for all parameters
        for _ in range(50):
            tooltip_manager.get_tooltip_html("temperature")
            tooltip_manager.get_tooltip_html("top_p")
            tooltip_manager.get_tooltip_html("max_tokens")
            tooltip_manager.get_tooltip_html("system_prompt")

        end_time = time.time()
        duration = end_time - start_time

        # Should generate 200 tooltips in under 0.05 seconds
        assert duration < 0.05, f"Tooltip generation took {duration:.3f}s, expected < 0.05s"

    @pytest.mark.asyncio
    async def test_loading_states_performance(self):
        """Test that loading state operations are fast."""
        start_time = time.time()

        # Test multiple loading operations
        for i in range(20):
            operation_id = f"perf-test-{i}"
            await loading_manager.start_loading(operation_id, "message_send", f"Test {i}")
            await loading_manager.complete_loading(operation_id, success=True)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 40 operations in under 0.1 seconds
        assert duration < 0.1, f"Loading operations took {duration:.3f}s, expected < 0.1s"

    @pytest.mark.asyncio
    async def test_session_workflow_performance(self):
        """Test that session workflow operations are fast."""
        start_time = time.time()

        # Test multiple session operations
        for i in range(25):
            session_id = f"perf-session-{i}"
            await session_workflow_manager.check_save_prompt_needed(session_id, 5)
            await session_workflow_manager.show_save_prompt(session_id)
            await session_workflow_manager.handle_save_action(session_id, "dismiss")

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 75 operations in under 0.2 seconds
        assert duration < 0.2, f"Session operations took {duration:.3f}s, expected < 0.2s"

    def test_memory_usage_stability(self):
        """Test that components don't have memory leaks."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform many operations
        for i in range(1000):
            error_manager.validate_field_with_enhanced_errors("temperature", i * 0.01)
            tooltip_manager.get_tooltip_html("temperature", i * 0.01)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be minimal (< 10MB)
        assert memory_increase < 10, f"Memory increased by {memory_increase:.1f}MB, expected < 10MB"

    def test_concurrent_operations_performance(self):
        """Test performance under concurrent operations."""
        import threading

        results = []
        errors = []

        def worker(worker_id):
            try:
                start = time.time()
                for i in range(50):
                    error_manager.validate_field_with_enhanced_errors("temperature", 0.5)
                    tooltip_manager.get_tooltip_html("temperature", 0.5)
                end = time.time()
                results.append(end - start)
            except Exception as e:
                errors.append(str(e))

        # Start 5 concurrent workers
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Check no errors occurred
        assert len(errors) == 0, f"Concurrent operations failed: {errors}"

        # Check average performance is acceptable
        avg_time = sum(results) / len(results)
        assert avg_time < 0.1, f"Average concurrent operation time {avg_time:.3f}s, expected < 0.1s"

    @pytest.mark.asyncio
    async def test_async_operations_scalability(self):
        """Test that async operations scale well."""
        start_time = time.time()

        # Create multiple concurrent operations
        tasks = []
        for i in range(10):
            operation_id = f"async-test-{i}"
            task = loading_manager.start_loading(operation_id, "message_send", f"Async {i}")
            tasks.append(task)

        # Wait for all to complete
        await asyncio.gather(*tasks)

        # Complete all operations
        completion_tasks = []
        for i in range(10):
            operation_id = f"async-test-{i}"
            task = loading_manager.complete_loading(operation_id, success=True)
            completion_tasks.append(task)

        await asyncio.gather(*completion_tasks)

        end_time = time.time()
        duration = end_time - start_time

        # Should handle 20 concurrent operations in under 0.2 seconds
        assert duration < 0.2, f"Concurrent async operations took {duration:.3f}s, expected < 0.2s"

    def test_ui_rendering_performance(self):
        """Test that UI rendering components are fast."""
        from src.components.session_workflow import render_session_status_indicator, render_session_switcher
        from src.components.enhanced_errors import render_error_message

        start_time = time.time()

        # Render various UI components multiple times
        for i in range(100):
            render_session_status_indicator(f"session-{i}", {"state": "saved"})
            render_session_switcher(f"session-{i}", [{"id": f"session-{i}", "name": f"Session {i}"}])
            render_error_message({"is_valid": False, "error_message": f"Error {i}", "help_content": None, "suggestions": [], "examples": []})

        end_time = time.time()
        duration = end_time - start_time

        # Should render 300 components in under 0.1 seconds
        assert duration < 0.1, f"UI rendering took {duration:.3f}s, expected < 0.1s"

    def test_initialization_performance(self):
        """Test that component initialization is fast."""
        start_time = time.time()

        # Re-initialize components multiple times
        for _ in range(10):
            from src.components.enhanced_errors import EnhancedErrorManager
            from src.components.parameter_tooltips import TooltipManager
            from src.components.session_workflow import SessionWorkflowManager

            EnhancedErrorManager()
            TooltipManager()
            SessionWorkflowManager()

        end_time = time.time()
        duration = end_time - start_time

        # Should initialize 30 components in under 0.05 seconds
        assert duration < 0.05, f"Component initialization took {duration:.3f}s, expected < 0.05s"