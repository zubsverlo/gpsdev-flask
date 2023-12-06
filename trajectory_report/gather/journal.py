from trajectory_report.JournalManager import HrManager


def update_journal():
    HrManager().todo_all()


if __name__ == "__main__":
    update_journal()
    