"""
Pytest configuration for content-service tests
"""
import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for the test session"""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="function")
def event_loop(event_loop_policy) -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = event_loop_policy.new_event_loop()
    yield loop
    loop.close()
