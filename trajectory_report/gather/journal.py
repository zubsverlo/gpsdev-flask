from trajectory_report.JournalManager import JournalManager


def update_journal():
    j = JournalManager()
    j.update_journal()
    j.set_quit_date()


if __name__ == "__main__":
    update_journal()
    