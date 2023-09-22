from trajectory_report.JournalManager import JournalManager

if __name__ == "__main__":
    j = JournalManager()
    j.update_journal()
    j.set_quit_date()
    