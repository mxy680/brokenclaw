import pytest

from brokenclaw.models.tasks import TaskItem, TaskListInfo
from brokenclaw.services import tasks as tasks_service
from tests.conftest import requires_tasks


@requires_tasks
class TestListTaskLists:
    def test_returns_list(self):
        lists = tasks_service.list_task_lists()
        assert isinstance(lists, list)
        # Every Google account has at least one default task list
        assert len(lists) >= 1
        assert isinstance(lists[0], TaskListInfo)
        assert lists[0].id
        assert lists[0].title


@requires_tasks
class TestCreateAndDeleteTaskList:
    def test_create_and_delete(self):
        created = tasks_service.create_task_list(title="brokenclaw_test_tasklist")
        try:
            assert isinstance(created, TaskListInfo)
            assert created.id
            assert created.title == "brokenclaw_test_tasklist"
        finally:
            tasks_service.delete_task_list(created.id)


@requires_tasks
class TestCreateAndCompleteTask:
    @pytest.fixture(autouse=True)
    def setup_tasklist(self):
        self.tasklist = tasks_service.create_task_list(title="brokenclaw_test_tasks")
        yield
        tasks_service.delete_task_list(self.tasklist.id)

    def test_create_task(self):
        task = tasks_service.create_task(self.tasklist.id, title="Test task")
        assert isinstance(task, TaskItem)
        assert task.title == "Test task"
        assert task.status == "needsAction"

    def test_create_and_list_tasks(self):
        tasks_service.create_task(self.tasklist.id, title="Task A")
        tasks_service.create_task(self.tasklist.id, title="Task B")
        tasks = tasks_service.list_tasks(self.tasklist.id)
        assert len(tasks) >= 2
        titles = [t.title for t in tasks]
        assert "Task A" in titles
        assert "Task B" in titles

    def test_complete_task(self):
        task = tasks_service.create_task(self.tasklist.id, title="Complete me")
        completed = tasks_service.complete_task(self.tasklist.id, task.id)
        assert completed.status == "completed"

    def test_update_task(self):
        task = tasks_service.create_task(self.tasklist.id, title="Original")
        updated = tasks_service.update_task(
            self.tasklist.id, task.id, title="Updated", notes="Some notes",
        )
        assert updated.title == "Updated"
        assert updated.notes == "Some notes"

    def test_delete_task(self):
        task = tasks_service.create_task(self.tasklist.id, title="Delete me")
        tasks_service.delete_task(self.tasklist.id, task.id)
        # Verify it's gone (or marked deleted)
        tasks = tasks_service.list_tasks(self.tasklist.id, show_completed=True)
        task_ids = [t.id for t in tasks]
        assert task.id not in task_ids
